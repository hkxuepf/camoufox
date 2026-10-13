"""API routes for Proxy Pool Management."""

import asyncio
import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from camoufox_pm.api.dependencies import get_storage_manager
from camoufox_pm.core.models import ProxyConfig, ProxyType
from camoufox_pm.core.proxy_check import locate, resolve_exit_ip

router = APIRouter()


class ProxyCreateRequest(BaseModel):
    name: str | None = None
    type: str = "http"
    server: str
    port: int | None = None
    username: str | None = None
    password: str | None = None


class ProxyUpdateRequest(BaseModel):
    name: str | None = None
    type: str | None = None
    server: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None


class BatchImportRequest(BaseModel):
    content: str | None = None
    default_type: str = "http"
    proxies: list[dict[str, Any]] | None = None


class BatchDeleteRequest(BaseModel):
    ids: list[str]


class BatchCheckRequest(BaseModel):
    ids: list[str] | None = None


def parse_proxy_line(line: str, default_type: str = "http") -> dict[str, Any] | None:
    """Parse common proxy string formats:
    - ip:port:user:pass
    - ip:port
    - protocol://user:pass@ip:port
    - protocol://ip:port
    - user:pass@ip:port
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    ptype = default_type.lower()

    # Check URI format
    uri_match = re.match(r"^([a-zA-Z0-9]+)://(?:([^:@]+):([^@]+)@)?([^:]+):(\d+)$", line)
    if uri_match:
        return {
            "type": uri_match.group(1).lower(),
            "username": uri_match.group(2),
            "password": uri_match.group(3),
            "server": uri_match.group(4),
            "port": int(uri_match.group(5)),
        }

    # user:pass@ip:port
    auth_match = re.match(r"^([^:@]+):([^@]+)@([^:]+):(\d+)$", line)
    if auth_match:
        return {
            "type": ptype,
            "username": auth_match.group(1),
            "password": auth_match.group(2),
            "server": auth_match.group(3),
            "port": int(auth_match.group(4)),
        }

    # Colon-separated: ip:port:user:pass or ip:port
    parts = line.split(":")
    if len(parts) == 4:
        # ip:port:user:pass
        try:
            return {
                "type": ptype,
                "server": parts[0].strip(),
                "port": int(parts[1].strip()),
                "username": parts[2].strip() or None,
                "password": parts[3].strip() or None,
            }
        except ValueError:
            return None
    elif len(parts) == 2:
        # ip:port
        try:
            return {
                "type": ptype,
                "server": parts[0].strip(),
                "port": int(parts[1].strip()),
                "username": None,
                "password": None,
            }
        except ValueError:
            return None

    return None


@router.get("/proxies")
async def list_proxies():
    """List all proxies in the pool."""
    storage = get_storage_manager()
    proxies = await storage.list_proxies()
    return {"proxies": proxies, "total": len(proxies)}


@router.post("/proxies", status_code=status.HTTP_201_CREATED)
async def create_proxy_endpoint(request: ProxyCreateRequest):
    """Create a single proxy."""
    storage = get_storage_manager()
    # If server contains port like 127.0.0.1:8080 and port is not specified
    server = request.server.strip()
    port = request.port
    if ":" in server and not port:
        parts = server.split(":")
        server = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            pass

    proxy = await storage.create_proxy(
        {
            "name": request.name,
            "type": request.type,
            "server": server,
            "port": port or 80,
            "username": request.username,
            "password": request.password,
        }
    )
    return proxy


@router.post("/proxies/batch")
async def batch_import_proxies(request: BatchImportRequest):
    """Batch import proxies from raw multiline text or JSON objects."""
    storage = get_storage_manager()
    parsed_list: list[dict[str, Any]] = []

    if request.proxies:
        for p in request.proxies:
            parsed_list.append(
                {
                    "name": p.get("name"),
                    "type": p.get("type", request.default_type),
                    "server": p.get("server", ""),
                    "port": int(p.get("port", 80)),
                    "username": p.get("username"),
                    "password": p.get("password"),
                }
            )

    if request.content:
        for line in request.content.splitlines():
            item = parse_proxy_line(line, request.default_type)
            if item:
                parsed_list.append(item)

    if not parsed_list:
        raise HTTPException(status_code=400, detail="未解析到有效代理，请检查格式 (如 ip:port:user:pass)")

    count = await storage.batch_create_proxies(parsed_list)
    return {"imported": count}


@router.put("/proxies/{proxy_id}")
async def update_proxy_endpoint(proxy_id: str, request: ProxyUpdateRequest):
    """Update proxy configuration."""
    storage = get_storage_manager()
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        return {"updated": False}
    ok = await storage.update_proxy(proxy_id, updates)
    if not ok:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return {"updated": True}


@router.delete("/proxies/{proxy_id}")
async def delete_proxy_endpoint(proxy_id: str):
    """Delete a proxy."""
    storage = get_storage_manager()
    ok = await storage.delete_proxy(proxy_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return {"deleted": True}


@router.post("/proxies/batch-delete")
async def batch_delete_proxies(request: BatchDeleteRequest):
    """Batch delete proxies by IDs."""
    storage = get_storage_manager()
    count = await storage.delete_proxies_batch(request.ids)
    return {"deleted": count}


async def _do_check_single_proxy(proxy_data: dict, storage) -> dict:
    """Helper to test a single proxy and update its record."""
    proxy_id = proxy_data["id"]
    ptype = proxy_data.get("type", "http").lower()
    server = proxy_data.get("server", "")
    port = proxy_data.get("port")
    server_addr = f"{server}:{port}" if port else server

    try:
        enum_type = ProxyType(ptype)
    except Exception:
        enum_type = ProxyType.HTTP

    cfg = ProxyConfig(
        type=enum_type,
        server=server_addr,
        username=proxy_data.get("username"),
        password=proxy_data.get("password"),
    )

    try:
        ip, latency = await resolve_exit_ip(cfg, timeout=6.0)
        country = None
        try:
            loc = await asyncio.to_thread(locate, ip)
            country = loc.country
        except Exception:
            pass

        updates = {
            "status": "active",
            "latency_ms": latency,
            "ip": ip,
            "country": country,
            "city": None,
            "last_checked_at": datetime.now().isoformat(),
        }
    except Exception as exc:
        updates = {
            "status": "failed",
            "latency_ms": None,
            "last_checked_at": datetime.now().isoformat(),
        }

    await storage.update_proxy(proxy_id, updates)
    return {"id": proxy_id, **updates}


@router.post("/proxies/{proxy_id}/check")
async def check_single_proxy_endpoint(proxy_id: str):
    """Test single proxy and update latency/status."""
    storage = get_storage_manager()
    proxy = await storage.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    result = await _do_check_single_proxy(proxy, storage)
    return result


@router.post("/proxies/batch-check")
async def batch_check_proxies_endpoint(request: BatchCheckRequest):
    """Concurrently test multiple proxies."""
    storage = get_storage_manager()
    all_proxies = await storage.list_proxies()

    if request.ids:
        targets = [p for p in all_proxies if p["id"] in set(request.ids)]
    else:
        targets = all_proxies

    if not targets:
        return {"checked": 0, "results": []}

    sem = asyncio.Semaphore(10)

    async def _worker(p):
        async with sem:
            return await _do_check_single_proxy(p, storage)

    tasks = [_worker(p) for p in targets]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid_results = [r for r in results if isinstance(r, dict)]

    return {"checked": len(valid_results), "results": valid_results}
