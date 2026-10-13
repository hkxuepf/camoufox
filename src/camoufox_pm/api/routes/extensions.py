"""API routes for Extension / Plugin Management."""

import base64
import io
import json
import os
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from loguru import logger
from pydantic import BaseModel

from camoufox_pm.api.dependencies import get_storage_manager
from camoufox_pm.config import get_settings
from camoufox_pm.core.models import generate_short_id
from camoufox_pm.core.preset_icons import PRESET_ICONS

router = APIRouter()


def get_extensions_dir() -> Path:
    """Return the extensions storage directory located within the user's data directory."""
    settings = get_settings()
    data_dir = Path(settings.db_path).resolve().parent
    ext_dir = data_dir / "extensions"
    ext_dir.mkdir(parents=True, exist_ok=True)
    return ext_dir


class ExtensionToggleRequest(BaseModel):
    enabled: bool


class ImportWebstoreRequest(BaseModel):
    url_or_id: str


def _resolve_locale_msg(dest_dir: Path, raw_text: str, default_locale: str = "en") -> str:
    """Resolve __MSG_key__ localized string using Chrome extension locale messages."""
    if not (isinstance(raw_text, str) and raw_text.startswith("__MSG_") and raw_text.endswith("__")):
        return raw_text
    key = raw_text[6:-2]
    locales_dir = dest_dir / "_locales"
    if not locales_dir.is_dir():
        return raw_text

    # Search in order of preferred languages
    for lang in ["zh_CN", "zh", "zh_TW", default_locale, "en", "en_US"]:
        msg_file = locales_dir / lang / "messages.json"
        if msg_file.is_file():
            try:
                data = json.loads(msg_file.read_text(encoding="utf-8"))
                if key in data and "message" in data[key]:
                    return data[key]["message"]
            except Exception:
                pass
    return raw_text


def _extract_icon_base64(dest_dir: Path, manifest: dict[str, Any]) -> str | None:
    """Find and encode the extension's icon as a base64 Data URI."""
    icon_candidates: list[str] = []

    # 1. From manifest "icons" dict: e.g. {"128": "...", "48": "...", "16": "..."}
    icons_dict = manifest.get("icons", {})
    if isinstance(icons_dict, dict):
        for size in sorted([int(k) for k in icons_dict.keys() if k.isdigit()], reverse=True):
            val = icons_dict.get(str(size))
            if val and isinstance(val, str):
                icon_candidates.append(val)

    # 2. From manifest action / browser_action default_icon
    for action_key in ("action", "browser_action"):
        action = manifest.get(action_key, {})
        if isinstance(action, dict):
            def_icon = action.get("default_icon")
            if isinstance(def_icon, str):
                icon_candidates.append(def_icon)
            elif isinstance(def_icon, dict):
                for size in sorted([int(k) for k in def_icon.keys() if k.isdigit()], reverse=True):
                    val = def_icon.get(str(size))
                    if val and isinstance(val, str):
                        icon_candidates.append(val)

    # 3. Check direct candidate paths
    for rel_path in icon_candidates:
        p = dest_dir / rel_path.lstrip("/\\")
        if p.is_file():
            try:
                b = p.read_bytes()
                mime = (
                    "image/png"
                    if p.suffix.lower() == ".png"
                    else "image/svg+xml"
                    if p.suffix.lower() == ".svg"
                    else "image/jpeg"
                )
                b64 = base64.b64encode(b).decode("ascii")
                return f"data:{mime};base64,{b64}"
            except Exception:
                pass

    # 4. Fallback search inside directory for icon*.png, icon*.svg, logo*.png
    for pattern in ("icon*.png", "icon*.svg", "logo*.png", "*128*.png", "*48*.png"):
        for p in dest_dir.rglob(pattern):
            if p.is_file():
                try:
                    b = p.read_bytes()
                    mime = "image/png" if p.suffix.lower() == ".png" else "image/svg+xml"
                    b64 = base64.b64encode(b).decode("ascii")
                    return f"data:{mime};base64,{b64}"
                except Exception:
                    pass

    return None


