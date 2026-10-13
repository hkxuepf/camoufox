"""Local Automation API for Selenium / Puppeteer / Playwright integration."""

import asyncio
import random
import secrets
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger
from pydantic import BaseModel

from camoufox_pm.api.dependencies import get_current_user, get_profile_manager, get_storage_manager
from camoufox_pm.core import auth

router = APIRouter()


def _resolve_plan_name(plan_id: str | None, role: str | None) -> str:
    if role == "admin":
        return "企业超管"
    p = (plan_id or "free").lower()
    if p == "enterprise":
        return "企业版"
    if p == "pro":
        return "专业版"
    if p == "starter":
        return "入门版"
    return "免费版"


@router.get("/automation/credentials")
async def get_automation_credentials(request: Request):
    """Retrieve HubStudio-compatible local API credentials and membership entitlement."""
    storage = get_storage_manager()
    user = await get_current_user(request)
    admin_settings = await storage.get_admin_settings()

    if user:
        username = user.get("username", "admin")
        role = user.get("role", "user")
        plan_id = user.get("plan_id", "free")
        is_member = (role == "admin") or (plan_id not in ("free", "", None))
        api_status = user.get("api_status") or "disabled"
        app_id = user.get("api_app_id") or ""
        app_secret = user.get("api_app_secret") or ""
    else:
        username = "admin"
        role = "admin"
        plan_id = "enterprise"
        is_member = True
        api_status = admin_settings.get("api_status") or "disabled"
        app_id = admin_settings.get("api_app_id") or ""
        app_secret = admin_settings.get("api_app_secret") or ""

    plan_name = _resolve_plan_name(plan_id, role)
    has_applied = (api_status == "active") and bool(app_id)

    return {
        "username": username,
        "is_member": is_member,
        "role": role,
        "plan_id": plan_id,
        "plan_name": plan_name,
        "has_applied": has_applied,
        "status": "normal" if has_applied else "unapplied",
        "local_endpoint": "http://127.0.0.1:6873",
        "app_id": app_id,
        "app_secret": app_secret,
        "rate_limit": "100 次/分钟",
        "max_devices": 200,
        "documentation_url": "http://127.0.0.1:18888/api-service/",
    }


@router.post("/automation/apply")
async def apply_automation_credentials(request: Request):
    """Apply for CamouHub Local API credentials (VIP membership required)."""
    storage = get_storage_manager()
    user = await get_current_user(request)
    admin_settings = await storage.get_admin_settings()

    if user:
        username = user.get("username", "admin")
        role = user.get("role", "user")
        plan_id = user.get("plan_id", "free")
        is_member = (role == "admin") or (plan_id not in ("free", "", None))
        app_id = user.get("api_app_id")
        app_secret = user.get("api_app_secret")
    else:
        username = "admin"
        role = "admin"
        plan_id = "enterprise"
        is_member = True
        app_id = admin_settings.get("api_app_id")
        app_secret = admin_settings.get("api_app_secret")

    if not is_member:
        raise HTTPException(
            status_code=403,
            detail="该功能为 VIP 会员专享特权，请先升级会员套餐以解锁自动化 API 权限",
        )

    # Generate or reuse App ID (similar to HubStudio 27-digit ID format)
    if not app_id:
        app_id = f"2026{int(time.time()*1000)}{random.randint(10000000, 99999999)}"

    # Generate or reuse App Secret
    if not app_secret:
        app_secret = secrets.token_hex(16)

    # Persist in storage
    if user:
        await storage.update_user_api_credentials(username, "active", app_id, app_secret)
    else:
        await storage.update_admin_setting("api_status", "active")
        await storage.update_admin_setting("api_app_id", app_id)
        await storage.update_admin_setting("api_app_secret", app_secret)

    return {
        "code": 0,
        "msg": "申请成功，已开通 Local 自动化 API 权限",
        "data": {
            "has_applied": True,
            "status": "normal",
            "local_endpoint": "http://127.0.0.1:6873",
            "app_id": app_id,
            "app_secret": app_secret,
            "rate_limit": "100 次/分钟",
            "max_devices": 200,
        },
    }


