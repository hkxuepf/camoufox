"""HubStudio API compatibility layer.

Enables seamless drop-in integration for existing RPA, Selenium, Puppeteer,
and Playwright scripts designed for HubStudio's local REST API.
"""

import asyncio
import json
import math
import subprocess
import sys
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger
from pydantic import BaseModel, Field

from camoufox_pm.api.dependencies import get_profile_manager, get_storage_manager
from camoufox_pm.core.chromium_launcher import get_chromium_executable_path
from camoufox_pm.core.models import BrowserSettings, Profile, ProxyConfig, ProxyType

router = APIRouter()


def hub_response(data: Any = None, code: int = 0, msg: str = "Success") -> dict[str, Any]:
    """Uniform response format conforming to HubStudio API standards."""
    return {
        "code": code,
        "msg": msg,
        "data": data,
    }


# ==========================================
# 1. 浏览器控制模块 (Browser Lifecycle)
# ==========================================


class HubBrowserStartRequest(BaseModel):
    containerCode: str | None = Field(None, description="Profile ID or environment code")
    serialNumber: str | int | None = Field(None, description="Alternative serial number")
    isHeadless: bool = Field(False, description="Whether to launch in headless mode")
    isWebDriverReadOnlyMode: bool = Field(False, description="Read-only mode")
    skipSystemResourceCheck: bool = Field(False, description="Skip resource check")
    containerTabs: list[str] | None = Field(None, description="Initial URLs to open")
    args: list[str] | None = Field(None, description="Extra command line arguments")
    cdpHide: bool = Field(False, description="Hide CDP flag")
    pageZoom: float | None = Field(None, description="Page zoom factor")


@router.post("/api/v1/browser/start", tags=["HubStudio Compat"])
async def hub_browser_start(body: HubBrowserStartRequest):
    """Launch a browser environment conforming to HubStudio POST /api/v1/browser/start."""
    pm = get_profile_manager()
    storage = get_storage_manager()

    target_code = body.containerCode
    if not target_code and body.serialNumber is not None:
        target_code = str(body.serialNumber)

    if not target_code:
        return hub_response(code=-10004, msg="未找到环境信息，请检查环境ID是否正确", data=None)

    # 1. Resolve Profile: by ID, or by serial number, or by name
    profile = await storage.get_profile(target_code)
    if not profile:
        # Search by name or substring
        all_profs = await storage.list_profiles()
        for p in all_profs:
            if p.name == target_code or getattr(p, "id", "") == target_code:
                profile = p
                break
        if not profile and all_profs:
            # Fallback by index if serialNumber
            try:
                idx = int(target_code) - 1
                if 0 <= idx < len(all_profs):
                    profile = all_profs[idx]
            except ValueError:
                pass

    if not profile:
        return hub_response(code=-10004, msg="未找到环境信息，请检查环境ID是否正确", data=None)

    # 2. Check if already running
    active_sessions = pm.browser_sessions.active_sessions
    existing_session = active_sessions.get(profile.id)
    if existing_session and (existing_session.is_alive() if hasattr(existing_session, "is_alive") else not getattr(existing_session, "_terminated", False)):
        cdp_port = getattr(existing_session, "cdp_port", None) or 0
        exe_path = get_chromium_executable_path() or ""
        detected_ip = "127.0.0.1"
        if profile.proxy and profile.proxy.server:
            detected_ip = profile.proxy.server.split(":")[0]

        return hub_response(
            data={
                "accountId": None,
                "action": "startBrowserByCode",
                "backgroundPluginId": "",
                "browserID": profile.id,
                "browserPath": exe_path,
                "debuggingPort": cdp_port,
                "downloadPath": "",
                "duplicate": 1,
                "ip": detected_ip,
                "isDynamicIp": False,
                "launcherPage": "about:blank",
                "proxyTag": "",
                "proxyType": str(profile.proxy.type.value if profile.proxy else "direct"),
                "reportPluginId": "",
                "runMode": "2",
                "webdriver": "",
                "statusCode": 0,
            }
        )

    # 3. Launch browser
    try:
        launch_kwargs: dict[str, Any] = {}
        if body.args:
            launch_kwargs["args"] = body.args
        if body.containerTabs:
            launch_kwargs["urls"] = body.containerTabs

        res = await pm.launch_browser(
            profile.id,
            headless=body.isHeadless,
            **launch_kwargs,
        )

        session = pm.browser_sessions.active_sessions.get(profile.id)
        cdp_port = getattr(session, "cdp_port", None) or 0
        exe_path = get_chromium_executable_path() or ""
        detected_ip = "127.0.0.1"
        if profile.proxy and profile.proxy.server:
            detected_ip = profile.proxy.server.split(":")[0]

        return hub_response(
            data={
                "accountId": None,
                "action": "startBrowserByCode",
                "backgroundPluginId": "",
                "browserID": profile.id,
                "browserPath": exe_path,
                "debuggingPort": cdp_port,
                "downloadPath": "",
                "duplicate": 0,
                "ip": detected_ip,
                "isDynamicIp": False,
                "launcherPage": "about:blank",
                "proxyTag": "",
                "proxyType": str(profile.proxy.type.value if profile.proxy else "direct"),
                "reportPluginId": "",
                "runMode": "2",
                "webdriver": "",
                "statusCode": 0,
            }
        )
    except Exception as exc:
        logger.error(f"HubStudio browser/start failed for {profile.id}: {exc}")
        return hub_response(code=-10000, msg=f"启动内核失败: {exc}", data=None)


