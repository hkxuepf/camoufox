"""Admin management API routes for user administration, plans, USDT orders, and system settings."""

from datetime import datetime, timedelta
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from camoufox_pm.api.dependencies import (
    get_profile_manager,
    get_storage_manager,
    require_admin,
)
from camoufox_pm.api.models.system import ApiResponse
from camoufox_pm.core import auth

router = APIRouter(dependencies=[Depends(require_admin)])


class AdminUserCreateRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)
    role: str = Field("user", description="user or admin")
    plan_id: str = Field("free")
    max_profiles: int = Field(10, ge=1)
    max_concurrent: int = Field(2, ge=1)
    duration_days: int | None = Field(30, description="Add days to expiration")


class AdminUserUpdateRequest(BaseModel):
    role: str | None = None
    plan_id: str | None = None
    max_profiles: int | None = None
    max_concurrent: int | None = None
    expires_at: str | None = None
    status: str | None = None


class AdminResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=6)


class PlanUpsertRequest(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    max_profiles: int = Field(..., ge=1)
    max_concurrent: int = Field(..., ge=1)
    duration_days: int = Field(..., ge=1)
    price_usdt: float = Field(..., ge=0)
    description: str | None = None


class AdminSettingsUpdateRequest(BaseModel):
    usdt_wallet_address: str | None = None
    usdt_network: str | None = None
    payment_gateway_url: str | None = None
    payment_gateway_secret: str | None = None


# --- Dashboard Stats ---

@router.get("/admin/dashboard", response_model=ApiResponse[dict[str, Any]])
async def get_dashboard():
    """Retrieve administrator overview statistics."""
    storage = get_storage_manager()
    stats = await storage.get_admin_dashboard_stats()
    return ApiResponse(success=True, data=stats)


# --- User Management ---

@router.get("/admin/users", response_model=ApiResponse[list[dict[str, Any]]])
async def list_admin_users():
    """List all registered users with their quota and profile usage."""
    storage = get_storage_manager()
    users = await storage.list_users()

    enriched_users = []
    for user in users:
        used_profiles = await storage.count_profiles({"user_id": user["id"]})
        user_copy = dict(user)
        user_copy["used_profiles"] = used_profiles
        enriched_users.append(user_copy)

    return ApiResponse(success=True, data=enriched_users)


@router.post("/admin/users", response_model=ApiResponse[dict[str, Any]])
async def create_admin_user(body: AdminUserCreateRequest):
    """Create a new user manually."""
    storage = get_storage_manager()
    existing = await storage.get_user_by_username(body.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在 / Username already exists")

    user_id = secrets.token_hex(8)
    password_hash = auth.hash_password(body.password)

    expires_at = None
    if body.duration_days and body.duration_days > 0:
        expires_at = (datetime.now() + timedelta(days=body.duration_days)).isoformat()

    await storage.create_user(
        user_id=user_id,
        username=body.username,
        password_hash=password_hash,
        role=body.role,
        plan_id=body.plan_id,
        max_profiles=body.max_profiles,
        max_concurrent=body.max_concurrent,
        expires_at=expires_at,
    )

    return ApiResponse(
        success=True,
        message="User created successfully",
        data={"id": user_id, "username": body.username},
    )


@router.put("/admin/users/{username}", response_model=ApiResponse[bool])
async def update_admin_user(username: str, body: AdminUserUpdateRequest):
    """Update user quota, plan, role or status."""
    storage = get_storage_manager()
    user = await storage.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updated = await storage.update_user_admin(
        username=username,
        role=body.role,
        plan_id=body.plan_id,
        max_profiles=body.max_profiles,
        max_concurrent=body.max_concurrent,
        expires_at=body.expires_at,
        status=body.status,
    )
    return ApiResponse(success=updated, data=updated)


@router.post("/admin/users/{username}/reset-password", response_model=ApiResponse[bool])
async def reset_user_password(username: str, body: AdminResetPasswordRequest):
    """Reset user password."""
    storage = get_storage_manager()
    user = await storage.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    password_hash = auth.hash_password(body.password)
    updated = await storage.update_user_password(username, password_hash)
    return ApiResponse(success=updated, message="Password reset successfully", data=updated)


@router.delete("/admin/users/{username}", response_model=ApiResponse[bool])
async def delete_admin_user(username: str):
    """Delete a user account."""
    if username in ("admin", "fgwl"):
        raise HTTPException(status_code=400, detail="Cannot delete super administrator")

    storage = get_storage_manager()
    deleted = await storage.delete_user(username)
    return ApiResponse(success=deleted, message="User deleted", data=deleted)


# --- Plans Management ---

@router.get("/admin/plans", response_model=ApiResponse[list[dict[str, Any]]])
async def list_admin_plans():
    """List subscription tiers."""
    storage = get_storage_manager()
    plans = await storage.list_plans()
    return ApiResponse(success=True, data=plans)


@router.post("/admin/plans", response_model=ApiResponse[bool])
async def save_admin_plan(body: PlanUpsertRequest):
    """Create or update a subscription plan."""
    storage = get_storage_manager()
    await storage.save_plan(body.model_dump())
    return ApiResponse(success=True, message="Plan saved", data=True)


@router.delete("/admin/plans/{plan_id}", response_model=ApiResponse[bool])
async def delete_admin_plan(plan_id: str):
    """Delete a subscription plan."""
    if plan_id == "free":
        raise HTTPException(status_code=400, detail="Cannot delete default free plan")
    storage = get_storage_manager()
    deleted = await storage.delete_plan(plan_id)
    return ApiResponse(success=deleted, message="Plan deleted", data=deleted)


# --- Orders Management ---

@router.get("/admin/orders", response_model=ApiResponse[list[dict[str, Any]]])
async def list_admin_orders():
    """List recent USDT payment orders."""
    storage = get_storage_manager()
    orders = await storage.list_orders(limit=200)
    return ApiResponse(success=True, data=orders)


@router.post("/admin/orders/{order_no}/confirm", response_model=ApiResponse[bool])
async def confirm_order_manually(order_no: str):
    """Manually approve and fulfill an order (补单/确认到账)."""
    storage = get_storage_manager()
    order = await storage.get_order(order_no)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["status"] == "paid":
        return ApiResponse(success=True, message="Order already paid", data=True)

    # 1. Update order status to paid
    await storage.update_order_status(order_no, "paid")

    # 2. Upgrade the user's plan and expiration
    user = await storage.get_user_by_id(order["user_id"])
    if not user:
        user = await storage.get_user_by_username(order["username"])

    if user:
        plan = await storage.get_plan(order["plan_id"])
        duration_days = plan["duration_days"] if plan else 30
        max_profiles = plan["max_profiles"] if plan else 20
        max_concurrent = plan["max_concurrent"] if plan else 2

        # Calculate new expires_at
        now = datetime.now()
        current_exp = None
        if user.get("expires_at"):
            try:
                parsed = datetime.fromisoformat(user["expires_at"])
                if parsed > now:
                    current_exp = parsed
            except Exception:
                pass

        base_time = current_exp if current_exp else now
        new_expires_at = (base_time + timedelta(days=duration_days)).isoformat()

        await storage.update_user_admin(
            username=user["username"],
            plan_id=order["plan_id"],
            max_profiles=max_profiles,
            max_concurrent=max_concurrent,
            expires_at=new_expires_at,
            status="active",
        )
        logger.info(
            f"Order {order_no} manually confirmed: User {user['username']} upgraded to {order['plan_id']}, expires at {new_expires_at}"
        )

    return ApiResponse(success=True, message="Order confirmed and plan activated", data=True)


# --- Admin Payment Settings ---

@router.get("/admin/settings", response_model=ApiResponse[dict[str, str]])
async def get_admin_settings():
    """Retrieve payment and gateway configuration."""
    storage = get_storage_manager()
    settings = await storage.get_admin_settings()
    return ApiResponse(success=True, data=settings)


@router.post("/admin/settings", response_model=ApiResponse[bool])
async def update_admin_settings(body: AdminSettingsUpdateRequest):
    """Update USDT wallet address and payment gateway settings."""
    storage = get_storage_manager()
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        if value is not None:
            await storage.update_admin_setting(key, value)
    return ApiResponse(success=True, message="Settings updated", data=True)
