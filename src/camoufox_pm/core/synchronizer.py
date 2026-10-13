"""Window and Browser Action Synchronizer for Multi-Instance Orchestration.

Broadcasts commands (navigation, scrolling, humanized input, clicking, reload)
across running browser profiles using Chrome DevTools Protocol (CDP) and native window APIs.
"""

import asyncio
import json
import random
from typing import Any

import httpx
from loguru import logger


async def get_cdp_pages(cdp_port: int) -> list[dict[str, Any]]:
    """Retrieve active page targets from a Chromium CDP port."""
    url = f"http://127.0.0.1:{cdp_port}/json"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                targets = resp.json()
                # Filter for regular page targets
                return [t for t in targets if t.get("type") == "page"]
    except Exception as exc:
        logger.debug(f"Could not connect to CDP port {cdp_port}: {exc}")
    return []


async def send_cdp_command(ws_url: str, method: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Send a single CDP command over WebSocket and return response."""
    try:
        import websockets

        async with websockets.connect(ws_url, close_timeout=1.0) as ws:
            msg_id = random.randint(1000, 9999)
            payload = {"id": msg_id, "method": method, "params": params or {}}
            await ws.send(json.dumps(payload))
            raw_resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
            return json.loads(raw_resp)
    except Exception as exc:
        logger.debug(f"CDP WebSocket command {method} failed: {exc}")
        return None


async def broadcast_action(
    sessions: list[dict[str, Any]],
    action: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Broadcast an action across all specified active browser sessions."""
    results: list[dict[str, Any]] = []

    for s in sessions:
        pid = s.get("profile_id")
        cdp_port = s.get("cdp_port")
        if not cdp_port:
            results.append({"profile_id": pid, "status": "skipped", "reason": "no_cdp_port"})
            continue

        pages = await get_cdp_pages(cdp_port)
        if not pages:
            results.append({"profile_id": pid, "status": "no_pages_found"})
            continue

        primary_page = pages[0]
        ws_url = primary_page.get("webSocketDebuggerUrl")
        if not ws_url:
            results.append({"profile_id": pid, "status": "no_ws_url"})
            continue

        try:
            if action == "navigate":
                target_url = payload.get("url", "https://google.com")
                # Add human jitter delay
                await asyncio.sleep(random.uniform(0.02, 0.15))
                await send_cdp_command(ws_url, "Page.navigate", {"url": target_url})
                results.append({"profile_id": pid, "status": "navigated", "url": target_url})

            elif action == "reload":
                await send_cdp_command(ws_url, "Page.reload", {"ignoreCache": True})
                results.append({"profile_id": pid, "status": "reloaded"})

            elif action == "scroll":
                delta_y = int(payload.get("delta_y", 400))
                # Human jitter in scroll distance (±5%)
                jitter_y = delta_y + random.randint(-15, 15)
                expr = f"window.scrollBy({{ top: {jitter_y}, behavior: 'smooth' }});"
                await send_cdp_command(ws_url, "Runtime.evaluate", {"expression": expr})
                results.append({"profile_id": pid, "status": "scrolled", "delta_y": jitter_y})

            elif action == "input":
                text = str(payload.get("text", ""))
                selector = payload.get("selector")
                escaped_text = json.dumps(text)

                if selector:
                    expr = f"""
                    (function() {{
                        const el = document.querySelector({json.dumps(selector)}) || document.activeElement;
                        if (el) {{
                            el.focus();
                            el.value = {escaped_text};
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}
                        return false;
                    }})();
                    """
                else:
                    expr = f"""
                    (function() {{
                        const el = document.activeElement;
                        if (el && ('value' in el || el.isContentEditable)) {{
                            if ('value' in el) el.value = {escaped_text};
                            else el.innerText = {escaped_text};
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}
                        return false;
                    }})();
                    """
                # Slight random delay before typing to prevent exact simultaneous submission
                await asyncio.sleep(random.uniform(0.05, 0.25))
                await send_cdp_command(ws_url, "Runtime.evaluate", {"expression": expr})
                results.append({"profile_id": pid, "status": "input_sent"})

            elif action == "click":
                selector = payload.get("selector")
                if selector:
                    # 1. Query target element bounding rectangle
                    measure_expr = f"""
                    (function() {{
                        const el = document.querySelector({json.dumps(selector)});
                        if (!el) return null;
                        el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        const r = el.getBoundingClientRect();
                        return {{ x: r.left, y: r.top, width: r.width, height: r.height }};
                    }})();
                    """
                    rect_resp = await send_cdp_command(ws_url, "Runtime.evaluate", {
                        "expression": measure_expr,
                        "returnByValue": True,
                    })

                    rect = None
                    if rect_resp and "result" in rect_resp and "value" in rect_resp["result"]:
                        rect = rect_resp["result"]["value"]

                    if rect and rect.get("width", 0) > 0 and rect.get("height", 0) > 0:
                        # Randomize target coordinate within the button (30% to 70% bounds)
                        target_x = round(rect["x"] + rect["width"] * random.uniform(0.35, 0.65), 1)
                        target_y = round(rect["y"] + rect["height"] * random.uniform(0.35, 0.65), 1)

                        # Generate realistic starting point
                        start_x = max(10, min(1200, target_x + random.uniform(-220, 220)))
                        start_y = max(10, min(800, target_y + random.uniform(100, 260)))

                        # Cubic Bézier control points with randomized deviation and tremor
                        p1_x = start_x + (target_x - start_x) * 0.3 + random.uniform(-40, 40)
                        p1_y = start_y + (target_y - start_y) * 0.1 + random.uniform(-30, 30)
                        p2_x = start_x + (target_x - start_x) * 0.7 + random.uniform(-30, 30)
                        p2_y = start_y + (target_y - start_y) * 0.9 + random.uniform(-20, 20)

                        steps = random.randint(12, 18)
                        for i in range(1, steps + 1):
                            t = i / steps
                            # Cubic Bezier formula
                            bx = ((1 - t) ** 3 * start_x
                                  + 3 * (1 - t) ** 2 * t * p1_x
                                  + 3 * (1 - t) * t ** 2 * p2_x
                                  + t ** 3 * target_x)
                            by = ((1 - t) ** 3 * start_y
                                  + 3 * (1 - t) ** 2 * t * p1_y
                                  + 3 * (1 - t) * t ** 2 * p2_y
                                  + t ** 3 * target_y)
                            # Micro tremor
                            bx += random.uniform(-0.5, 0.5)
                            by += random.uniform(-0.5, 0.5)

                            await send_cdp_command(ws_url, "Input.dispatchMouseEvent", {
                                "type": "mouseMoved",
                                "x": round(bx, 1),
                                "y": round(by, 1),
                            })
                            await asyncio.sleep(random.uniform(0.006, 0.016))

                        # Dwell on target before clicking
                        await asyncio.sleep(random.uniform(0.04, 0.09))

                        # Mouse down
                        await send_cdp_command(ws_url, "Input.dispatchMouseEvent", {
                            "type": "mousePressed",
                            "button": "left",
                            "clickCount": 1,
                            "x": target_x,
                            "y": target_y,
                        })
                        # Natural human press duration (50ms - 110ms)
                        await asyncio.sleep(random.uniform(0.05, 0.11))

                        # Mouse up
                        await send_cdp_command(ws_url, "Input.dispatchMouseEvent", {
                            "type": "mouseReleased",
                            "button": "left",
                            "clickCount": 1,
                            "x": target_x,
                            "y": target_y,
                        })

                        # Fallback click to ensure event propagation
                        fallback_expr = f"""
                        (function() {{
                            const el = document.querySelector({json.dumps(selector)});
                            if (el) el.click();
                        }})();
                        """
                        await send_cdp_command(ws_url, "Runtime.evaluate", {"expression": fallback_expr})
                        results.append({"profile_id": pid, "status": "clicked_bezier", "selector": selector, "coords": [target_x, target_y]})
                    else:
                        # Fallback direct click if rect wasn't measurable
                        expr = f"""
                        (function() {{
                            const el = document.querySelector({json.dumps(selector)});
                            if (el) {{
                                el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                                el.click();
                                return true;
                            }}
                            return false;
                        }})();
                        """
                        await send_cdp_command(ws_url, "Runtime.evaluate", {"expression": expr})
                        results.append({"profile_id": pid, "status": "clicked", "selector": selector})
                else:
                    results.append({"profile_id": pid, "status": "error", "message": "selector required for click"})

            else:
                results.append({"profile_id": pid, "status": "unknown_action", "action": action})

        except Exception as exc:
            logger.error(f"Error broadcasting {action} to profile {pid}: {exc}")
            results.append({"profile_id": pid, "status": "error", "message": str(exc)})

    return {
        "success": True,
        "action": action,
        "total_targets": len(sessions),
        "results": results,
    }