class HubBrowserStopRequest(BaseModel):
    containerCode: str | None = None
    serialNumber: str | int | None = None


@router.post("/api/v1/browser/stop", tags=["HubStudio Compat"])
async def hub_browser_stop_post(body: HubBrowserStopRequest):
    """Close browser conforming to HubStudio POST /api/v1/browser/stop."""
    return await _do_browser_stop(body.containerCode or body.serialNumber)


@router.get("/api/v1/browser/stop", tags=["HubStudio Compat"])
async def hub_browser_stop_get(
    containerCode: str | None = Query(None),
    serialNumber: str | int | None = Query(None),
):
    """Close browser conforming to HubStudio GET /api/v1/browser/stop."""
    return await _do_browser_stop(containerCode or serialNumber)


async def _do_browser_stop(target_code: Any):
    if not target_code:
        return hub_response(code=-10004, msg="未提供环境ID", data=None)
    target_code = str(target_code)
    pm = get_profile_manager()
    storage = get_storage_manager()

    profile = await storage.get_profile(target_code)
    if not profile:
        all_profs = await storage.list_profiles()
        for p in all_profs:
            if p.name == target_code or getattr(p, "id", "") == target_code:
                profile = p
                break

    prof_id = profile.id if profile else target_code
    try:
        await pm.close_browser(prof_id)
    except Exception as exc:
        logger.warning(f"Error stopping browser {prof_id}: {exc}")

    return hub_response(
        data={
            "action": "stopBrowserByCode",
            "statusCode": 0,
        }
    )


class HubStopAllRequest(BaseModel):
    clearOpening: bool = Field(False)


@router.post("/api/v1/browser/stop-all", tags=["HubStudio Compat"])
async def hub_browser_stop_all(body: HubStopAllRequest = HubStopAllRequest()):
    """Close all browsers conforming to HubStudio POST /api/v1/browser/stop-all."""
    pm = get_profile_manager()
    try:
        await pm.close_all_browsers()
    except Exception as exc:
        logger.warning(f"Error in hub_browser_stop_all: {exc}")

    return hub_response(
        data={
            "action": "CloseAllBrowser",
            "err": "成功(Success)",
            "statusCode": "0",
        }
    )


class HubBrowserStatusRequest(BaseModel):
    containerCodes: list[str] = Field(default_factory=list)


@router.post("/api/v1/browser/all-browser-status", tags=["HubStudio Compat"])
async def hub_browser_all_status(body: HubBrowserStatusRequest):
    """Query browser execution status: 0-已开启, 1-开启中, 2-关闭中, 3-已关闭."""
    pm = get_profile_manager()
    status_map: dict[str, int] = {}
    for code in body.containerCodes:
        code_str = str(code)
        status_map[code_str] = 0 if pm.browser_sessions.is_live(code_str) else 3

    return hub_response(data=status_map)


class HubForegroundRequest(BaseModel):
    containerCode: str


@router.post("/api/v1/browser/foreground", tags=["HubStudio Compat"])
async def hub_browser_foreground(body: HubForegroundRequest):
    """Bring target browser window to the front."""
    if sys.platform == "darwin":
        subprocess.run(["osascript", "-e", 'tell application "Chromium" to activate'], check=False)
    return hub_response(data={"action": "bringToForeground", "statusCode": 0})


class HubArrangeRequest(BaseModel):
    x: int = 10
    y: int = 10
    width: int = 600
    height: int = 500
    gapX: int = 20
    gapY: int = 20
    colNum: int = 3
    screenId: int | None = None


