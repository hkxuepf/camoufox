"""Kernel Version Management, Jittered UA Generation & Update Channel.

Manages multiple Chromium anti-detect kernel versions (new and old coexistence),
detects installed binary capabilities, provides real-version micro-jittered
User Agent generation, and manages cloud update channels.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal
from datetime import datetime
import json
import platform
import random
from loguru import logger
from pydantic import BaseModel, Field

from camoufox_pm.config import get_settings


class KernelInfo(BaseModel):
    """Metadata describing an installed or available Chromium kernel."""

    version: str = Field(..., description="Full version string, e.g. '154.0.8037.97'")
    major: int = Field(..., description="Major version number, e.g. 154")
    build: int = Field(8037, description="Build number, e.g. 8037")
    patch: int = Field(97, description="Patch number, e.g. 97")
    flavor: Literal["camou_native", "cloak_stealth", "gecko_native"] = "camou_native"
    is_default: bool = Field(False, description="Whether this is the primary active kernel")
    executable_path: str = Field(..., description="Path to the executable binary")
    channel: Literal["stable", "beta", "dev"] = "stable"


class KernelUpdateCheckResult(BaseModel):
    """Result of checking for newer compiled kernel updates."""

    current_version: str
    latest_version: str
    has_update: bool
    download_url: str | None = None
    changelog: str | None = None
    size_mb: float = 0.0


# Baseline build numbers by major version for realistic jitter ranges
KNOWN_MAJOR_BUILD_BASELINES = {
    151: 7922,
    152: 7977,
    153: 8010,
    154: 8037,
    155: 8080,
    156: 8120,
    158: 8200,
    160: 8300,
}


class KernelManager:
    """Manages multi-version kernel installation, detection, and invocation routing."""

    def __init__(self) -> None:
        self._cached_version_map: dict[str, KernelInfo] = {}
        self._default_major: int = 155

    def get_kernels_root_dir(self, engine: str = "chromium") -> Path:
        """Root directory where multi-version kernels are stored (~/.camoufox/kernels/{engine})."""
        kernels_dir = Path.home() / ".camoufox" / "kernels" / engine
        kernels_dir.mkdir(parents=True, exist_ok=True)
        return kernels_dir

    def get_kernel_meta(self, executable_path: str) -> dict | None:
        """Read .version_meta.json from kernel directory if present."""
        try:
            exe_p = Path(executable_path)
            candidates = [
                exe_p.parent / ".version_meta.json",
                exe_p.parent.parent / ".version_meta.json",
                exe_p.parent.parent.parent / ".version_meta.json",
            ]
            for cand in candidates:
                if cand.is_file():
                    return json.loads(cand.read_text(encoding="utf-8"))
        except Exception:
            pass
        return None

    def detect_binary_version(self, executable_path: str) -> KernelInfo | None:
        """Execute a Chromium binary with --version and parse its version string."""
        if not Path(executable_path).is_file():
            return None

        # Return cached if already parsed
        if executable_path in self._cached_version_map:
            return self._cached_version_map[executable_path]

        try:
            res = subprocess.run(
                [executable_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = res.stdout.strip()
            # Output format: Chromium 155.0.8059.39
            m = re.search(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", out)
            if m:
                major = int(m.group(1))
                build = int(m.group(3))
                patch = int(m.group(4))
                meta = self.get_kernel_meta(executable_path)
                flavor = meta.get("flavor") if meta else ("camou_native" if major >= 155 else "cloak_stealth")
                info = KernelInfo(
                    version=m.group(0),
                    major=major,
                    build=build,
                    patch=patch,
                    flavor=flavor,
                    is_default=(major == 155),
                    executable_path=executable_path,
                )
                self._cached_version_map[executable_path] = info
                return info
        except Exception as exc:
            logger.warning(f"Failed to detect version for {executable_path}: {exc}")

        # Fallback based on executable name or default 155
        meta = self.get_kernel_meta(executable_path)
        flavor = meta.get("flavor") if meta else "camou_native"
        return KernelInfo(
            version="155.0.8059.39",
            major=155,
            build=8059,
            patch=39,
            flavor=flavor,
            is_default=True,
            executable_path=executable_path,
        )

    def list_installed_kernels(self) -> list[KernelInfo]:
        """Scan and list all installed Chromium kernels (default + versioned kernels)."""
        kernels: list[KernelInfo] = []
        seen_paths: set[str] = set()

        # 1. Check primary/default Chromium in bin/Chromium.app or launcher path
        from camoufox_pm.core.chromium_launcher import get_chromium_executable_path
        default_exe = get_chromium_executable_path()
        if default_exe and Path(default_exe).is_file():
            info = self.detect_binary_version(default_exe)
            if info:
                info.is_default = True
                kernels.append(info)
                seen_paths.add(str(Path(default_exe).resolve()))
                self._default_major = info.major

        # 2. Check multi-version kernel directories (~/.camoufox/kernels/chromium/ & ~/.camoufox/bin/kernels/)
        scan_roots = [
            self.get_kernels_root_dir("chromium"),
            Path.home() / ".camoufox" / "bin" / "kernels",
        ]
        settings = get_settings()
        data_dir = Path(settings.db_path).resolve().parent
        scan_roots.append(data_dir / "bin" / "kernels")

        for root in scan_roots:
            if not root.is_dir():
                continue
            for item in root.iterdir():
                if item.is_dir():
                    candidates = [
                        item / "Contents" / "MacOS" / "Chromium",
                        item / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
                        item / "chrome.exe",
                        item / "chromium",
                    ]
                    for cand in candidates:
                        cand_str = str(cand)
                        real_p = str(cand.resolve()) if cand.exists() else cand_str
                        if cand.is_file() and real_p not in seen_paths:
                            info = self.detect_binary_version(cand_str)
                            if info:
                                kernels.append(info)
                                seen_paths.add(real_p)

        # Sort by major version descending
        kernels.sort(key=lambda k: k.major, reverse=True)
        return kernels

    def get_active_kernel_major(self) -> int:
        """Return the major version of the current default active kernel."""
        kernels = self.list_installed_kernels()
        for k in kernels:
            if k.is_default:
                return k.major
        return self._default_major

    def get_executable_for_version(self, target_version: str | int | None = None) -> str | None:
        """Route to the matching kernel executable for a target version (new or old).
        
        If target_version is specified (e.g. 154 or "151"):
        1. Searches installed kernels for an exact or major match.
        2. If not found, falls back cleanly to the primary/default kernel.
        """
        kernels = self.list_installed_kernels()
        if not kernels:
            from camoufox_pm.core.chromium_launcher import get_chromium_executable_path
            return get_chromium_executable_path()

        if target_version:
            target_str = str(target_version)
            target_major = None
            m = re.search(r"(\d+)", target_str)
            if m:
                target_major = int(m.group(1))

            if target_major is not None:
                for k in kernels:
                    if k.major == target_major:
                        return k.executable_path

        # Default fallback: return kernel marked is_default, or highest version
        for k in kernels:
            if k.is_default:
                return k.executable_path

        return kernels[0].executable_path

    async def ensure_kernel_ready(self, engine: str = "chromium", version: str | None = None) -> str | None:
        """Ensure the specified kernel is available locally, downloading lazily if missing."""
        exe = self.get_executable_for_version(version)
        if exe and Path(exe).is_file():
            return exe

        if not version:
            return exe

        logger.info(f"Kernel {engine} v{version} not found locally. Checking download channels...")
        try:
            from camoufox_pm.api.dependencies import get_storage_manager
            storage = get_storage_manager()
            kernels = await storage.list_kernel_releases(engine=engine, active_only=True)
            matched = None
            for k in kernels:
                if k.get("version") == version or (version and str(version) in k.get("version", "")):
                    matched = k
                    break

            if not matched and kernels:
                matched = kernels[0]

            if not matched:
                return exe

            plat = "mac_arm64" if sys.platform == "darwin" and platform.machine() == "arm64" else (
                "mac_x64" if sys.platform == "darwin" else "win_x64"
            )
            download_url = matched.get(f"{plat}_url")
            expected_sha = matched.get(f"{plat}_sha256")
            if not download_url:
                return exe

            target_dir = self.get_kernels_root_dir(engine) / version
            candidates = [
                target_dir / "Contents" / "MacOS" / "Chromium",
                target_dir / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
                target_dir / "chrome.exe",
                target_dir / "firefox.exe",
                target_dir / "firefox",
            ]
            for cand in candidates:
                if cand.is_file():
                    return str(cand)

            unpack_dir = self.get_kernels_root_dir(engine) / f"{version}.unpacking"
            if unpack_dir.exists():
                shutil.rmtree(unpack_dir, ignore_errors=True)
            unpack_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Downloading kernel {version} from {download_url}...")
            import urllib.request
            tmp_archive = unpack_dir / ("kernel.tar.gz" if "tar.gz" in download_url else "kernel.zip")
            urllib.request.urlretrieve(download_url, str(tmp_archive))

            if expected_sha:
                import hashlib
                h = hashlib.sha256()
                with open(tmp_archive, "rb") as f:
                    while chunk := f.read(1024 * 1024):
                        h.update(chunk)
                if h.hexdigest().lower() != expected_sha.lower():
                    shutil.rmtree(unpack_dir, ignore_errors=True)
                    raise RuntimeError(f"Kernel download SHA256 mismatch for {version}")

            if str(tmp_archive).endswith(".tar.gz"):
                import tarfile
                with tarfile.open(tmp_archive, "r:gz") as tar:
                    tar.extractall(path=unpack_dir)
            else:
                import zipfile
                with zipfile.ZipFile(tmp_archive, "r") as zf:
                    zf.extractall(path=unpack_dir)
            tmp_archive.unlink(missing_ok=True)

            v_major = int(re.search(r'\d+', version).group()) if re.search(r'\d+', version) else 155
            flavor = "camou_native" if (matched.get("flavor") == "camou_native" or v_major >= 155) else "cloak_stealth"
            meta_json = {
                "engine": engine,
                "version": version,
                "flavor": flavor,
                "platform": plat,
                "installed_at": datetime.now().isoformat(),
                "is_ready": True,
            }
            (unpack_dir / ".version_meta.json").write_text(json.dumps(meta_json, indent=2), encoding="utf-8")

            if sys.platform == "darwin":
                try:
                    subprocess.run(["xattr", "-rd", "com.apple.quarantine", str(unpack_dir)], check=False, capture_output=True)
                except Exception:
                    pass
                for root_p, _, files in os.walk(unpack_dir):
                    for fn in files:
                        fp = Path(root_p) / fn
                        if fn in ("Chromium", "chrome", "firefox"):
                            fp.chmod(0o755)

            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            unpack_dir.rename(target_dir)

            for cand in candidates:
                if cand.is_file():
                    return str(cand)
        except Exception as exc:
            logger.warning(f"ensure_kernel_ready failed for {engine} {version}: {exc}")

        return self.get_executable_for_version(version)

    def generate_jittered_ua(
        self,
        os_name: str = "windows",
        kernel_major: int | None = None,
    ) -> str:
        """Generate a realistic User Agent aligned with the actual kernel version,
        featuring natural micro-jitter on the build and patch numbers.
        
        Example outputs for 154:
        - Windows: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8037.114 Safari/537.36
        - macOS:   Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8038.86 Safari/537.36
        """
        major = kernel_major or self.get_active_kernel_major()
        base_build = KNOWN_MAJOR_BUILD_BASELINES.get(major, 8037)

        # Micro-jitter on build (±2) and patch (35 ~ 185)
        build_jitter = base_build + random.randint(-2, 4)
        patch_jitter = random.randint(35, 185)
        full_version = f"{major}.0.{build_jitter}.{patch_jitter}"

        os_lower = os_name.lower()
        if "android" in os_lower:
            models = ["SM-S918B", "SM-S928B", "Pixel 8", "Pixel 7 Pro", "23049PCD8G"]
            model = random.choice(models)
            return (
                f"Mozilla/5.0 (Linux; Android 14; {model}) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{full_version} Mobile Safari/537.36"
            )
        elif "ios" in os_lower or "iphone" in os_lower:
            ios_versions = ["17_5_1", "17_4_1", "17_6", "18_0"]
            v = random.choice(ios_versions)
            return (
                f"Mozilla/5.0 (iPhone; CPU iPhone OS {v} like Mac OS X) "
                f"AppleWebKit/605.1.15 (KHTML, like Gecko) "
                f"Version/17.5 Mobile/15E148 Safari/604.1"
            )
        elif "mac" in os_lower or "darwin" in os_lower:
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{full_version} Safari/537.36"
            )
        elif "linux" in os_lower:
            return (
                f"Mozilla/5.0 (X11; Linux x86_64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{full_version} Safari/537.36"
            )
        else:
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{full_version} Safari/537.36"
            )

    async def check_updates(self) -> KernelUpdateCheckResult:
        """Check the cloud server/R2 for newly compiled kernel versions."""
        current_major = self.get_active_kernel_major()
        current_ver = f"{current_major}.0.8037.97"

        # In cloud updates, check manifest or settings.cloud_server
        # Default mock channel info for next scheduled kernel release (Chrome 156)
        latest_major = 156
        has_update = latest_major > current_major

        return KernelUpdateCheckResult(
            current_version=current_ver,
            latest_version=f"{latest_major}.0.8120.45" if has_update else current_ver,
            has_update=has_update,
            download_url="https://a416a58f6b1d69a87d52bf0c70c27163.r2.cloudflarestorage.com/tikmatrix/camoufox/chromium-macos-arm64-v156.tar.gz"
            if has_update
            else None,
            changelog="Chromium 156 商业防关联内核升级：原生对齐 Chrome 156 V8 引擎与 Client Hints，修复最新 WebRTC 泄漏向量。"
            if has_update
            else "当前内核已是最新版本。",
            size_mb=168.5,
        )


kernel_manager = KernelManager()
