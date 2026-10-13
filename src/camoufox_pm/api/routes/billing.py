"""Billing and USDT payment routes for user subscriptions."""

from datetime import datetime, timedelta
import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field

from camoufox_pm.api.dependencies import (
    get_current_user,
    get_storage_manager,
    require_auth,
)
from camoufox_pm.api.models.system import ApiResponse

router = APIRouter()


class CreateOrderRequest(BaseModel):
    plan_id: str = Field(..., min_length=1)


class SubmitTxRequest(BaseModel):
    tx_hash: str = Field(..., min_length=5)


class WebhookPayload(BaseModel):
    order_no: str
    status: str = "paid"
    tx_hash: str | None = None
    secret: str | None = None


@router.get("/billing/plans", response_model=ApiResponse[list[dict[str, Any]]])
async def list_available_plans():
    """List subscription tiers available for purchase."""
    storage = get_storage_manager()
    plans = await storage.list_plans()
    return ApiResponse(success=True, data=plans)


@router.get(
    "/billing/orders",
    response_model=ApiResponse[list[dict[str, Any]]],
    dependencies=[Depends(require_auth)],
)
async def list_user_orders(request: Request):
    """List the current user's order history."""
    storage = get_storage_manager()
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    orders = await storage.list_orders(user_id=user["id"], limit=50)
    return ApiResponse(success=True, data=orders)


@router.post(
    "/billing/orders",
    response_model=ApiResponse[dict[str, Any]],
    dependencies=[Depends(require_auth)],
)
async def create_usdt_order(request: Request, body: CreateOrderRequest):
    """Create a new USDT order to purchase or renew a subscription plan."""
    storage = get_storage_manager()
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    plan = await storage.get_plan(body.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Selected plan does not exist")

    settings = await storage.get_admin_settings()
    wallet_address = settings.get("usdt_wallet_address", "")
    network = settings.get("usdt_network", "TRC20")

    order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(2).upper()}"
    order_id = secrets.token_hex(8)

    order_data = {
        "id": order_id,
        "order_no": order_no,
        "user_id": user["id"],
        "username": user["username"],
        "plan_id": plan["id"],
        "plan_name": plan["name"],
        "amount_usdt": float(plan["price_usdt"]),
        "status": "pending",
        "pay_network": network,
        "pay_address": wallet_address,
        "tx_hash": None,
        "created_at": datetime.now().isoformat(),
    }

    created = await storage.create_order(order_data)
    logger.info(
        f"USDT Order {order_no} created for user {user['username']}, amount={plan['price_usdt']} USDT ({network})"
    )

    return ApiResponse(
        success=True,
        message="Order created successfully",
        data=created,
    )


@router.get(
    "/billing/orders/{order_no}",
    response_model=ApiResponse[dict[str, Any]],
    dependencies=[Depends(require_auth)],
)
async def get_order_status(order_no: str, request: Request):
    """Check status of a specific order."""
    storage = get_storage_manager()
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    order = await storage.get_order(order_no)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Non-admin users can only view their own orders
    if user.get("role") != "admin" and order["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    return ApiResponse(success=True, data=order)


@router.post(
    "/billing/orders/{order_no}/submit-tx",
    response_model=ApiResponse[bool],
    dependencies=[Depends(require_auth)],
)
async def submit_order_tx_hash(order_no: str, body: SubmitTxRequest, request: Request):
    """User submits transaction hash after transferring USDT for verification."""
    storage = get_storage_manager()
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    order = await storage.get_order(order_no)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if user.get("role") != "admin" and order["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Update order with tx_hash
    await storage.update_order_status(order_no, "pending", tx_hash=body.tx_hash.strip())
    logger.info(f"User {user['username']} submitted TxHash for order {order_no}: {body.tx_hash}")

    return ApiResponse(
        success=True,
        message="Transaction submitted. Please allow a few minutes for network confirmations.",
        data=True,
    )


@router.post("/billing/webhook", response_model=ApiResponse[bool])
async def billing_payment_webhook(payload: WebhookPayload):
    """Payment gateway webhook to automatically verify and fulfill orders."""
    storage = get_storage_manager()
    settings = await storage.get_admin_settings()
    configured_secret = settings.get("payment_gateway_secret")

    if configured_secret and payload.secret != configured_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret signature")

    order = await storage.get_order(payload.order_no)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["status"] == "paid":
        return ApiResponse(success=True, message="Order already paid", data=True)

    if payload.status == "paid":
        await storage.update_order_status(payload.order_no, "paid", tx_hash=payload.tx_hash)

        # Fulfill plan upgrade
        user = await storage.get_user_by_id(order["user_id"])
        if user:
            plan = await storage.get_plan(order["plan_id"])
            duration_days = plan["duration_days"] if plan else 30
            max_profiles = plan["max_profiles"] if plan else 20
            max_concurrent = plan["max_concurrent"] if plan else 2

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
                f"Order {payload.order_no} webhook fulfilled: User {user['username']} plan updated"
            )

    return ApiResponse(success=True, data=True)