@router.post("/api/v1/browser/arrange", tags=["HubStudio Compat"])
async def hub_browser_arrange(body: HubArrangeRequest = HubArrangeRequest()):
    """Custom grid tile arrangement for open browser windows."""
    from camoufox_pm.api.routes.window_manager import tile_windows, WindowTileRequest
    req = WindowTileRequest(cols=body.colNum, padding=body.gapX, top_offset=body.y)
    await tile_windows(req)
    return hub_response(
        data={
            "action": "customArrange",
            "err": "成功(Success)",
            "requestId": str(uuid.uuid4()),
            "statusCode": "0",
        }
    )


# ==========================================
# 2. 环境管理模块 (Environment CRUD)
# ==========================================


class HubEnvListRequest(BaseModel):
    current: int = 1
    size: int = 50
    containerCodes: list[str] | None = None
    containerName: str | None = None
    tagName: str | None = None
    remark: str | None = None


@router.post("/api/v1/env/list", tags=["HubStudio Compat"])
async def hub_env_list(body: HubEnvListRequest = HubEnvListRequest()):
    """List profiles conforming to HubStudio POST /api/v1/env/list."""
    storage = get_storage_manager()
    all_profiles = await storage.list_profiles()

    # Filter
    filtered: list[Profile] = []
    for p in all_profiles:
        if body.containerCodes and p.id not in body.containerCodes:
            continue
        if body.containerName and body.containerName.lower() not in p.name.lower():
            continue
        filtered.append(p)

    total = len(filtered)
    start_idx = (body.current - 1) * body.size
    end_idx = start_idx + body.size
    paged = filtered[start_idx:end_idx]

    hub_list: list[dict[str, Any]] = []
    for idx, p in enumerate(paged, start=start_idx + 1):
        p_host = ""
        p_port = 0
        p_type = "不使用代理"
        p_acc = ""
        p_pwd = ""
        if p.proxy:
            p_type = str(p.proxy.type.value if hasattr(p.proxy.type, "value") else p.proxy.type).upper()
            if p.proxy.server:
                parts = p.proxy.server.split(":")
                p_host = parts[0]
                if len(parts) > 1:
                    try:
                        p_port = int(parts[1])
                    except ValueError:
                        pass
            p_acc = p.proxy.username or ""
            p_pwd = p.proxy.password or ""

        created_str = p.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(p, "created_at") and p.created_at else ""
        open_time_str = p.last_used.strftime("%m-%d %H:%M:%S") if hasattr(p, "last_used") and p.last_used else ""
        ua_str = p.browser_settings.user_agent or ""

        grp = getattr(p, "group", None) or (p.tags[0] if getattr(p, "tags", None) else "")
        hub_list.append({
            "allOpenTime": open_time_str,
            "asDynamicType": 1,
            "containerCode": p.id,
            "serialNumber": idx,
            "containerName": p.name,
            "createTime": created_str,
            "lastCity": "",
            "lastCountry": "",
            "lastRegion": "",
            "lastUsedIp": p_host,
            "openTime": open_time_str,
            "remark": getattr(p, "notes", "") or "",
            "proxyHost": p_host,
            "proxyPort": p_port,
            "proxyTypeName": p_type,
            "proxyAccount": p_acc,
            "proxyPassword": p_pwd,
            "refreshUrl": "",
            "tagName": grp or "未分组",
            "tagCode": grp or "",
            "ua": ua_str,
        })

    return hub_response(
        data={
            "list": hub_list,
            "total": total,
        }
    )


class HubEnvCreateRequest(BaseModel):
    containerName: str
    remark: str | None = None
    tagName: str | None = None
    cookie: str | None = None
    proxyTypeName: str | None = "不使用代理"
    proxyServer: str | None = None
    proxyPort: int | None = None
    proxyAccount: str | None = None
    proxyPassword: str | None = None
    type: str | None = "windows"
    browser: str | None = "chrome"
    coreVersion: int | None = 154


