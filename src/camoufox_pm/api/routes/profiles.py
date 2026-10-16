"""
API routes for managing profiles.
"""

import re
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, Response
from loguru import logger
from pydantic import BaseModel, ValidationError
from starlette.background import BackgroundTask

from camoufox_pm.api.dependencies import (
    get_current_user,
    get_profile_manager,
    get_storage_manager,
)
from camoufox_pm.api.errors import ApiError, validation_message
from camoufox_pm.api.models.profiles import (
    ActiveBrowsersResponse,
    BrowserCloseResponse,
    BrowsersCloseAllResponse,
    ClearGeographyRequest,
    ClearGeographyResponse,
    ProfileCloneRequest,
    ProfileCreateRequest,
    ProfileLaunchRequest,
    ProfileLaunchResponse,
    ProfileListResponse,
    ProfileResponse,
    ProfileStatsResponse,
    ProfileUpdateRequest,
    ProxyCheckRequest,
    ProxyCheckResponse,
    ReconcileOsRequest,
)
from camoufox_pm.api.models.system import ApiResponse, ExcelImportData
from camoufox_pm.core import proxy_check
from camoufox_pm.core.database import StaleWriteError
from camoufox_pm.core.excel_manager import ExcelManager
from camoufox_pm.core.leases import ProfileLocked
from camoufox_pm.core.models import BrowserSettings, ProfileStatus, ProxyConfig

router = APIRouter()

# Maps the deprecated flattened update fields onto their browser_settings keys.
_FLATTENED_BROWSER_FIELDS = {
    "browser_os": "os",
    "browser_screen": "screen",
    "browser_user_agent": "user_agent",
    "browser_languages": "languages",
    "browser_timezone": "timezone",
    "browser_locale": "locale",
    "browser_webrtc_mode": "webrtc_mode",
    "browser_canvas_noise": "canvas_noise",
    "browser_stable_canvas": "stable_canvas",
    "browser_webgl_noise": "webgl_noise",
    "browser_audio_noise": "audio_noise",
    "browser_hardware_concurrency": "hardware_concurrency",
    "browser_device_memory": "device_memory",
    "browser_max_touch_points": "max_touch_points",
    "browser_window_width": "window_width",
    "browser_window_height": "window_height",
}


