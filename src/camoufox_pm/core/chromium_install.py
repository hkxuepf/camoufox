"""Chromium anti-detect browser cloud installer and status manager."""

import datetime
import hashlib
import hmac
import os
import shutil
import sys
import tarfile
import threading
import urllib.request
from pathlib import Path
from typing import Literal

from loguru import logger
from pydantic import BaseModel

from camoufox_pm.config import get_settings


class ChromiumStatus(BaseModel):
    installed: bool
    version: str | None = None
    state: Literal["idle", "downloading", "ready", "error"] = "idle"
    progress: int | None = None
    message: str = "Download the Chromium anti-detect browser to open profiles."
    error: str | None = None
    executable_path: str | None = None


R2_ACCESS_KEY_ID = "9f12c91813dddea0d5fe6c63963dadf5"
R2_SECRET_ACCESS_KEY = "6ae268a165e49f6c05de633b037177606bef740ff991ab7db9c29f9254d2f4a1"
R2_HOST = "a416a58f6b1d69a87d52bf0c70c27163.r2.cloudflarestorage.com"
R2_BUCKET = "tikmatrix"
R2_PREFIX = "camoufox"


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = _sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region_name)
    k_service = _sign(k_region, service_name)
    return _sign(k_service, "aws4_request")


def _make_r2_request(canonical_uri: str) -> urllib.request.Request:
    t = datetime.datetime.now(datetime.timezone.utc)
    amzdate = t.strftime("%Y%m%dT%H%M%SZ")
    datestamp = t.strftime("%Y%m%d")
    region = "auto"
    service = "s3"

    payload_hash = hashlib.sha256(b"").hexdigest()
    canonical_headers = f"host:{R2_HOST}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amzdate}\n"
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = f"GET\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{datestamp}/{region}/{service}/aws4_request"
    string_to_sign = f"{algorithm}\n{amzdate}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"

    signing_key = _get_signature_key(R2_SECRET_ACCESS_KEY, datestamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    auth_header = (
        f"{algorithm} Credential={R2_ACCESS_KEY_ID}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    return urllib.request.Request(
        f"https://{R2_HOST}{canonical_uri}",
        headers={
            "Host": R2_HOST,
            "x-amz-date": amzdate,
            "x-amz-content-sha256": payload_hash,
            "Authorization": auth_header,
        },
    )


class ChromiumInstaller:
    """Manages the lifecycle and cloud download of the custom Chromium browser engine."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = ChromiumStatus(installed=False)

    def _get_target_bin_dir(self) -> Path:
        settings = get_settings()
        data_dir = Path(settings.db_path).resolve().parent
        bin_dir = data_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        return bin_dir

    def _find_installed_executable(self) -> str | None:
        from camoufox_pm.core.chromium_launcher import get_chromium_executable_path
        return get_chromium_executable_path()

    def status(self) -> ChromiumStatus:
        with self._lock:
            if self._state.state == "downloading":
                return self._state.model_copy()

            exe = self._find_installed_executable()
            if exe and Path(exe).is_file():
                return ChromiumStatus(
                    installed=True,
                    version="154.0.8037.97 (Anti-detect)",
                    state="ready",
                    progress=100,
                    message="Chromium 浏览器内核已就绪",
                    executable_path=exe,
                )

            return ChromiumStatus(
                installed=False,
                state="idle",
                progress=0,
                message="未检测到定制 Chromium 内核。支持从云端一键下载安装。",
            )

    def start(self) -> ChromiumStatus:
        with self._lock:
            if self._state.state == "downloading":
                return self._state.model_copy()

            self._state = ChromiumStatus(
                installed=False,
                state="downloading",
                progress=0,
                message="正在从云端连接下载 Chromium 内核…",
            )
            thread = threading.Thread(
                target=self._run_download, daemon=True, name="chromium-download"
            )
            thread.start()
            return self._state.model_copy()

    def _update(self, **kwargs) -> None:
        with self._lock:
            self._state = self._state.model_copy(update=kwargs)

    def _run_download(self) -> None:
        try:
            logger.info("Starting Chromium cloud kernel download from Cloudflare R2...")
            self._update(progress=5, message="正在从云端检索内核元数据…")

            bin_dir = self._get_target_bin_dir()
            archive_path = bin_dir / "chromium-macos-arm64.tar.gz"

            uri = f"/{R2_BUCKET}/{R2_PREFIX}/chromium-macos-arm64.tar.gz"
            req = _make_r2_request(uri)

            self._update(progress=10, message="正在从云端下载 Chromium 内核安装包 (167MB)…")

            with urllib.request.urlopen(req, timeout=120) as resp:
                total_bytes = int(resp.headers.get("Content-Length", 175000000))
                downloaded = 0
                chunk_size = 512 * 1024

                with open(archive_path, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        pct = 10 + int((downloaded / total_bytes) * 75)
                        pct = min(85, max(10, pct))
                        mb = downloaded / (1024 * 1024)
                        total_mb = total_bytes / (1024 * 1024)
                        self._update(
                            progress=pct,
                            message=f"正在下载内核文件: {mb:.1f} MB / {total_mb:.1f} MB",
                        )

            self._update(progress=88, message="下载完成，正在解压内核组件…")
            logger.info(f"Extracting {archive_path} to {bin_dir}...")

            # Extract archive
            temp_extract = bin_dir / "temp_extract"
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
            temp_extract.mkdir(parents=True, exist_ok=True)

            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=temp_extract)

            extracted_app = temp_extract / "Chromium.app"
            target_app = bin_dir / "Chromium.app"

            if not extracted_app.exists():
                # Check subdirectories
                found = list(temp_extract.glob("**/Chromium.app"))
                if found:
                    extracted_app = found[0]

            if extracted_app.exists():
                if target_app.exists():
                    shutil.rmtree(target_app)
                shutil.move(str(extracted_app), str(target_app))

            if temp_extract.exists():
                shutil.rmtree(temp_extract)
            if archive_path.exists():
                archive_path.unlink()

            self._update(progress=96, message="正在配置系统执行权限与防隔离属性…")

            # Remove quarantine and set permissions
            if sys.platform == "darwin" and target_app.exists():
                os.system(f'xattr -dr com.apple.quarantine "{target_app}" 2>/dev/null || true')
                exec_file = target_app / "Contents" / "MacOS" / "Chromium"
                if exec_file.exists():
                    os.chmod(exec_file, 0o755)

            exe = self._find_installed_executable()
            logger.info(f"Chromium installation complete! Executable: {exe}")

            self._update(
                installed=True,
                version="154.0.8037.97 (Anti-detect)",
                state="ready",
                progress=100,
                message="Chromium 内核安装完成并已就绪",
                executable_path=exe,
                error=None,
            )

        except Exception as exc:
            logger.error(f"Chromium download/installation failed: {exc}")
            self._update(
                installed=False,
                state="error",
                progress=0,
                message="Chromium 内核下载失败，请检查网络后重试",
                error=str(exc),
            )


chromium_installer = ChromiumInstaller()