@router.post("/automation/reset-secret")
async def reset_automation_secret(request: Request):
    """Regenerate App Secret for the current user."""
    storage = get_storage_manager()
    user = await get_current_user(request)
    admin_settings = await storage.get_admin_settings()

    if user:
        username = user.get("username", "admin")
        role = user.get("role", "user")
        plan_id = user.get("plan_id", "free")
        is_member = (role == "admin") or (plan_id not in ("free", "", None))
        app_id = user.get("api_app_id")
    else:
        username = "admin"
        role = "admin"
        plan_id = "enterprise"
        is_member = True
        app_id = admin_settings.get("api_app_id")

    if not is_member:
        raise HTTPException(
            status_code=403,
            detail="该功能为 VIP 会员专享特权，请先升级会员套餐",
        )

    if not app_id:
        app_id = f"2026{int(time.time()*1000)}{random.randint(10000000, 99999999)}"

    new_secret = secrets.token_hex(16)
    if user:
        await storage.update_user_api_credentials(username, "active", app_id, new_secret)
    else:
        await storage.update_admin_setting("api_status", "active")
        await storage.update_admin_setting("api_app_id", app_id)
        await storage.update_admin_setting("api_app_secret", new_secret)

    return {
        "code": 0,
        "msg": "已重置 APP Secret",
        "data": {
            "app_id": app_id,
            "app_secret": new_secret,
        },
    }


class AutomationStartRequest(BaseModel):
    profile_id: str
    headless: bool = False


class AutomationStopRequest(BaseModel):
    profile_id: str


async def _get_cdp_ws_url(cdp_port: int) -> str | None:
    """Fetch webSocketDebuggerUrl from Chromium's /json/version endpoint."""
    url = f"http://127.0.0.1:{cdp_port}/json/version"
    for _ in range(15):  # try for up to 3 seconds
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("webSocketDebuggerUrl")
        except Exception:
            pass
        await asyncio.sleep(0.2)
    return None


@router.get("/automation/active")
async def list_active_sessions():
    """List all running browser instances and their automation CDP ports."""
    pm = get_profile_manager()
    sessions = pm.browser_sessions.active_sessions
    results = []

    for pid, session in sessions.items():
        ws_url = None
        if session.cdp_port:
            ws_url = await _get_cdp_ws_url(session.cdp_port)

        results.append(
            {
                "profile_id": pid,
                "engine": session.engine,
                "process_id": session.process_id,
                "cdp_port": session.cdp_port,
                "ws_endpoint": ws_url,
                "http_endpoint": f"http://127.0.0.1:{session.cdp_port}" if session.cdp_port else None,
                "started_at": session.started_at.isoformat() if session.started_at else None,
            }
        )

    return {"active_sessions": results, "total": len(results)}


@router.post("/automation/start")
async def start_automation_browser(request: AutomationStartRequest):
    """Launch a profile and return its CDP WebSocket debug endpoint for Puppeteer/Playwright."""
    pm = get_profile_manager()
    profile = await pm.get_profile(request.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {request.profile_id} not found")

    # Launch browser
    res = await pm.launch_browser(request.profile_id, headless=request.headless)
    session = pm.browser_sessions.active_sessions.get(request.profile_id)

    ws_url = None
    cdp_port = session.cdp_port if session else None
    if cdp_port:
        ws_url = await _get_cdp_ws_url(cdp_port)

    return {
        "status": "ok",
        "profile_id": request.profile_id,
        "engine": profile.browser_settings.browser_engine,
        "cdp_port": cdp_port,
        "ws_endpoint": ws_url,
        "http_endpoint": f"http://127.0.0.1:{cdp_port}" if cdp_port else None,
        "info": "Connect with Playwright: chromium.connect_over_cdp(ws_endpoint)",
    }


@router.post("/automation/stop")
async def stop_automation_browser(request: AutomationStopRequest):
    """Close a running browser session."""
    pm = get_profile_manager()
    if not pm.browser_sessions.is_running(request.profile_id):
        return {"status": "ok", "message": "Browser is not running"}

    res = await pm.close_browser(request.profile_id)
    return {"status": "ok", "result": res}
