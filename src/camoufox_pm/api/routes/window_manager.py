"""Window manager API for tiling and arranging browser instances."""

import math
import subprocess
import sys
from typing import Any

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel

router = APIRouter()


class WindowTileRequest(BaseModel):
    cols: int | None = None
    rows: int | None = None
    padding: int = 8
    top_offset: int = 50  # leave room for menu bar / dock


@router.post("/windows/tile")
async def tile_windows(request: WindowTileRequest = WindowTileRequest()):
    """Tile all open browser windows (Chromium / Camoufox) across the screen."""
    if sys.platform != "darwin":
        return {
            "success": True,
            "message": "Window tiling is currently optimized for macOS desktop",
            "windows_count": 0,
        }

    # AppleScript to find screen dimensions and tile windows
    padding = request.padding
    top_offset = request.top_offset
    custom_cols = request.cols or 0
    custom_rows = request.rows or 0

    applescript = f"""
    tell application "Finder"
        set screenBounds to bounds of window of desktop
        set screenWidth to item 3 of screenBounds
        set screenHeight to item 4 of screenBounds
    end tell

    set targetProcessNames to {{"Chromium", "Google Chrome", "Camoufox", "Firefox"}}
    set openWindows to {{}}

    tell application "System Events"
        repeat with procName in targetProcessNames
            if exists (process procName) then
                tell process procName
                    repeat with w in windows
                        set end of openWindows to w
                    end repeat
                end tell
            end if
        end repeat

        set winCount to count of openWindows
        if winCount = 0 then
            return "0:No browser windows open"
        end if

        set reqCols to {custom_cols}
        set reqRows to {custom_rows}

        if reqCols > 0 then
            set numCols to reqCols
        else
            if winCount = 1 then
                set numCols to 1
            else if winCount <= 4 then
                set numCols to 2
            else if winCount <= 9 then
                set numCols to 3
            else
                set numCols to 4
            end if
        end if

        set numRows to round (winCount / numCols) rounding up
        if reqRows > 0 then
            set numRows to reqRows
        end if

        set availW to screenWidth - ({padding} * (numCols + 1))
        set availH to screenHeight - {top_offset} - ({padding} * (numRows + 1))

        set cellW to round (availW / numCols)
        set cellH to round (availH / numRows)

        set idx to 0
        repeat with w in openWindows
            set r to idx div numCols
            set c to idx mod numCols
            set posX to {padding} + c * (cellW + {padding})
            set posY to {top_offset} + r * (cellH + {padding})
            try
                set position of w to {{posX, posY}}
                set size of w to {{cellW, cellH}}
            end try
            set idx to idx + 1
        end repeat

        return (winCount as string) & ":Windows tiled successfully"
    end tell
    """

    try:
        proc = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = proc.stdout.strip()
        count = 0
        msg = output
        if ":" in output:
            parts = output.split(":", 1)
            try:
                count = int(parts[0])
            except ValueError:
                pass
            msg = parts[1]

        return {
            "success": proc.returncode == 0,
            "windows_count": count,
            "message": msg,
        }
    except Exception as exc:
        logger.error(f"Failed to tile windows: {exc}")
        return {"success": False, "error": str(exc), "windows_count": 0}


class SynchronizerBroadcastRequest(BaseModel):
    action: str  # navigate, scroll, input, click, reload
    target_profile_ids: list[str] | None = None
    payload: dict[str, Any] = {}


@router.get("/windows/active")
async def list_active_windows():
    """List all currently active browser windows for the synchronizer panel."""
    from camoufox_pm.api.dependencies import get_profile_manager

    pm = get_profile_manager()
    raw_sessions = pm.browser_sessions.list_active()
    enriched = []
    for s in raw_sessions:
        p = await pm.get_profile(s["profile_id"])
        enriched.append({
            **s,
            "profile_name": p.name if p else s["profile_id"],
        })
    return {"sessions": enriched, "total": len(enriched)}


@router.post("/windows/synchronizer/broadcast")
async def broadcast_synchronizer(request: SynchronizerBroadcastRequest):
    """Broadcast an action (navigation, human typing, scroll, click) across browser instances."""
    from camoufox_pm.api.dependencies import get_profile_manager
    from camoufox_pm.core.synchronizer import broadcast_action

    pm = get_profile_manager()
    active_sessions = pm.browser_sessions.list_active()
    if request.target_profile_ids:
        target_set = set(request.target_profile_ids)
        active_sessions = [s for s in active_sessions if s["profile_id"] in target_set]

    res = await broadcast_action(active_sessions, request.action, request.payload)
    return res

