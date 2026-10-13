"""API routes for user login sessions.

Mounted without the auth guard: login must be reachable logged out, and the
session probe is how the UI decides whether to show the login screen at all.
"""

import asyncio
from typing import NoReturn

from fastapi import APIRouter, HTTPException, Request, Response
from loguru import logger

from camoufox_pm.api.dependencies import get_storage_manager
from camoufox_pm.api.models.auth import AuthSessionResponse, LoginRequest, RegisterRequest
from camoufox_pm.api.models.system import ApiResponse
from camoufox_pm.config import get_settings
from camoufox_pm.core import auth

router = APIRouter()

# Flat friction against online guessing; argon2 already makes each attempt cost
# real work, this keeps a loop from trying thousands per second regardless.
FAILED_LOGIN_DELAY_SECONDS = 0.5


def _set_session_cookie(request: Request, response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies or request.url.scheme == "https",
    )


async def _reject_login(password: str, burn_hash: bool) -> NoReturn:
    """One indistinguishable failure for wrong password and unknown user."""
    if burn_hash:
        auth.verify_dummy(password)
    await asyncio.sleep(FAILED_LOGIN_DELAY_SECONDS)
    raise HTTPException(status_code=401, detail="Invalid username or password")


import json
import secrets
import urllib.error
import urllib.request

@router.post(
    "/auth/register",
    response_model=AuthSessionResponse,
    operation_id="register",
    summary="Register a new user account.",
    description="Create a new user account and open a session.",
)
async def register(body: RegisterRequest, request: Request, response: Response) -> AuthSessionResponse:
    """Register a new user and log in immediately."""
    storage = get_storage_manager()
    username = body.username.strip()

    if len(username) < 2:
        raise HTTPException(status_code=400, detail="用户名长度至少为 2 个字符")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少为 6 个字符")

    existing = await storage.get_user_by_username(username)
    if existing:
        raise HTTPException(status_code=400, detail="该用户名已被注册")

    user_id = secrets.token_hex(8)
    pwd_hash = auth.hash_password(body.password)
    await storage.create_user(
        user_id=user_id,
        username=username,
        password_hash=pwd_hash,
        role="user",
        plan_id="free",
        max_profiles=10,
        max_concurrent=2,
    )
    user = await storage.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")

    await storage.delete_expired_sessions()
    token = await auth.create_session(storage, user["id"])
    _set_session_cookie(request, response, token)
    logger.info(f"User {user['username']} registered and logged in")

    used_profiles = await storage.count_profiles({"user_id": user["id"]})
    return AuthSessionResponse(
        user_auth_enabled=True,
        authenticated=True,
        token=token,
        username=user["username"],
        role=user.get("role", "user"),
        plan_id=user.get("plan_id", "free"),
        max_profiles=user.get("max_profiles", 10),
        used_profiles=used_profiles,
        max_concurrent=user.get("max_concurrent", 2),
        expires_at=user.get("expires_at"),
        status=user.get("status", "active"),
    )