@router.post("/api/v1/env/create", tags=["HubStudio Compat"])
async def hub_env_create(body: HubEnvCreateRequest):
    """Create a profile conforming to HubStudio POST /api/v1/env/create."""
    pm = get_profile_manager()

    proxy_cfg = None
    pt_clean = (body.proxyTypeName or "").strip().lower()
    if body.proxyServer and pt_clean not in ("不使用代理", "direct", "none", ""):
        p_type = ProxyType.HTTP
        if "socks5" in pt_clean:
            p_type = ProxyType.SOCKS5
        elif "socks4" in pt_clean:
            p_type = ProxyType.SOCKS4
        elif "https" in pt_clean:
            p_type = ProxyType.HTTPS

        port_str = f":{body.proxyPort}" if body.proxyPort else ""
        proxy_cfg = ProxyConfig(
            type=p_type,
            server=f"{body.proxyServer}{port_str}",
            username=body.proxyAccount,
            password=body.proxyPassword,
        )

    engine_choice = "chromium" if (body.browser or "").lower() in ("chrome", "chromium") else "camoufox"

    b_settings = BrowserSettings(
        browser_engine=engine_choice,
        os=(body.type or "windows").lower(),
    )

    created_profile = await pm.create_profile(
        name=body.containerName,
        browser_settings=b_settings,
        proxy_config=proxy_cfg.model_dump() if proxy_cfg else None,
        notes=body.remark,
        group=body.tagName,
        cookies=body.cookie,
    )

    return hub_response(
        data={
            "containerCode": created_profile.id,
            "coreVersion": body.coreVersion or 154,
        }
    )


class HubEnvDeleteRequest(BaseModel):
    containerCodes: list[str] = Field(default_factory=list)


@router.post("/api/v1/env/del", tags=["HubStudio Compat"])
async def hub_env_delete(body: HubEnvDeleteRequest):
    """Batch delete profiles conforming to HubStudio POST /api/v1/env/del."""
    pm = get_profile_manager()
    for code in body.containerCodes:
        try:
            await pm.delete_profile(code)
        except Exception as exc:
            logger.warning(f"Failed to delete profile {code}: {exc}")

    return hub_response(data=True)


class HubCookieImportRequest(BaseModel):
    containerCode: str
    cookie: str = ""


@router.post("/api/v1/env/import-cookie", tags=["HubStudio Compat"])
async def hub_env_import_cookie(body: HubCookieImportRequest):
    """Import cookie into environment conforming to HubStudio POST /api/v1/env/import-cookie."""
    pm = get_profile_manager()
    profile = await pm.get_profile(body.containerCode)
    if not profile:
        return hub_response(code=-10004, msg="环境不存在", data=False)

    await pm.update_profile(body.containerCode, {"cookies": body.cookie})
    return hub_response(data=True)


class HubCookieExportRequest(BaseModel):
    containerCode: str


@router.post("/api/v1/env/export-cookie", tags=["HubStudio Compat"])
async def hub_env_export_cookie(body: HubCookieExportRequest):
    """Export environment cookie conforming to HubStudio POST /api/v1/env/export-cookie."""
    pm = get_profile_manager()
    profile = await pm.get_profile(body.containerCode)
    if not profile:
        return hub_response(code=-10004, msg="环境不存在", data="[]")

    cookies_raw = profile.cookies or "[]"
    return hub_response(data=cookies_raw)


class HubRandomUaRequest(BaseModel):
    type: str | None = "windows"
    version: list[int] | None = None


@router.post("/api/v1/env/random-ua", tags=["HubStudio Compat"])
async def hub_env_random_ua(body: HubRandomUaRequest = HubRandomUaRequest()):
    """Generate random User-Agent conforming to HubStudio POST /api/v1/env/random-ua."""
    os_name = (body.type or "windows").lower()
    ver = body.version[0] if body.version else 130

    if os_name == "macos":
        ua = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36"
    elif os_name == "linux":
        ua = f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36"
    else:
        ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36"

    return hub_response(data=ua)


# ==========================================
# 3. 客户端管理 (Client Lifecycle)
# ==========================================


class HubLoginRequest(BaseModel):
    appId: str | None = None
    appSecret: str | None = None
    groupCode: str | None = None


@router.post("/login", tags=["HubStudio Compat"])
async def hub_client_login(body: HubLoginRequest = HubLoginRequest()):
    """Client login conforming to HubStudio POST /login."""
    return hub_response(data=None)


@router.post("/quit", tags=["HubStudio Compat"])
async def hub_client_quit():
    """Client quit conforming to HubStudio POST /quit."""
    from camoufox_pm.core.browser_session import cleanup_all_browsers_sync
    try:
        cleanup_all_browsers_sync()
    except Exception:
        pass
    if sys.platform == "darwin":
        asyncio.get_event_loop().call_later(0.5, lambda: sys.exit(0))
    return hub_response(data=None)
