"""Cloudflare R2 Zero-Config Cloud Sync for Browser Profiles.

Provides fast, lightweight, and encrypted session snapshots (Cookies, LocalStorage,
IndexedDB, Preferences, and Metadata) uploaded and restored via AWS SigV4.
"""

import asyncio
import datetime
import hashlib
import hmac
import io
import json
import tarfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from loguru import logger

# Cloudflare R2 Credentials (same bucket as kernel infrastructure)
R2_ACCESS_KEY_ID = "9f12c91813dddea0d5fe6c63963dadf5"
R2_SECRET_ACCESS_KEY = "6ae268a165e49f6c05de633b037177606bef740ff991ab7db9c29f9254d2f4a1"
R2_HOST = "a416a58f6b1d69a87d52bf0c70c27163.r2.cloudflarestorage.com"
R2_BUCKET = "tikmatrix"
R2_PREFIX = "camoufox/cloud_profiles"


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = _sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region_name)
    k_service = _sign(k_region, service_name)
    return _sign(k_service, "aws4_request")


def _make_r2_sigv4_request(
    method: str, canonical_uri: str, body: bytes = b"", content_type: str = "application/octet-stream"
) -> urllib.request.Request:
    t = datetime.datetime.now(datetime.timezone.utc)
    amzdate = t.strftime("%Y%m%dT%H%M%SZ")
    datestamp = t.strftime("%Y%m%d")
    region = "auto"
    service = "s3"

    payload_hash = hashlib.sha256(body).hexdigest()
    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{R2_HOST}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amzdate}\n"
    )
    signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"
    canonical_request = f"{method}\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{datestamp}/{region}/{service}/aws4_request"
    string_to_sign = f"{algorithm}\n{amzdate}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"

    signing_key = _get_signature_key(R2_SECRET_ACCESS_KEY, datestamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    auth_header = (
        f"{algorithm} Credential={R2_ACCESS_KEY_ID}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    req = urllib.request.Request(
        f"https://{R2_HOST}{canonical_uri}",
        data=body if method in ("PUT", "POST") else None,
        headers={
            "Host": R2_HOST,
            "Content-Type": content_type,
            "x-amz-date": amzdate,
            "x-amz-content-sha256": payload_hash,
            "Authorization": auth_header,
        },
        method=method,
    )
    return req


def pack_profile_snapshot(profile_dir: Path, profile_meta: dict[str, Any]) -> bytes:
    """Create a lightweight compressed snapshot containing session cookies, storage, and metadata."""
    buf = io.BytesIO()

    # Chromium paths (with SQLite WAL files)
    chromium_paths = [
        "Default/Network/Cookies",
        "Default/Network/Cookies-wal",
        "Default/Network/Cookies-shm",
        "Default/Cookies",
        "Default/Cookies-wal",
        "Default/Cookies-shm",
        "Default/Preferences",
        "Default/Web Data",
        "Default/Web Data-wal",
        "Default/Web Data-shm",
        "Default/Local Storage",
        "Default/IndexedDB",
        "Default/Session Storage",
    ]

    # Firefox / Camoufox paths
    firefox_paths = [
        "cookies.sqlite",
        "cookies.sqlite-wal",
        "cookies.sqlite-shm",
        "places.sqlite",
        "places.sqlite-wal",
        "places.sqlite-shm",
        "key4.db",
        "logins.json",
        "prefs.js",
        "storage/default",
        "sessionstore.jsonlz4",
    ]

    include_rel_paths = chromium_paths + firefox_paths

    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # Add profile metadata (with default=str for datetime/UUID objects)
        meta_json = json.dumps(profile_meta, default=str, indent=2, ensure_ascii=False).encode("utf-8")
        meta_tarinfo = tarfile.TarInfo(name="profile_meta.json")
        meta_tarinfo.size = len(meta_json)
        meta_tarinfo.mtime = int(datetime.datetime.now().timestamp())
        tar.addfile(meta_tarinfo, io.BytesIO(meta_json))

        # Add profile directory files
        if profile_dir.is_dir():
            for rel in include_rel_paths:
                p = profile_dir / rel
                if p.is_file():
                    tar.add(str(p), arcname=rel)
                elif p.is_dir():
                    tar.add(str(p), arcname=rel)

    buf.seek(0)
    return buf.getvalue()


def unpack_profile_snapshot(tar_bytes: bytes, profile_dir: Path) -> dict[str, Any]:
    """Unpack a compressed snapshot into the profile directory and return profile metadata."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(tar_bytes)
    meta: dict[str, Any] = {}

    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.name == "profile_meta.json":
                f = tar.extractfile(member)
                if f:
                    meta = json.loads(f.read().decode("utf-8"))
            else:
                tar.extract(member, path=str(profile_dir))

    return meta


def generate_r2_presigned_url(method: str, canonical_uri: str, expires_in: int = 300) -> str:
    """Generate AWS SigV4 presigned URL for direct S3/R2 client download/upload."""
    import urllib.parse

    t = datetime.datetime.now(datetime.timezone.utc)
    amzdate = t.strftime("%Y%m%dT%H%M%SZ")
    datestamp = t.strftime("%Y%m%d")
    region = "auto"
    service = "s3"

    uri = canonical_uri if canonical_uri.startswith("/") else f"/{canonical_uri}"
    credential_scope = f"{datestamp}/{region}/{service}/aws4_request"
    credential = f"{R2_ACCESS_KEY_ID}/{credential_scope}"

    query_params = {
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": credential,
        "X-Amz-Date": amzdate,
        "X-Amz-Expires": str(expires_in),
        "X-Amz-SignedHeaders": "host",
    }
    sorted_params = sorted(query_params.items())
    canonical_query = urllib.parse.urlencode(sorted_params, quote_via=urllib.parse.quote)

    canonical_headers = f"host:{R2_HOST}\n"
    signed_headers = "host"
    payload_hash = "UNSIGNED-PAYLOAD"

    canonical_request = (
        f"{method}\n"
        f"{uri}\n"
        f"{canonical_query}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    algorithm = "AWS4-HMAC-SHA256"
    string_to_sign = (
        f"{algorithm}\n"
        f"{amzdate}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    signing_key = _get_signature_key(R2_SECRET_ACCESS_KEY, datestamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    return f"https://{R2_HOST}{uri}?{canonical_query}&X-Amz-Signature={signature}"


async def upload_profile_to_r2(
    profile_id: str, profile_dir: Path, profile_meta: dict[str, Any], pm: Any = None
) -> dict[str, Any]:
    """Compress and upload a profile snapshot to Cloudflare R2, keeping snapshot history."""
    import uuid

    snapshot_bytes = pack_profile_snapshot(profile_dir, profile_meta)
    size_kb = round(len(snapshot_bytes) / 1024, 1)

    # 1. Main snapshot pointer (latest)
    uri = f"/{R2_BUCKET}/{R2_PREFIX}/{profile_id}/snapshot.tar.gz"
    req = _make_r2_sigv4_request("PUT", uri, body=snapshot_bytes, content_type="application/gzip")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status in (200, 204):
                logger.info(f"Successfully uploaded latest profile {profile_id} to R2 ({size_kb} KB)")
    except Exception as exc:
        logger.error(f"Failed to upload profile {profile_id} to R2: {exc}")
        return {"success": False, "error": str(exc), "profile_id": profile_id}

    # 2. Historical versioned snapshot (时光机)
    snap_suffix = uuid.uuid4().hex[:8]
    time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    history_key = f"{R2_PREFIX}/{profile_id}/snapshots/snapshot_{time_str}_{snap_suffix}.tar.gz"
    history_uri = f"/{R2_BUCKET}/{history_key}"
    req_hist = _make_r2_sigv4_request(
        "PUT", history_uri, body=snapshot_bytes, content_type="application/gzip"
    )

    try:
        with urllib.request.urlopen(req_hist, timeout=30) as resp:
            if resp.status in (200, 204):
                logger.info(f"Recorded historical snapshot in R2: {history_key}")
    except Exception as exc:
        logger.warning(f"Failed to upload historical snapshot copy: {exc}")

    # 3. Record in database if pm is provided
    snapshot_record = None
    if pm:
        try:
            snapshot_name = f"快照 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            snapshot_record = await pm.storage.record_profile_snapshot(
                profile_id=profile_id,
                snapshot_name=snapshot_name,
                size_kb=size_kb,
                r2_key=history_key,
            )
        except Exception as exc:
            logger.warning(f"Failed to record profile snapshot in database: {exc}")

    return {
        "success": True,
        "profile_id": profile_id,
        "size_kb": size_kb,
        "uploaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "snapshot": snapshot_record,
    }


async def download_profile_from_r2(profile_id: str, profile_dir: Path) -> dict[str, Any]:
    """Download and extract the latest profile snapshot from Cloudflare R2."""
    uri = f"/{R2_BUCKET}/{R2_PREFIX}/{profile_id}/snapshot.tar.gz"
    req = _make_r2_sigv4_request("GET", uri)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                tar_bytes = resp.read()
                size_kb = round(len(tar_bytes) / 1024, 1)
                meta = unpack_profile_snapshot(tar_bytes, profile_dir)
                logger.info(f"Successfully restored profile {profile_id} from R2 ({size_kb} KB)")
                return {
                    "success": True,
                    "profile_id": profile_id,
                    "size_kb": size_kb,
                    "meta": meta,
                }
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"success": False, "error": "Cloud backup not found for this profile", "profile_id": profile_id}
        logger.error(f"Failed to download profile {profile_id} from R2: {exc}")
        return {"success": False, "error": str(exc), "profile_id": profile_id}
    except Exception as exc:
        logger.error(f"Failed to download profile {profile_id} from R2: {exc}")
        return {"success": False, "error": str(exc), "profile_id": profile_id}

    return {"success": False, "error": "Unknown download error", "profile_id": profile_id}


async def download_snapshot_from_key(r2_key: str, profile_dir: Path) -> dict[str, Any]:
    """Download and extract a specific profile snapshot from Cloudflare R2 by key."""
    canonical_key = r2_key.lstrip("/")
    if not canonical_key.startswith(R2_BUCKET):
        uri = f"/{R2_BUCKET}/{canonical_key}"
    else:
        uri = f"/{canonical_key}"

    req = _make_r2_sigv4_request("GET", uri)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                tar_bytes = resp.read()
                size_kb = round(len(tar_bytes) / 1024, 1)
                meta = unpack_profile_snapshot(tar_bytes, profile_dir)
                logger.info(f"Successfully restored snapshot {r2_key} ({size_kb} KB)")
                return {
                    "success": True,
                    "r2_key": r2_key,
                    "size_kb": size_kb,
                    "meta": meta,
                }
    except Exception as exc:
        logger.error(f"Failed to download snapshot {r2_key}: {exc}")
        return {"success": False, "error": str(exc), "r2_key": r2_key}

    return {"success": False, "error": "Unknown error restoring snapshot", "r2_key": r2_key}


async def check_cloud_snapshot_exists(profile_id: str) -> bool:
    """Check if a cloud snapshot exists in Cloudflare R2."""
    uri = f"/{R2_BUCKET}/{R2_PREFIX}/{profile_id}/snapshot.tar.gz"
    req = _make_r2_sigv4_request("HEAD", uri)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


async def auto_pull_profile_snapshot(profile_id: str, profile_dir: Path, pm: Any = None) -> dict[str, Any]:
    """Auto pull profile snapshot if available in cloud, updating database status."""
    logger.info(f"Auto-Pull: Checking cloud snapshot for profile {profile_id}")
    res = await download_profile_from_r2(profile_id, profile_dir)
    if res.get("success") and pm:
        try:
            meta = res.get("meta")
            if meta and isinstance(meta, dict):
                existing = await pm.get_profile(profile_id)
                if existing:
                    await pm.storage.set_cloud_sync_status(
                        profile_id, "synced", size_kb=res.get("size_kb")
                    )
        except Exception as exc:
            logger.warning(f"Failed to update metadata during auto pull: {exc}")
    return res


async def auto_push_profile_snapshot(
    profile_id: str, profile_dir: Path, profile_meta: dict[str, Any], pm: Any = None
) -> dict[str, Any]:
    """Auto push profile snapshot with SQLite WAL quiet period and status tracking."""
    from .event_bus import event_bus

    if pm:
        try:
            await pm.storage.set_cloud_sync_status(profile_id, "syncing")
            await event_bus.broadcast("PROFILE_SYNC_COMPLETED", {
                "profile_id": profile_id,
                "sync_status": "syncing",
            })
        except Exception:
            pass

    # Wait 500ms for browser sub-processes to finish SQLite WAL flushing
    await asyncio.sleep(0.5)

    res = await upload_profile_to_r2(profile_id, profile_dir, profile_meta, pm=pm)
    sync_status = "synced" if res.get("success") else "failed"
    if pm:
        try:
            await pm.storage.set_cloud_sync_status(
                profile_id, sync_status, size_kb=res.get("size_kb")
            )
        except Exception as exc:
            logger.warning(f"Failed to update sync status in storage: {exc}")

    try:
        await event_bus.broadcast("PROFILE_SYNC_COMPLETED", {
            "profile_id": profile_id,
            "sync_status": sync_status,
            "size_kb": res.get("size_kb"),
        })
    except Exception:
        pass

    return res