def _extract_crx_or_zip(file_bytes: bytes, dest_dir: Path) -> dict[str, Any]:
    """Unpack a .zip or .crx file into dest_dir, extracting manifest details and local icon."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Check for ZIP header
    pk_idx = file_bytes.find(b"PK\x03\x04")
    if pk_idx == -1:
        raise ValueError("Invalid ZIP or CRX file: missing ZIP header")

    zip_data = file_bytes[pk_idx:]
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        zf.extractall(dest_dir)

    # Read manifest.json if present
    manifest_path = dest_dir / "manifest.json"
    meta: dict[str, Any] = {"name": dest_dir.name, "version": "1.0.0", "description": "", "icon_url": None}
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            default_loc = data.get("default_locale", "en")
            raw_name = data.get("name", meta["name"])
            raw_desc = data.get("description", "")

            meta["name"] = _resolve_locale_msg(dest_dir, raw_name, default_loc)
            meta["version"] = data.get("version", meta["version"])
            meta["description"] = _resolve_locale_msg(dest_dir, raw_desc, default_loc)
            meta["icon_url"] = _extract_icon_base64(dest_dir, data)
        except Exception as exc:
            logger.warning(f"Failed to parse manifest.json: {exc}")

    return meta


async def _download_crx(crx_id: str) -> bytes:
    """Download CRX from Google Chrome Web Store update servers with fallback strategies."""
    urls = [
        f"https://clients2.google.com/service/update2/crx?response=redirect&prodversion=128.0&acceptformat=crx3&x=id%3D{crx_id}%26installsource%3Dondemand%26uc",
        f"https://clients2.google.com/service/update2/crx?response=redirect&prodversion=115.0&acceptformat=crx2,crx3&x=id%3D{crx_id}%26installsource%3Dondemand%26uc",
    ]
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
    }

    last_err = None
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        for url in urls:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200 and len(resp.content) > 100:
                    return resp.content
            except Exception as e:
                last_err = e
                continue

    raise RuntimeError(
        f"无法从 Chrome Web Store 下载该扩展 (ID: {crx_id})，请检查网络连接或确认该扩展是否在商店中公开可用: {last_err or 'HTTP 204/404'}"
    )


@router.get("/extensions")
async def list_extensions():
    """List all available extensions."""
    storage = get_storage_manager()
    items = await storage.list_extensions()
    return {"extensions": items, "total": len(items)}


@router.post("/extensions/toggle/{ext_id}")
async def toggle_extension(ext_id: str, request: ExtensionToggleRequest):
    """Enable or disable an extension."""
    storage = get_storage_manager()
    ext = await storage.get_extension(ext_id)
    if not ext:
        raise HTTPException(status_code=404, detail="Extension not found")
    await storage.update_extension(ext_id, {"enabled": 1 if request.enabled else 0})
    return {"id": ext_id, "enabled": request.enabled}


@router.post("/extensions/upload")
async def upload_extension(file: UploadFile = File(...)):
    """Upload a custom .crx or .zip browser extension."""
    storage = get_storage_manager()
    filename = file.filename or "extension.zip"
    if not (filename.endswith(".zip") or filename.endswith(".crx")):
        raise HTTPException(status_code=400, detail="只支持上传 .crx 或 .zip 格式的浏览器插件包")

    content = await file.read()
    ext_id = f"ext_{generate_short_id(8)}"
    dest_path = get_extensions_dir() / ext_id

    try:
        meta = _extract_crx_or_zip(content, dest_path)
    except Exception as exc:
        if dest_path.exists():
            shutil.rmtree(dest_path, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"解压安装扩展包失败: {exc}") from exc

    saved = await storage.create_extension(
        {
            "id": ext_id,
            "name": meta.get("name", filename),
            "version": meta.get("version", "1.0.0"),
            "icon_url": meta.get("icon_url"),
            "description": meta.get("description", "用户本地自定义上传插件"),
            "category": "custom",
            "local_path": str(dest_path.resolve()),
            "is_preset": 0,
            "enabled": 1,
        }
    )
    return saved


@router.post("/extensions/import-webstore")
async def import_webstore_extension(request: ImportWebstoreRequest):
    """Import and download an extension directly from a Chrome Web Store URL or 32-letter ID."""
    storage = get_storage_manager()
    raw = request.url_or_id.strip()

    # Extract 32 lowercase letter extension ID
    match = re.search(r"([a-p]{32})", raw.lower())
    if not match:
        raise HTTPException(
            status_code=400,
            detail="未能识别有效的 Chrome 商店扩展 ID (应为32位字母，例如 dhdgffkkebhmkfjojejmpbldmpobfkfo 或直接粘贴商店链接)",
        )

    crx_id = match.group(1)
    ext_id = f"ext_{crx_id[:12]}"
    dest_path = get_extensions_dir() / ext_id

    try:
        content = await _download_crx(crx_id)
        meta = _extract_crx_or_zip(content, dest_path)
    except Exception as exc:
        if dest_path.exists():
            shutil.rmtree(dest_path, ignore_errors=True)
        logger.error(f"Failed to import extension {crx_id}: {exc}")
        raise HTTPException(status_code=400, detail=f"导入 Chrome 商店扩展失败: {exc}") from exc

    saved = await storage.create_extension(
        {
            "id": ext_id,
            "name": meta.get("name", f"Extension {crx_id[:8]}"),
            "version": meta.get("version", "1.0.0"),
            "icon_url": meta.get("icon_url"),
            "description": meta.get("description", "从 Chrome Web Store 导入"),
            "category": "custom",
            "crx_id": crx_id,
            "local_path": str(dest_path.resolve()),
            "is_preset": 0,
            "enabled": 1,
        }
    )
    return saved


@router.post("/extensions/install-preset/{ext_id}")
async def install_preset_extension(ext_id: str):
    """Download and prepare a preset extension from Chrome Web Store."""
    storage = get_storage_manager()
    ext = await storage.get_extension(ext_id)
    if not ext:
        raise HTTPException(status_code=404, detail="Preset extension not found")

    crx_id = ext.get("crx_id")
    if not crx_id:
        raise HTTPException(status_code=400, detail="Extension has no CRX store ID")

    dest_path = get_extensions_dir() / ext_id

    # If already installed
    if dest_path.is_dir() and (dest_path / "manifest.json").exists():
        await storage.update_extension(ext_id, {"local_path": str(dest_path.resolve()), "enabled": 1})
        return {"id": ext_id, "installed": True, "local_path": str(dest_path.resolve())}

    extracted_icon = None
    try:
        content = await _download_crx(crx_id)
        meta = _extract_crx_or_zip(content, dest_path)
        extracted_icon = meta.get("icon_url")
    except Exception as exc:
        logger.warning(f"Could not download CRX ({exc}), creating placeholder manifest")
        dest_path.mkdir(parents=True, exist_ok=True)
        manifest = {
            "manifest_version": 3,
            "name": ext.get("name"),
            "version": ext.get("version", "1.0.0"),
            "description": ext.get("description", ""),
        }
        (dest_path / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    updates: dict[str, Any] = {"local_path": str(dest_path.resolve()), "enabled": 1}
    if extracted_icon:
        updates["icon_url"] = extracted_icon
    await storage.update_extension(ext_id, updates)
    return {"id": ext_id, "installed": True, "local_path": str(dest_path.resolve())}


@router.delete("/extensions/{ext_id}")
async def delete_extension_endpoint(ext_id: str):
    """Delete a custom extension."""
    storage = get_storage_manager()
    ext = await storage.get_extension(ext_id)
    if not ext:
        raise HTTPException(status_code=404, detail="Extension not found")
    if ext.get("is_preset"):
        raise HTTPException(status_code=400, detail="预置应用不支持删除，可点击开关禁用")

    if ext.get("local_path"):
        p = Path(ext["local_path"])
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)

    await storage.delete_extension(ext_id)
    return {"deleted": True}