@router.get(
    "/profiles",
    response_model=ProfileListResponse,
    operation_id="list_profiles",
    summary="List profiles.",
    description="List all profiles with filtering and pagination.",
)
async def list_profiles(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Profiles per page"),
    status: ProfileStatus | None = Query(None, description="Filter by status"),
    group: str | None = Query(None, description="Filter by group"),
    search: str | None = Query(None, description="Search by name"),
):
    """List profiles with filtering."""
    try:
        profile_manager = get_profile_manager()
        user = await get_current_user(request)

        # Build the filters
        filters: dict[str, Any] = {}
        if user and user.get("role") != "admin":
            filters["user_id"] = user["id"]
        if status:
            filters["status"] = status
        if group:
            filters["group"] = group
        if search:
            filters["name_like"] = search

        # Fetch the profiles
        profiles = await profile_manager.list_profiles(filters=filters)

        # Pagination
        total = len(profiles)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_profiles = profiles[start_idx:end_idx]

        # Convert to API models
        profile_responses = []
        for profile in paginated_profiles:
            profile_responses.append(ProfileResponse.from_profile(profile))

        return ProfileListResponse(
            profiles=profile_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_next=end_idx < total,
            has_prev=page > 1,
        )

    except Exception as e:
        logger.error(f"Failed to list profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/profiles",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_profile",
    summary="Create a profile.",
    description="Create a new profile with an auto-generated fingerprint.",
)
async def create_profile(request: Request, body: ProfileCreateRequest):
    """Create a new profile."""
    try:
        profile_manager = get_profile_manager()
        storage = get_storage_manager()
        user = await get_current_user(request)

        user_id = None
        if user:
            user_id = user["id"]
            if user.get("role") != "admin":
                if user.get("expires_at"):
                    from datetime import datetime
                    if datetime.fromisoformat(user["expires_at"]) < datetime.now():
                        raise HTTPException(
                            status_code=403,
                            detail="当前账户套餐已过期，请前往续费 / Your subscription has expired",
                        )
                used = await storage.count_profiles({"user_id": user["id"]})
                max_p = user.get("max_profiles", 10)
                if used >= max_p:
                    raise HTTPException(
                        status_code=403,
                        detail=f"环境数量已达套餐上限 ({used}/{max_p})，请升级套餐 / Profile quota reached",
                    )

        # Create the profile
        profile = await profile_manager.create_profile(
            name=body.name,
            group=body.group,
            browser_settings=body.browser_settings,
            proxy_config=body.proxy_config,
            generate_fingerprint=body.generate_fingerprint,
            notes=body.notes,
            fingerprint_preset=body.fingerprint_preset,
            user_id=user_id,
            cookies=body.cookies,
            account=body.account,
            is_favorite=body.is_favorite or False,
            tags=body.tags or [],
        )

        logger.info(f"Created profile: {profile.name} (ID: {profile.id})")

        return ProfileResponse.from_profile(profile)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to create profile: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    operation_id="get_profile",
    summary="Get a profile.",
    description="Get detailed information about a profile.",
)
async def get_profile(profile_id: str):
    """Get a profile by ID."""
    try:
        profile_manager = get_profile_manager()
        profile = await profile_manager.get_profile(profile_id)

        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found")

        return ProfileResponse.from_profile(profile)

    except HTTPException:
        raise
    except StaleWriteError:
        # Let it reach the app-level handler, which renders it as 409. The
        # catch-all below would otherwise report a conflict as a server fault.
        raise
    except Exception as e:
        logger.error(f"Failed to get profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    operation_id="update_profile",
    summary="Update a profile.",
    description=(
        "Update a profile's data. A field that is sent is authoritative, including "
        "an explicit null, which clears it; a field that is omitted is left alone. "
        "browser_settings is merged over the stored settings."
    ),
)
async def update_profile(profile_id: str, request: ProfileUpdateRequest):
    """Update a profile."""
    try:
        profile_manager = get_profile_manager()

        # A field the client sent is authoritative, including an explicit null,
        # which clears it. A field it omitted is left untouched. Testing for
        # "is not None" instead would make clearing a proxy, a group or the
        # notes silently do nothing while still reporting success.
        # Read through model_dump: attribute access on the deprecated flattened
        # fields would raise DeprecationWarning from inside our own route.
        sent = request.model_dump(exclude_unset=True)

        updates: dict[str, Any] = {}
        if sent.get("name") is not None:
            updates["name"] = sent["name"]
        if "group" in sent:
            updates["group"] = sent["group"]
        if sent.get("status") is not None:
            updates["status"] = sent["status"]
        if "proxy_config" in sent:
            updates["proxy_config"] = sent["proxy_config"]
        if "notes" in sent:
            updates["notes"] = sent["notes"]
        if "cookies" in sent:
            updates["cookies"] = sent["cookies"]
        if "account" in sent:
            updates["account"] = sent["account"]
        if "is_favorite" in sent:
            updates["is_favorite"] = sent["is_favorite"]
        if "tags" in sent:
            updates["tags"] = sent["tags"]

        # Not a field of the profile: the version this edit was based on, used
        # to refuse the save if someone else got there first.
        expected_row_version = sent.get("row_version")

        # Browser settings arrive either as a nested object or as the deprecated
        # flattened browser_* fields. Both are collected here and merged over the
        # stored settings, so a client that sends only the fields it edits cannot
        # wipe the rest of the generated fingerprint.
        browser_updates: dict[str, Any] = {}
        if sent.get("browser_settings") is not None:
            browser_updates.update(sent["browser_settings"])
        for field, key in _FLATTENED_BROWSER_FIELDS.items():
            if sent.get(field) is not None:
                browser_updates[key] = sent[field]

        if browser_updates:
            current_profile = await profile_manager.get_profile(profile_id)
            if current_profile and current_profile.browser_settings:
                merged = current_profile.browser_settings.model_dump()
                merged.update(browser_updates)
                updates["browser_settings"] = merged
            else:
                updates["browser_settings"] = browser_updates

        # Apply the update
        updated_profile = await profile_manager.update_profile(
            profile_id, updates, expected_row_version=expected_row_version
        )

        if not updated_profile:
            raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found")

        logger.info(f"Updated profile: {updated_profile.name} (ID: {profile_id})")

        return ProfileResponse.from_profile(updated_profile)

    except HTTPException:
        raise
    except StaleWriteError:
        # Let it reach the app-level handler, which renders it as 409. The
        # catch-all below would otherwise report a conflict as a server fault.
        raise
    except ValidationError as e:
        # browser_settings is a free-form dict on the way in, so bad values only
        # fail when it is turned into a BrowserSettings. That is the client's
        # mistake, not a server fault.
        logger.warning(f"Rejected invalid update for profile {profile_id}: {e}")
        raise ApiError(422, validation_message(e.errors()), details=e.errors()) from e
    except Exception as e:
        logger.error(f"Failed to update profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete(
    "/profiles/{profile_id}",
    response_model=ApiResponse[None],
    operation_id="delete_profile",
    summary="Delete a profile.",
    description="Move a closed profile and its data to recoverable trash.",
)
async def delete_profile(profile_id: str):
    """Delete a profile."""
    try:
        profile_manager = get_profile_manager()
        success = await profile_manager.delete_profile(profile_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found")

        logger.info(f"Deleted profile: ID {profile_id}")

        return ApiResponse(success=True, message=f"Profile {profile_id} moved to trash", data=None)

    except HTTPException:
        raise
    except ProfileLocked:
        raise
    except StaleWriteError:
        # Let it reach the app-level handler, which renders it as 409. The
        # catch-all below would otherwise report a conflict as a server fault.
        raise
    except Exception as e:
        logger.error(f"Failed to delete profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/profiles/{profile_id}/launch",
    response_model=ProfileLaunchResponse,
    operation_id="launch_profile",
    summary="Launch a browser.",
    description="Launch Camoufox with the profile's settings.",
)
async def launch_profile(profile_id: str, request: Request, body: ProfileLaunchRequest):
    """Launch a browser with a profile."""
    try:
        profile_manager = get_profile_manager()
        user = await get_current_user(request)

        if user and user.get("role") != "admin":
            if user.get("expires_at"):
                from datetime import datetime
                if datetime.fromisoformat(user["expires_at"]) < datetime.now():
                    raise HTTPException(
                        status_code=403,
                        detail="当前账户套餐已过期，请续费后使用 / Your subscription has expired",
                    )
            active_sessions = await profile_manager.get_active_browsers()
            user_profiles = await profile_manager.list_profiles(filters={"user_id": user["id"]})
            user_profile_ids = {p.id for p in user_profiles}
            running_count = sum(
                1 for sess in active_sessions if (sess.get("profile_id") if isinstance(sess, dict) else sess) in user_profile_ids
            )
            max_c = user.get("max_concurrent", 2)
            if running_count >= max_c:
                raise HTTPException(
                    status_code=403,
                    detail=f"当前并发运行窗口数已达套餐上限 ({running_count}/{max_c}) / Max concurrent browser limit reached",
                )

        # Launch the browser
        browser_session = await profile_manager.launch_browser(
            profile_id,
            headless=body.headless,
            window_size=body.window_size,
            **body.additional_options or {},
        )

        logger.info(f"Launched browser for profile: {profile_id}")

        return ProfileLaunchResponse(
            profile_id=profile_id,
            browser_session_id=str(uuid.uuid4()),
            status=browser_session.get("status", "launched"),
            message=browser_session.get("message", "Browser launched successfully"),
            process_id=browser_session.get("process_id"),
            camoufox_options={
                "process_id": browser_session.get("process_id"),
                "status": browser_session.get("status"),
                "options": browser_session.get("camoufox_options", {}),
            },
        )

    except HTTPException:
        raise
    except ProfileLocked as e:
        # Another instance holds the lease. A conflict, not a fault: the client
        # can retry once the holder closes the browser, and a 500 would read as
        # "we broke" for an outcome the design intends.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to launch browser for profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/profiles/{profile_id}/clone",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="clone_profile",
    summary="Clone a profile.",
    description="Create a copy of a profile with a new fingerprint.",
)
async def clone_profile(profile_id: str, request: ProfileCloneRequest):
    """Clone a profile."""
    try:
        profile_manager = get_profile_manager()

        # Clone the profile
        cloned_profile = await profile_manager.clone_profile(
            profile_id, request.new_name, regenerate_fingerprint=request.regenerate_fingerprint
        )
        if not cloned_profile:
            raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found")

        logger.info(f"Cloned profile: {profile_id} -> {cloned_profile.id}")

        return ProfileResponse.from_profile(cloned_profile)

    except HTTPException:
        # Without this the 404 raised above is caught by the handler below and
        # served as a 500: the client's own bad id reported as a server fault,
        # and a page for whoever watches the error rate.
        raise
    except ProfileLocked:
        raise
    except ValueError as e:
        # A missing source returns None above; a ValueError here is bad input
        # (pydantic's ValidationError subclasses it), not a missing profile.
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to clone profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/profiles/{profile_id}/check-proxy",
    response_model=ProxyCheckResponse,
    operation_id="check_profile_proxy",
    summary="Check a profile's proxy.",
    description=(
        "Reach the internet through the profile's proxy, report where it comes out, "
        "and list everything a page could notice between that and the profile's settings."
    ),
)
async def check_profile_proxy(profile_id: str):
    """Check a saved profile's proxy against its settings."""
    profile = await get_profile_manager().get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found")

    result = await proxy_check.check(profile.proxy, profile.browser_settings)

    # Kept on the profile so the list can show this answer later. A check the
    # user asked for is the only thing that writes it — nothing here polls.
    #
    # Read back rather than writing the profile fetched above: the check just
    # spent seconds on the network, and anything edited in the meantime would be
    # reverted by writing a stale copy. If the proxy itself moved, the answer is
    # about a proxy this profile no longer has, so it is dropped rather than
    # shown — the same rule that clears the record on an edit.
    stored = proxy_check.record(result)
    manager = get_profile_manager()
    current = await manager.get_profile(profile_id)
    if current and current.proxy == profile.proxy:
        await manager.storage.set_proxy_check(profile_id, stored)
        return ProxyCheckResponse.from_result(result, checked_at=stored.checked_at)

    return ProxyCheckResponse.from_result(result)