@router.post(
    "/auth/login",
    response_model=AuthSessionResponse,
    operation_id="login",
    summary="Log in and receive a session cookie.",
    description=(
        "Exchange a username and password for an HttpOnly session cookie. The failure "
        "response is identical whether the username exists or the password is wrong."
    ),
)
async def login(body: LoginRequest, request: Request, response: Response) -> AuthSessionResponse:
    """Verify credentials and open a session."""
    storage = get_storage_manager()
    settings = get_settings()

    # 1. Attempt cloud authentication against cloud server
    cloud_user = None
    if settings.cloud_server and settings.cloud_server.strip():
        cloud_url = settings.cloud_server.rstrip("/")
        try:
            def _do_cloud_req():
                req = urllib.request.Request(
                    f"{cloud_url}/api/v1/auth/login",
                    data=json.dumps({"username": body.username, "password": body.password}).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "Connection": "close",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status == 200:
                        return json.loads(resp.read().decode())
                return None

            cloud_user = await asyncio.to_thread(_do_cloud_req)
        except urllib.error.HTTPError as e:
            logger.warning(f"Cloud login verification HTTP error: {e.code} {e.reason}")
        except Exception as e:
            logger.warning(f"Cloud login verification exception: {e}")

    # 2. Sync cloud user data locally if cloud login succeeded
    if cloud_user and cloud_user.get("authenticated"):
        user = await storage.get_user_by_username(body.username)
        pwd_hash = auth.hash_password(body.password)
        if not user:
            user_id = secrets.token_hex(8)
            await storage.create_user(
                user_id=user_id,
                username=body.username,
                password_hash=pwd_hash,
                role=cloud_user.get("role", "user"),
                plan_id=cloud_user.get("plan_id", "free"),
                max_profiles=cloud_user.get("max_profiles", 10),
                max_concurrent=cloud_user.get("max_concurrent", 2),
                expires_at=cloud_user.get("expires_at"),
            )
            user = await storage.get_user_by_username(body.username)
        else:
            await storage.update_user_password(body.username, pwd_hash)
            await storage.update_user_admin(
                username=body.username,
                role=cloud_user.get("role", "user"),
                plan_id=cloud_user.get("plan_id", "free"),
                max_profiles=cloud_user.get("max_profiles", 10),
                max_concurrent=cloud_user.get("max_concurrent", 2),
                expires_at=cloud_user.get("expires_at"),
                status=cloud_user.get("status", "active"),
            )
            user = await storage.get_user_by_username(body.username)
    else:
        # Fall back to local database authentication
        user = await storage.get_user_by_username(body.username)
        if user is None:
            await _reject_login(body.password, burn_hash=True)
        if not auth.verify_password(user["password_hash"], body.password):
            await _reject_login(body.password, burn_hash=False)
        if auth.password_needs_rehash(user["password_hash"]):
            await storage.update_user_password(user["username"], auth.hash_password(body.password))

    await storage.delete_expired_sessions()
    token = await auth.create_session(storage, user["id"])
    _set_session_cookie(request, response, token)
    logger.info(f"User {user['username']} logged in (role={user.get('role', 'user')})")
    
    is_admin = user.get("role") == "admin"
    used_profiles = await storage.count_profiles(None if is_admin else {"user_id": user["id"]})

    return AuthSessionResponse(
        user_auth_enabled=True,
        authenticated=True,
        token=token,
        username=user["username"],
        role=user.get("role", "user"),
        plan_id=user.get("plan_id", "free"),
        max_profiles=user.get("max_profiles", 10),
        used_profiles=used_profiles,
        max_concurrent=user.get("max_concurrent", 2),
        expires_at=user.get("expires_at"),
        status=user.get("status", "active"),
    )


@router.post(
    "/auth/logout",
    response_model=ApiResponse[None],
    operation_id="logout",
    summary="Log out and invalidate the session.",
    description=(
        "Delete the server-side session and clear the cookie. Idempotent: logging out "
        "without a session is not an error."
    ),
)
async def logout(request: Request, response: Response) -> ApiResponse[None]:
    """Invalidate the caller's session, if any."""
    token = auth.extract_session_token(request)
    if token:
        await get_storage_manager().delete_session(auth.hash_token(token))
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return ApiResponse(success=True, message="Logged out", data=None)


@router.get(
    "/auth/user-profile",
    response_model=AuthSessionResponse,
    summary="Get user plan and profile quota for client sync",
)
async def get_user_profile(username: str) -> AuthSessionResponse:
    storage = get_storage_manager()
    user = await storage.get_user_by_username(username.strip())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_admin = user.get("role") == "admin"
    used_profiles = await storage.count_profiles(None if is_admin else {"user_id": user["id"]})
    return AuthSessionResponse(
        user_auth_enabled=True,
        authenticated=True,
        token="",
        username=user["username"],
        role=user.get("role", "user"),
        plan_id=user.get("plan_id", "free"),
        max_profiles=user.get("max_profiles", 10),
        used_profiles=used_profiles,
        max_concurrent=user.get("max_concurrent", 2),
        expires_at=user.get("expires_at"),
        status=user.get("status", "active"),
    )


@router.get(
    "/auth/session",
    response_model=AuthSessionResponse,
    operation_id="get_auth_session",
    summary="Report the caller's authentication state.",
    description=(
        "Whether user login is enabled on this instance and whether this request "
        "carries a valid session. Reachable without authentication."
    ),
)
async def get_auth_session(request: Request, response: Response) -> AuthSessionResponse:
    """Report whether login is required and whether the caller is logged in."""
    storage = get_storage_manager()
    settings = get_settings()

    token = auth.extract_session_token(request)
    if token:
        username = await auth.validate_session(storage, token)
        if username:
            user = await storage.get_user_by_username(username)
            if user:
                # If connected to cloud server, sync latest user plan & quota
                if settings.cloud_server and settings.cloud_server.strip():
                    cloud_url = settings.cloud_server.rstrip("/")
                    try:
                        def _fetch_cloud_user():
                            req = urllib.request.Request(
                                f"{cloud_url}/api/v1/auth/user-profile?username={username}",
                                headers={
                                    "User-Agent": "CamouHub-Desktop",
                                    "Connection": "close",
                                },
                            )
                            with urllib.request.urlopen(req, timeout=3.5) as resp:
                                if resp.status == 200:
                                    return json.loads(resp.read().decode())
                            return None

                        cloud_data = await asyncio.to_thread(_fetch_cloud_user)
                        if cloud_data and cloud_data.get("authenticated"):
                            await storage.update_user_admin(
                                username=username,
                                role=cloud_data.get("role", user.get("role", "user")),
                                plan_id=cloud_data.get("plan_id", user.get("plan_id", "free")),
                                max_profiles=cloud_data.get("max_profiles", user.get("max_profiles", 10)),
                                max_concurrent=cloud_data.get("max_concurrent", user.get("max_concurrent", 2)),
                                expires_at=cloud_data.get("expires_at", user.get("expires_at")),
                                status=cloud_data.get("status", user.get("status", "active")),
                            )
                            user = await storage.get_user_by_username(username)
                    except Exception as exc:
                        logger.debug(f"Cloud user profile sync skipped: {exc}")

                # Ensure the cookie is refreshed in the browser
                _set_session_cookie(request, response, token)
                is_admin = user.get("role") == "admin"
                used_profiles = await storage.count_profiles(None if is_admin else {"user_id": user["id"]})
                return AuthSessionResponse(
                    user_auth_enabled=True,
                    authenticated=True,
                    token=token,
                    username=username,
                    role=user.get("role", "user"),
                    plan_id=user.get("plan_id", "free"),
                    max_profiles=user.get("max_profiles", 10),
                    used_profiles=used_profiles,
                    max_concurrent=user.get("max_concurrent", 2),
                    expires_at=user.get("expires_at"),
                    status=user.get("status", "active"),
                )

    # In cloud-connected mode, always require authentication
    return AuthSessionResponse(
        user_auth_enabled=True,
        authenticated=False,
        username=None,
    )