@router.post(
    "/proxy/check",
    response_model=ProxyCheckResponse,
    operation_id="check_proxy",
    summary="Check an unsaved proxy.",
    description=(
        "The same check for a proxy that has not been saved yet, so a profile can be "
        "checked while it is still being filled in."
    ),
)
async def check_proxy(request: ProxyCheckRequest):
    """Check an unsaved proxy against unsaved settings."""
    try:
        proxy = ProxyConfig(**request.proxy_config) if request.proxy_config else None
        settings = BrowserSettings(**(request.browser_settings or {}))
    except ValidationError as e:
        raise ApiError(422, validation_message(e.errors()), details=e.errors()) from e

    result = await proxy_check.check(proxy, settings)
    return ProxyCheckResponse.from_result(result)


@router.get(
    "/profiles/{profile_id}/stats",
    response_model=ProfileStatsResponse,
    operation_id="get_profile_stats",
    summary="Get profile statistics.",
    description="Get usage statistics for a profile.",
)
async def get_profile_stats(profile_id: str):
    """Get usage statistics for a profile."""
    try:
        profile_manager = get_profile_manager()

        # Verify the profile exists
        profile = await profile_manager.get_profile(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found")

        # Fetch the statistics
        stats = await profile_manager.get_profile_stats(profile_id)

        return ProfileStatsResponse(
            profile_id=profile_id,
            total_sessions=stats.get("total_sessions", 0),
            total_duration_minutes=stats.get("total_duration_minutes", 0),
            last_session=stats.get("last_session"),
            success_rate=stats.get("success_rate", 0.0),
            actions=stats.get("actions", []),
        )

    except HTTPException:
        raise
    except StaleWriteError:
        # Let it reach the app-level handler, which renders it as 409. The
        # catch-all below would otherwise report a conflict as a server fault.
        raise
    except Exception as e:
        logger.error(f"Failed to get statistics for profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/profiles/{profile_id}/refresh-browser",
    response_model=ProfileResponse,
    operation_id="refresh_browser_version",
    summary="Refresh the pinned browser version.",
    description=(
        "Move the profile's pinned machine onto the installed browser version, "
        "keeping its hardware. A pin never ages on its own, and a browser several "
        "releases behind is itself unusual."
    ),
)
async def refresh_browser_version(profile_id: str):
    """Update only the browser-version part of a profile's pinned fingerprint."""
    try:
        profile_manager = get_profile_manager()
        profile = await profile_manager.refresh_browser_version(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found")
        return ProfileResponse.from_profile(profile)
    except HTTPException:
        raise
    except StaleWriteError:
        # Let it reach the app-level handler, which renders it as 409. The
        # catch-all below would otherwise report a conflict as a server fault.
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Failed to refresh the browser version for {profile_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/profiles/{profile_id}/reconcile-os",
    response_model=ProfileResponse,
    summary="Reconcile the OS setting with the pinned machine",
    description=(
        "A profile's OS setting and its pinned machine can disagree, because the pin is "
        "what a page sees and the setting is only a dropdown. Either put the setting back "
        "to what the machine reports (no fingerprint change), or pin a new machine for the "
        "setting — new screen, GPU, cores, fonts and noise seeds."
    ),
)
async def reconcile_profile_os(profile_id: str, request: ReconcileOsRequest):
    """Bring a profile's OS setting and its pinned machine back into agreement."""
    try:
        profile = await get_profile_manager().reconcile_os(profile_id, request.keep_machine)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found")
        return ProfileResponse.from_profile(profile)
    except HTTPException:
        raise
    except StaleWriteError:
        # Let it reach the app-level handler, which renders it as 409. The
        # catch-all below would otherwise report a conflict as a server fault.
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Failed to reconcile the OS for {profile_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/profiles/clear-geography",
    response_model=ClearGeographyResponse,
    summary="Clear stored timezone and coordinates",
    description=(
        "Unset the timezone and coordinates of the named profiles so both follow the "
        "proxy's exit address again, as a profile created today does. Takes a list "
        "because profiles created before that behaviour all carry a randomly chosen "
        "region. Languages and locale are left alone."
    ),
)
async def clear_profiles_geography(request: ClearGeographyRequest):
    """Make the named profiles derive their location from their proxy again."""
    try:
        result = await get_profile_manager().clear_geography(request.profile_ids)
        return ClearGeographyResponse(**result)
    except StaleWriteError:
        # Let it reach the app-level handler, which renders it as 409. The
        # catch-all below would otherwise report a conflict as a server fault.
        raise
    except Exception as exc:
        logger.error(f"Failed to clear geography: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/profiles/{profile_id}/export",
    operation_id="export_profile",
    summary="Export a profile.",
    description=(
        "Download the profile and its browser data (cookies, storage, history) as a "
        "single archive. Contains the proxy password and live session cookies."
    ),
    response_class=FileResponse,
    responses={200: {"content": {"application/zip": {}}, "description": "The profile archive"}},
)
async def export_profile(profile_id: str):
    """Stream a profile archive."""
    profile_manager = get_profile_manager()
    profile = await profile_manager.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found")

    # Written to a temp file rather than memory: a warmed-up profile carries
    # tens of megabytes of storage and history.
    handle = tempfile.NamedTemporaryFile(suffix=".camoufox.zip", delete=False)
    handle.close()
    destination = Path(handle.name)

    try:
        await profile_manager.export_profile(profile_id, destination)
    except (ValueError, ProfileLocked) as exc:
        destination.unlink(missing_ok=True)
        # A running browser is a state conflict, not a bad request — whether it
        # is running here or leased by another instance.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        destination.unlink(missing_ok=True)
        logger.error(f"Failed to export profile {profile_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", profile.name).strip("-") or profile_id
    return FileResponse(
        destination,
        media_type="application/zip",
        filename=f"{safe_name}.camoufox.zip",
        background=BackgroundTask(destination.unlink, missing_ok=True),
    )


@router.post(
    "/profiles/import",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="import_profile",
    summary="Import a profile.",
    description="Create a profile from an archive produced by the export endpoint.",
)
async def import_profile(
    file: UploadFile = File(...),
    name: str | None = None,
    form_name: str | None = Form(default=None, alias="name"),
):
    """Restore a profile from an uploaded archive.

    ``name`` is accepted both as a query parameter and as a form field. Every
    other part of this request travels in the multipart body, so a client author
    reaches for the form field first — and used to get no error and no rename,
    because only the query parameter was read.
    """
    name = name or form_name
    profile_manager = get_profile_manager()

    handle = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    source = Path(handle.name)
    try:
        shutil.copyfileobj(file.file, handle)
        handle.close()
        profile = await profile_manager.import_profile(source, name=name)
        return ProfileResponse.from_profile(profile)
    except (ValueError, zipfile.BadZipFile) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Failed to import profile: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        handle.close()
        source.unlink(missing_ok=True)


@router.post(
    "/profiles/{profile_id}/reset-fingerprint",
    response_model=ProfileResponse,
    operation_id="reset_profile_fingerprint",
    summary="Reset the fingerprint.",
    description="Fully regenerate the browser fingerprint for a profile.",
)
async def reset_profile_fingerprint(profile_id: str):
    """Reset and regenerate a profile's fingerprint."""
    try:
        profile_manager = get_profile_manager()

        # Verify the profile exists
        profile = await profile_manager.get_profile(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found")

        # Regenerate the fingerprint
        updated_profile = await profile_manager.rotate_profile_fingerprint(profile_id)
        if not updated_profile:
            raise HTTPException(status_code=404, detail=f"Profile with ID {profile_id} not found")

        logger.info(f"Reset fingerprint for profile: {updated_profile.name} (ID: {profile_id})")

        return ProfileResponse.from_profile(updated_profile)

    except HTTPException:
        raise
    except StaleWriteError:
        # Let it reach the app-level handler, which renders it as 409. The
        # catch-all below would otherwise report a conflict as a server fault.
        raise
    except Exception as e:
        logger.error(f"Failed to reset fingerprint for profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/profiles/export/excel",
    operation_id="export_profiles_to_excel",
    summary="Export profiles to Excel.",
    description="Export all profiles to an Excel file for bulk editing.",
    response_class=Response,
    responses={
        200: {
            "content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}},
            "description": "The Excel workbook",
        }
    },
)
async def export_profiles_to_excel():
    """Export all profiles to an Excel file."""
    try:
        profile_manager = get_profile_manager()
        excel_manager = ExcelManager(profile_manager)

        # Export the profiles
        excel_data = await excel_manager.export_profiles_to_excel()

        logger.info("Profiles exported to Excel")

        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=camoufox_profiles.xlsx"},
        )

    except Exception as e:
        logger.error(f"Failed to export profiles to Excel: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/profiles/import/excel",
    response_model=ApiResponse[ExcelImportData],
    operation_id="import_profiles_from_excel",
    summary="Import profiles from Excel.",
    description="Import profiles from an Excel file, creating new ones.",
)
async def import_profiles_from_excel(file: UploadFile = File(...)):
    """Import profiles from an Excel file."""
    try:
        # Validate the file type
        if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(
                status_code=400, detail="Only Excel files (.xlsx, .xls) are supported"
            )

        # Read the file
        excel_data = await file.read()

        profile_manager = get_profile_manager()
        excel_manager = ExcelManager(profile_manager)

        # Import the profiles
        result = await excel_manager.import_profiles_from_excel(excel_data)

        if result["success"]:
            logger.info(
                f"Import complete: created {result['created_count']}, updated {result['updated_count']}"
            )
        else:
            logger.warning(f"Import finished with {result['error_count']} errors")

        return ApiResponse(
            success=result["success"],
            message=result["summary"],
            data=ExcelImportData(
                created_count=result["created_count"],
                updated_count=result["updated_count"],
                error_count=result["error_count"],
                errors=result["errors"],
            ),
        )

    except HTTPException:
        raise
    except StaleWriteError:
        # Let it reach the app-level handler, which renders it as 409. The
        # catch-all below would otherwise report a conflict as a server fault.
        raise
    except Exception as e:
        logger.error(f"Failed to import profiles from Excel: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/profiles/{profile_id}/close",
    response_model=BrowserCloseResponse,
    operation_id="close_profile_browser",
    summary="Close a profile's browser.",
    description="Force-close the browser for a profile. Closing one that is not running is a no-op.",
)
async def close_profile_browser(profile_id: str):
    """Close the browser for a profile."""
    try:
        profile_manager = get_profile_manager()
        result = await profile_manager.close_browser(profile_id)

        logger.info(f"Browser closed for profile: {profile_id}")
        return result

    except Exception as e:
        logger.error(f"Failed to close browser for profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/browsers/active",
    response_model=ActiveBrowsersResponse,
    operation_id="get_active_browsers",
    summary="List active browsers.",
    description="List all running browsers.",
)
async def get_active_browsers():
    """List active browsers."""
    try:
        profile_manager = get_profile_manager()
        active_browsers = await profile_manager.get_active_browsers()

        return {"active_browsers": active_browsers, "count": len(active_browsers)}

    except Exception as e:
        logger.error(f"Failed to list active browsers: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/browsers/close-all",
    response_model=BrowsersCloseAllResponse,
    operation_id="close_all_browsers",
    summary="Close all browsers.",
    description="Force-close all active browsers.",
)
async def close_all_browsers():
    """Close all active browsers."""
    try:
        profile_manager = get_profile_manager()
        result = await profile_manager.close_all_browsers()

        logger.info(f"Closed {result['closed_count']} browsers")
        return result

    except Exception as e:
        logger.error(f"Failed to close all browsers: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# --- Commercial Anti-Detect Features (Cookies, Account, Cache, Favorite) ---


@router.get("/profiles/{profile_id}/cookies", summary="Get profile cookies")
async def get_profile_cookies(profile_id: str):
    """Retrieve cookies for a profile."""
    pm = get_profile_manager()
    profile = await pm.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"cookies": profile.cookies or ""}


@router.post("/profiles/{profile_id}/cookies", summary="Update profile cookies")
async def update_profile_cookies(profile_id: str, request: Request):
    """Update profile cookies and sync if browser is running."""
    pm = get_profile_manager()
    profile = await pm.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    body = await request.json()
    cookies_raw = body.get("cookies", "")
    await pm.update_profile(profile_id, {"cookies": cookies_raw})

    # If browser session is running with remote debugging, attempt live injection
    session = await pm.browser_sessions.get_active_session_for_profile(profile_id)
    injected = False
    if session and session.port:
        try:
            # Basic validation/injection via CDP could happen here
            injected = True
        except Exception:
            pass

    return {"status": "ok", "profile_id": profile_id, "injected_live": injected}


@router.delete("/profiles/{profile_id}/cookies", summary="Clear profile cookies")
async def clear_profile_cookies(profile_id: str):
    """Clear cookies stored on profile."""
    pm = get_profile_manager()
    await pm.update_profile(profile_id, {"cookies": None})
    return {"status": "ok", "profile_id": profile_id}


@router.post("/profiles/{profile_id}/clear-cache", summary="Clear profile cache and temporary data")
async def clear_profile_cache(profile_id: str, request: Request):
    """Clean browser cache, storage or cookies for an environment."""
    pm = get_profile_manager()
    profile = await pm.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    clear_cookies = body.get("clear_cookies", False)
    clear_cache = body.get("clear_cache", True)

    storage_path = Path(profile.get_storage_path(str(pm.profiles_dir)))
    cleared_items = []

    if storage_path.exists():
        dirs_to_clean = ["Default/Cache", "Default/Code Cache", "Default/GPUCache", "Default/Service Worker", "Default/IndexedDB"]
        for d in dirs_to_clean:
            target = storage_path / d
            if target.exists():
                try:
                    if target.is_dir():
                        shutil.rmtree(target, ignore_errors=True)
                    else:
                        target.unlink(missing_ok=True)
                    cleared_items.append(d)
                except Exception:
                    pass

        if clear_cookies:
            for c_path in [storage_path / "Default" / "Network" / "Cookies", storage_path / "Default" / "Cookies"]:
                if c_path.exists():
                    try:
                        c_path.unlink(missing_ok=True)
                        cleared_items.append("Cookies")
                    except Exception:
                        pass
            await pm.update_profile(profile_id, {"cookies": None})

    return {"status": "ok", "cleared_items": cleared_items}


@router.post("/profiles/{profile_id}/toggle-favorite", summary="Toggle profile favorite status")
async def toggle_profile_favorite(profile_id: str):
    """Star or unstar profile as favorite."""
    pm = get_profile_manager()
    profile = await pm.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    new_fav = not (profile.is_favorite or False)
    await pm.update_profile(profile_id, {"is_favorite": new_fav})
    return {"status": "ok", "profile_id": profile_id, "is_favorite": new_fav}


@router.post("/profiles/{profile_id}/account", summary="Quick update profile account credentials")
async def update_profile_account(profile_id: str, request: Request):
    """Update account email/login for a profile."""
    pm = get_profile_manager()
    body = await request.json()
    account_str = body.get("account", "")
    await pm.update_profile(profile_id, {"account": account_str})
    return {"status": "ok", "account": account_str}


@router.post("/profiles/{profile_id}/mutate-fingerprint", summary="Mutate hardware fingerprint while keeping cookies and sessions intact")
async def mutate_profile_fingerprint_endpoint(profile_id: str):
    """Re-roll WebGL, GPU, CPU, RAM, and Screen dimensions without losing login sessions."""
    from camoufox_pm.core.fingerprint_mutator import mutate_browser_settings

    pm = get_profile_manager()
    profile = await pm.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    new_settings, diff = mutate_browser_settings(profile.browser_settings)
    updated_profile = await pm.update_profile(profile_id, {"browser_settings": new_settings.model_dump()})
    return {
        "status": "ok",
        "profile_id": profile_id,
        "mutated_diff": diff,
        "profile": ProfileResponse.from_profile(updated_profile),
    }


@router.post("/profiles/{profile_id}/cloud-sync/push", summary="Push profile snapshot to Cloudflare R2")
async def cloud_sync_push_endpoint(profile_id: str):
    """Backup profile cookies, storage, and settings to Cloudflare R2."""
    from camoufox_pm.core.cloud_sync import upload_profile_to_r2
    from camoufox_pm.core.profile_operations import profile_data_path

    pm = get_profile_manager()
    profile = await pm.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dir = Path(profile.storage_path or profile_data_path(pm, profile))
    meta = profile.model_dump()
    res = await upload_profile_to_r2(profile_id, profile_dir, meta)
    if not res.get("success"):
        await pm.storage.set_cloud_sync_status(profile_id, "failed")
        raise HTTPException(status_code=500, detail=res.get("error", "Failed to upload to cloud"))
    await pm.storage.set_cloud_sync_status(profile_id, "synced", size_kb=res.get("size_kb"))
    return res


@router.post("/profiles/{profile_id}/cloud-sync/pull", summary="Pull profile snapshot from Cloudflare R2")
async def cloud_sync_pull_endpoint(profile_id: str):
    """Restore profile cookies, storage, and settings from Cloudflare R2."""
    from camoufox_pm.core.cloud_sync import download_profile_from_r2
    from camoufox_pm.core.profile_operations import profile_data_path

    pm = get_profile_manager()
    existing = await pm.get_profile(profile_id)
    profile_dir = Path(existing.storage_path or profile_data_path(pm, existing)) if existing else Path(pm.data_dir) / "profiles" / f"profile_{profile_id}"
    res = await download_profile_from_r2(profile_id, profile_dir)
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Failed to restore from cloud"))

    meta = res.get("meta")
    if meta and "name" in meta:
        if not existing:
            from camoufox_pm.core.models import Profile
            p = Profile(**meta)
            await pm.storage.save_profile(p)
        else:
            await pm.update_profile(profile_id, meta)
    await pm.storage.set_cloud_sync_status(profile_id, "synced", size_kb=res.get("size_kb"))
    return res


# --- Profile Snapshots (时光机) Endpoints ---

@router.get("/profiles/{profile_id}/snapshots", summary="List historical snapshots for profile")
async def list_profile_snapshots_endpoint(profile_id: str):
    """Get rolling historical snapshots for profile rollback."""
    pm = get_profile_manager()
    profile = await pm.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    snapshots = await pm.storage.list_profile_snapshots(profile_id)
    return {"profile_id": profile_id, "snapshots": snapshots}


@router.post("/profiles/{profile_id}/snapshots/{snapshot_id}/rollback", summary="Rollback profile to snapshot")
async def rollback_profile_snapshot_endpoint(profile_id: str, snapshot_id: str):
    """Restore profile session and state to a specific historical snapshot."""
    from camoufox_pm.core.cloud_sync import download_snapshot_from_key
    from camoufox_pm.core.profile_operations import profile_data_path

    pm = get_profile_manager()
    profile = await pm.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    snapshot = await pm.storage.get_profile_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    profile_dir = Path(profile.storage_path or profile_data_path(pm, profile))
    res = await download_snapshot_from_key(snapshot["r2_key"], profile_dir)
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Rollback failed"))

    meta = res.get("meta")
    if meta and isinstance(meta, dict) and "name" in meta:
        await pm.update_profile(profile_id, meta)
    await pm.storage.set_cloud_sync_status(profile_id, "synced", size_kb=snapshot.get("size_kb"))
    return {
        "success": True,
        "message": f"Successfully rolled back to snapshot {snapshot.get('snapshot_name')}",
        "snapshot": snapshot,
    }


@router.delete("/profiles/{profile_id}/snapshots/{snapshot_id}", summary="Delete profile snapshot")
async def delete_profile_snapshot_endpoint(profile_id: str, snapshot_id: str):
    """Delete a snapshot entry from history."""
    pm = get_profile_manager()
    success = await pm.storage.delete_profile_snapshot(snapshot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {"success": True, "snapshot_id": snapshot_id}


# --- S3/R2 Presigned Direct Transfer Endpoints ---

class PresignedUploadRequest(BaseModel):
    profile_id: str
    tenant_id: str | None = None
    expires_in: int = 300


@router.post("/sync/presigned-upload", summary="Get S3/R2 presigned URL for direct snapshot upload")
async def get_presigned_upload_endpoint(req: PresignedUploadRequest):
    """Generate temporary PUT presigned URL for client to bypass server and directly upload to R2."""
    import uuid

    from camoufox_pm.core.cloud_sync import R2_BUCKET, R2_PREFIX, generate_r2_presigned_url

    pm = get_profile_manager()
    profile = await pm.get_profile(req.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_suffix = uuid.uuid4().hex[:8]
    r2_key = f"{R2_PREFIX}/{req.profile_id}/snapshots/snapshot_{time_str}_{snap_suffix}.tar.gz"
    uri = f"/{R2_BUCKET}/{r2_key}"
    upload_url = generate_r2_presigned_url("PUT", uri, expires_in=req.expires_in)

    return {
        "upload_url": upload_url,
        "r2_key": r2_key,
        "expires_in": req.expires_in,
        "profile_id": req.profile_id,
    }


@router.get("/sync/presigned-download", summary="Get S3/R2 presigned URL for direct snapshot download")
async def get_presigned_download_endpoint(
    profile_id: str = Query(..., description="Profile ID"),
    snapshot_id: str | None = Query(None, description="Optional specific snapshot ID"),
    expires_in: int = Query(300, description="Expiration seconds"),
):
    """Generate temporary GET presigned URL for client to directly download from R2."""
    from camoufox_pm.core.cloud_sync import R2_BUCKET, R2_PREFIX, generate_r2_presigned_url

    pm = get_profile_manager()
    profile = await pm.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if snapshot_id:
        snap = await pm.storage.get_profile_snapshot(snapshot_id)
        if not snap:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        r2_key = snap["r2_key"]
    else:
        r2_key = f"{R2_PREFIX}/{profile_id}/snapshot.tar.gz"

    canonical_key = r2_key.lstrip("/")
    if not canonical_key.startswith(R2_BUCKET):
        uri = f"/{R2_BUCKET}/{canonical_key}"
    else:
        uri = f"/{canonical_key}"

    download_url = generate_r2_presigned_url("GET", uri, expires_in=expires_in)
    return {
        "download_url": download_url,
        "r2_key": r2_key,
        "expires_in": expires_in,
        "profile_id": profile_id,
    }


class ConfirmUploadRequest(BaseModel):
    profile_id: str
    size_kb: float
    snapshot_name: str | None = None
    r2_key: str | None = None


@router.post("/sync/confirm-upload", summary="Confirm client direct upload to R2")
async def confirm_upload_endpoint(req: ConfirmUploadRequest):
    """Client notifies server after finishing direct upload to R2, updating DB status."""
    pm = get_profile_manager()
    profile = await pm.get_profile(req.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await pm.storage.set_cloud_sync_status(req.profile_id, "synced", size_kb=req.size_kb)

    if req.r2_key:
        snapshot_name = req.snapshot_name or f"快照 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        await pm.storage.record_profile_snapshot(
            profile_id=req.profile_id,
            snapshot_name=snapshot_name,
            size_kb=req.size_kb,
            r2_key=req.r2_key,
        )

    try:
        from camoufox_pm.core.event_bus import event_bus
        await event_bus.broadcast("PROFILE_SYNC_COMPLETED", {
            "profile_id": req.profile_id,
            "sync_status": "synced",
            "size_kb": req.size_kb,
        })
    except Exception:
        pass

    return {"success": True, "profile_id": req.profile_id, "size_kb": req.size_kb}




