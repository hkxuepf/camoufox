"""Browser session lifecycle: launch, monitor, and close Camoufox instances.

Extracted from ``profile_manager`` so profile CRUD and browser control have
clear, independently testable responsibilities.

Cleanup is driven primarily by Playwright's ``close``/``disconnected`` events, so
a user closing the browser window is detected and the session is torn down. OS
process polling is only a best-effort fallback: with a persistent context the
resolvable pid is Playwright's driver process, not Firefox, so it is not a
reliable window-close signal on its own.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psutil
from loguru import logger

from ..config import get_settings

if TYPE_CHECKING:
    # Type-only: importing StorageManager at runtime would be a cycle, since
    # database.py has no need of this module at all.
    from .database import StorageManager

try:
    from camoufox.async_api import AsyncCamoufox

    CAMOUFOX_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without camoufox installed
    AsyncCamoufox = None  # type: ignore[assignment, misc]
    CAMOUFOX_AVAILABLE = False

ExitHandler = Callable[[str], Awaitable[None]]


class BrowserLaunchError(RuntimeError):
    """Raised when a Camoufox browser fails to launch."""


def _resolve_process_id(obj: Any) -> int | None:
    """Best-effort resolution of a driver/browser OS process id.

    Playwright does not expose this publicly, so this walks known internal
    attributes and returns ``None`` if none are available. It never fabricates a
    placeholder pid. Note: for a persistent context this is the Playwright driver
    process, used only as a forceful-kill fallback.
    """
    candidates = (
        lambda b: b._browser_process.pid,  # noqa: SLF001
        lambda b: b.browser._impl._connection._transport._proc.pid,  # noqa: SLF001
        lambda b: b._impl._connection._transport._proc.pid,  # noqa: SLF001
    )
    for getter in candidates:
        try:
            pid = getter(obj)
            if pid:
                return int(pid)
        except Exception:  # noqa: BLE001 - private attributes vary across versions
            continue
    return None


class BrowserSession:
    """A single running Camoufox or Chromium browser tied to a profile."""

    def __init__(
        self,
        profile_id: str,
        camoufox: Any = None,
        process_id: int | None = None,
        process: Any = None,
        engine: str = "camoufox",
        cdp_port: int | None = None,
        profile_path: str | None = None,
        proxy_forwarder: Any = None,
    ):
        self.profile_id = profile_id
        self.camoufox = camoufox  # AsyncCamoufox context manager instance
        self.process = process  # asyncio.subprocess.Process for Chromium
        self.process_id = process_id
        self.profile_path = profile_path
        self.engine = engine
        self.cdp_port = cdp_port
        self.proxy_forwarder = proxy_forwarder
        self.started_at = datetime.now()
        self.monitor_task: asyncio.Task | None = None
        self.on_exit: ExitHandler | None = None
        self._terminated = False

    def is_alive(self) -> bool:
        """Return True if session is currently alive and running."""
        if self._terminated:
            return False
        if self.process is not None:
            return self.process.returncode is None
        return True

    async def terminate(self) -> None:
        """Close the browser and stop its monitor task. Safe to call twice."""
        if self._terminated:
            return
        self._terminated = True
        logger.info(f"Terminating {self.engine} browser session for profile {self.profile_id}")

        # The monitor can be the caller here (_monitor -> _handle_exit -> terminate),
        # and a task cannot await itself; cancelling is enough in that case.
        monitor = self.monitor_task
        if monitor and not monitor.done():
            monitor.cancel()
            if asyncio.current_task() is not monitor:
                try:
                    await monitor
                except asyncio.CancelledError:
                    pass

        if self.camoufox is not None:
            try:
                await self.camoufox.__aexit__(None, None, None)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Error closing browser for {self.profile_id}: {exc}")

        if self.process is not None:
            try:
                # Terminate children of the Chromium process first
                if hasattr(self.process, "pid") and self.process.pid:
                    try:
                        p_obj = psutil.Process(self.process.pid)
                        for child in p_obj.children(recursive=True):
                            try:
                                child.kill()
                            except Exception:
                                pass
                    except Exception:
                        pass
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=1.5)
                except (asyncio.TimeoutError, TimeoutError):
                    self.process.kill()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Error terminating Chromium process for {self.profile_id}: {exc}")

        # Stop local proxy forwarder if running
        if self.proxy_forwarder is not None:
            try:
                await self.proxy_forwarder.stop()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Error stopping proxy forwarder for {self.profile_id}: {exc}")

        # Kill any OS processes tied to this profile (Camoufox main, GPU helper, Chrome helpers, etc.)
        if self.profile_path:
            p_str = str(self.profile_path)
            for p in psutil.process_iter(["pid", "cmdline"]):
                try:
                    if p.pid == psutil.Process().pid:
                        continue
                    cmdline = " ".join(p.info["cmdline"] or [])
                    if p_str in cmdline:
                        try:
                            for child in p.children(recursive=True):
                                try:
                                    child.kill()
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass
                            p.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except Exception:
                    pass

            # Clean stale .parentlock file if still left
            try:
                lock_file = Path(self.profile_path) / ".parentlock"
                if lock_file.exists():
                    lock_file.unlink(missing_ok=True)
            except Exception:
                pass

        # Best-effort: make sure the driver process and all its children are gone.
        if self.process_id:
            try:
                process = psutil.Process(self.process_id)
                for child in process.children(recursive=True):
                    try:
                        child.kill()
                    except Exception:
                        pass
                process.kill()
            except psutil.NoSuchProcess:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Error killing process {self.process_id}: {exc}")

    def info(self) -> dict[str, Any]:
        """Return a serializable summary of this session."""
        return {
            "profile_id": self.profile_id,
            "process_id": self.process_id,
            "engine": self.engine,
            "cdp_port": getattr(self, "cdp_port", None),
            "started_at": self.started_at.isoformat(),
        }


def _clean_stale_sessions(storage_dir: Path) -> None:
    """Remove stale session restore files and locks so the browser opens cleanly."""
    if not storage_dir.exists() or not storage_dir.is_dir():
        return
    for fname in ("sessionstore.jsonlz4", ".parentlock", "sessionCheckpoints.json"):
        target = storage_dir / fname
        if target.exists():
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
    backups = storage_dir / "sessionstore-backups"
    if backups.exists() and backups.is_dir():
        for child in backups.glob("*.jsonlz4"):
            try:
                child.unlink(missing_ok=True)
            except OSError:
                pass


class BrowserSessionManager:
    """Track and control the browsers currently running."""

    def __init__(self, storage: "StorageManager | None" = None, holder: str | None = None) -> None:
        self.active_sessions: dict[str, BrowserSession] = {}
        # Profile id -> how many launches are currently inside camoufox.start().
        # A count rather than a set, because two concurrent launches of one
        # profile both mark it and the first to leave would otherwise clear the
        # mark while the other is still starting.
        self._starting: dict[str, int] = {}
        # The event loop only holds weak references to tasks, so a teardown
        # suspended inside camoufox.__aexit__ could be garbage-collected and take
        # the primary cleanup path with it. Hold a strong reference until done.
        self._exit_tasks: set[asyncio.Task[None]] = set()
        # Lease bookkeeping. Without a storage and a holder id (unit tests, and
        # anything that only watches processes) every lease call below is a
        # no-op and this class behaves exactly as it did before leases existed.
        self._storage = storage
        self._holder = holder
        self._heartbeat_task: asyncio.Task[None] | None = None

    def start_heartbeat(self, interval: float = 30.0) -> None:
        """Begin renewing this process's leases in the background.

        The heartbeat is the difference between "this profile is running" and
        "this profile was running when someone last crashed": while it beats
        the lease stays alive, and when it stops — SIGKILL, a power cut — the
        lease outlives the browser by at most its TTL and then frees itself.
        """
        if self._storage is None or self._holder is None:
            return
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval))

    async def stop_heartbeat(self) -> None:
        """Stop the renewal loop, and wait for the beat in flight to finish."""
        if self._heartbeat_task is None:
            return
        self._heartbeat_task.cancel()
        try:
            await self._heartbeat_task
        except asyncio.CancelledError:
            pass
        self._heartbeat_task = None

    async def _heartbeat_loop(self, interval: float) -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                await self._renew_leases()
            except Exception as exc:  # noqa: BLE001 - one bad beat must not stop the loop
                logger.warning(f"Lease heartbeat failed: {exc}")

    async def _renew_leases(self) -> None:
        """Renew every lease we hold, and close any browser whose lease is gone."""
        if self._storage is None or self._holder is None or not self.active_sessions:
            return
        profile_ids = list(self.active_sessions)
        # The configured TTL, not a constant: a hardcoded value here would
        # shorten a deliberately long lease on every beat and let it expire
        # under a browser that is still running.
        ttl_seconds = get_settings().lease_ttl
        renewed = await self._storage.renew_lease(profile_ids, self._holder, ttl_seconds)
        if renewed == len(profile_ids):
            return
        # Something was taken from us. The bulk update already renewed whatever
        # survived; ask one at a time only to learn which ones those were.
        for profile_id in profile_ids:
            if await self._storage.renew_lease([profile_id], self._holder, ttl_seconds) > 0:
                continue
            logger.warning(
                f"Lost the lease on profile {profile_id} — another instance may be "
                "driving this identity; closing the browser."
            )
            # No attempt to take it back: whoever holds it now is already
            # running the profile, and racing them is the corruption itself.
            await self.close(profile_id)

    def is_running(self, profile_id: str) -> bool:
        """Return whether a browser is currently tracked for the profile."""
        return profile_id in self.active_sessions

    def is_live(self, profile_id: str) -> bool:
        """Whether a browser is running *or* still starting for the profile.

        ``is_running`` is false for the whole time ``camoufox.start()`` is
        being awaited, so a lease released on that answer can be taken away
        from a browser that is coming up. Lease decisions use this; the
        user-facing "is it open" answers stay on ``is_running``.
        """
        return profile_id in self.active_sessions or profile_id in self._starting

    def list_active(self) -> list[dict[str, Any]]:
        """Return summaries of the active sessions.

        A pure read: it used to drop sessions whose driver process had gone,
        which skipped ``terminate()`` and the exit handler and so leaked the
        Camoufox context. Teardown belongs to the close event and, failing that,
        to :meth:`_monitor`; both route through ``_handle_exit``.
        """
        return [session.info() for session in self.active_sessions.values()]

    async def launch(
        self,
        profile_id: str,
        launch_options: dict[str, Any],
        on_exit: ExitHandler | None = None,
        engine: str = "camoufox",
    ) -> BrowserSession:
        """Launch a Camoufox or Chromium browser and register a monitored session."""
        if profile_id in self.active_sessions:
            return self.active_sessions[profile_id]

        # Check and initialize local proxy forwarder bridge if needed
        raw_proxy = launch_options.get("raw_proxy")
        if not raw_proxy and "proxy" in launch_options and isinstance(launch_options["proxy"], dict):
            try:
                from .models import ProxyConfig
                raw_proxy = ProxyConfig(**launch_options["proxy"])
            except Exception:
                pass

        forwarder = None
        if raw_proxy and getattr(raw_proxy, "server", None):
            p_type = getattr(raw_proxy.type, "value", str(raw_proxy.type)).lower()
            needs_bridge = (
                "socks" in p_type
                or bool(raw_proxy.username)
                or bool(raw_proxy.password)
            )
            if needs_bridge:
                try:
                    from .proxy_forwarder import LocalProxyForwarder
                    forwarder = LocalProxyForwarder.from_proxy_config(raw_proxy)
                    local_url = await forwarder.start()
                    if engine == "chromium":
                        from .models import ProxyConfig, ProxyType
                        local_cfg = ProxyConfig(
                            type=ProxyType.HTTP,
                            server=local_url.split("://", 1)[1],
                        )
                        launch_options["proxy"] = local_cfg.model_dump()
                    else:
                        # For Camoufox / Playwright: MUST only have 'server', no 'type' or extra fields!
                        launch_options["proxy"] = {"server": local_url}
                except Exception as exc:
                    logger.warning(f"Failed to start local proxy forwarder for {profile_id}: {exc}")
                    if forwarder:
                        await forwarder.stop()
                        forwarder = None
        elif engine != "chromium" and "proxy" in launch_options:
            # If not bridged, ensure Camoufox proxy dict contains strictly valid keys (server, username, password, bypass)
            p_dict = launch_options.get("proxy")
            if isinstance(p_dict, dict):
                valid_keys = {"server", "username", "password", "bypass"}
                launch_options["proxy"] = {k: v for k, v in p_dict.items() if k in valid_keys and v is not None}

        if engine == "chromium":
            from .chromium_launcher import launch_chromium_process

            self._starting[profile_id] = self._starting.get(profile_id, 0) + 1
            try:
                proc, pid, cdp_port = await launch_chromium_process(profile_id, launch_options)
                u_dir = Path(launch_options["user_data_dir"]) if launch_options.get("user_data_dir") else None
                session = BrowserSession(
                    profile_id=profile_id,
                    camoufox=None,
                    process_id=pid,
                    process=proc,
                    engine="chromium",
                    cdp_port=cdp_port,
                    profile_path=u_dir,
                    proxy_forwarder=forwarder,
                )
                session.on_exit = on_exit
                self.active_sessions[profile_id] = session
            except Exception as exc:
                if forwarder:
                    await forwarder.stop()
                raise BrowserLaunchError(f"Failed to launch Chromium: {exc}") from exc
            finally:
                remaining = self._starting.get(profile_id, 1) - 1
                if remaining > 0:
                    self._starting[profile_id] = remaining
                else:
                    self._starting.pop(profile_id, None)

            session.monitor_task = asyncio.create_task(
                self._monitor_process(profile_id, proc, cdp_port)
            )
            logger.info(f"Chromium launched for profile {profile_id} (pid={pid}, cdp={cdp_port})")
            return session

        # Camoufox engine
        if not CAMOUFOX_AVAILABLE:
            raise BrowserLaunchError(
                "Camoufox is not installed. Install it with: pip install 'camoufox[geoip]'"
            )

        # Counted before the first await: from here until the session is
        # registered, is_live() says this profile is coming up, and nothing
        # may hand its lease away.
        self._starting[profile_id] = self._starting.get(profile_id, 0) + 1
        try:
            try:
                user_data_dir = launch_options.get("user_data_dir")
                if user_data_dir:
                    u_dir = Path(user_data_dir)
                    _clean_stale_sessions(u_dir)
                    try:
                        chrome_dir = u_dir / "chrome"
                        chrome_dir.mkdir(parents=True, exist_ok=True)
                        user_chrome_css = """/* Camoufox Clean Native UI Styles */
toolbarspring,
.titlebar-spacer,
[id^="customizableui-special-spring"],
.vertical-spacer,
#nav-bar-overflow-button,
#smartwindow-ask-button,
#smartwindow-ask-button-inner,
#smartwindow-group-tabs-button,
#ai-window-toggle,
#taskbar-tabs-button,
#taskbar-tabs-audio,
#document-pip-return-to-opener-button,
#sidebar-button,
#fxa-toolbar-menu-button,
#developer-button,
#reset-pbm-toolbar-button {
    display: none !important;
    visibility: collapse !important;
    width: 0 !important;
    max-width: 0 !important;
    min-width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
}

/* Hide Taskbar Tabs button in urlbar */
#taskbar-tabs-button {
    display: none !important;
    visibility: collapse !important;
    width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Hide new tab extension takeover warning dialog */
#extension-notification-panel,
#extension-new-tab-notification,
.extension-controlled-notification,
popupnotification[popupid="extension-new-tab"] {
    display: none !important;
    visibility: collapse !important;
}

/* Ensure native + button is displayed right next to tabs */
#tabbrowser-tabs[orient="horizontal"] #tabs-newtab-button,
#tabbrowser-tabs:not([hasadjacentnewtabbutton])[orient="horizontal"] #tabs-newtab-button,
#tabs-newtab-button {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    list-style-image: url("chrome://global/skin/icons/plus.svg") !important;
}

#tabs-newtab-button > .toolbarbutton-icon {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    width: 16px !important;
    height: 16px !important;
}

#tabbrowser-arrowscrollbox-periphery {
    display: flex !important;
    visibility: visible !important;
}
"""
                        (chrome_dir / "userChrome.css").write_text(user_chrome_css, encoding="utf-8")
                        user_js_file = u_dir / "user.js"
                        u_content = user_js_file.read_text(encoding="utf-8", errors="ignore") if user_js_file.exists() else ""
                        pref_str1 = 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);'
                        pref_str2 = 'user_pref("browser.taskbarTabs.enabled", false);'
                        bs_dict = launch_options.get("browser_settings", {})
                        fx_langs = bs_dict.get("languages") if isinstance(bs_dict, dict) else getattr(bs_dict, "languages", None)

                        with user_js_file.open("a", encoding="utf-8") as f:
                            if pref_str1 not in u_content:
                                f.write(f"\n{pref_str1}\n")
                            if pref_str2 not in u_content:
                                f.write(f"\n{pref_str2}\n")
                            if fx_langs and isinstance(fx_langs, list) and len(fx_langs) > 0:
                                lang_accept = ", ".join(fx_langs)
                                pref_str_lang = f'user_pref("intl.accept_languages", "{lang_accept}");'
                                pref_str_loc = f'user_pref("general.useragent.locale", "{fx_langs[0]}");'
                                if "intl.accept_languages" not in u_content:
                                    f.write(f"\n{pref_str_lang}\n")
                                if "general.useragent.locale" not in u_content:
                                    f.write(f"\n{pref_str_loc}\n")
                    except Exception:
                        pass

                camoufox_kwargs = dict(launch_options)
                camoufox_kwargs.pop("browser_settings", None)
                startup_target = camoufox_kwargs.pop("startup_url", None)
                open_radar = camoufox_kwargs.pop("open_health_radar", True)
                camoufox_kwargs.pop("raw_proxy", None)
                if "proxy" in camoufox_kwargs and isinstance(camoufox_kwargs["proxy"], dict):
                    valid_proxy_keys = {"server", "username", "password", "bypass"}
                    camoufox_kwargs["proxy"] = {
                        k: v for k, v in camoufox_kwargs["proxy"].items()
                        if k in valid_proxy_keys and v is not None
                    }

                camoufox = AsyncCamoufox(**camoufox_kwargs)
                browser = await camoufox.start()

                try:
                    pages = getattr(browser, "pages", [])
                    init_page = pages[0] if pages else await browser.new_page()
                    if startup_target:
                        asyncio.create_task(init_page.goto(startup_target))
                except Exception as exc:
                    logger.warning(f"Could not navigate Camoufox initial page: {exc}")
            except Exception as exc:  # noqa: BLE001
                if forwarder:
                    await forwarder.stop()
                raise BrowserLaunchError(f"Failed to launch browser: {exc}") from exc

            process_id = _resolve_process_id(browser) or _resolve_process_id(camoufox)
            session = BrowserSession(
                profile_id=profile_id,
                camoufox=camoufox,
                process_id=process_id,
                profile_path=user_data_dir,
                engine="camoufox",
                proxy_forwarder=forwarder,
            )
            session.on_exit = on_exit
            self.active_sessions[profile_id] = session
        finally:
            remaining = self._starting.get(profile_id, 1) - 1
            if remaining > 0:
                self._starting[profile_id] = remaining
            else:
                self._starting.pop(profile_id, None)

        # Primary signal: the browser/context closing (e.g. the user closes the window).
        self._register_close_handler(browser, profile_id)
        # Fallback: poll the driver pid, only if we could resolve one.
        if process_id:
            session.monitor_task = asyncio.create_task(self._monitor(profile_id, process_id))

        logger.info(f"Camoufox launched for profile {profile_id} (pid={process_id})")
        return session

    def _register_close_handler(self, browser: Any, profile_id: str) -> None:
        """Wire Playwright close/disconnect events and window close watcher to session cleanup."""
        loop = asyncio.get_running_loop()

        def _on_close(*_: Any) -> None:
            task = loop.create_task(self._handle_exit(profile_id))
            self._exit_tasks.add(task)
            task.add_done_callback(self._exit_tasks.discard)

        for event in ("close", "disconnected"):
            try:
                browser.on(event, _on_close)
            except Exception:  # noqa: BLE001 - Browser vs BrowserContext expose different events
                continue

        # Watch for all pages closing (especially on macOS where closing windows does not exit the app)
        def _check_empty_pages() -> None:
            async def _delayed_check() -> None:
                await asyncio.sleep(0.5)
                if profile_id not in self.active_sessions:
                    return
                pages = getattr(browser, "pages", [])
                if len(pages) == 0:
                    logger.info(f"All browser windows closed for {profile_id}, terminating session")
                    await self._handle_exit(profile_id)
            task = loop.create_task(_delayed_check())
            self._exit_tasks.add(task)
            task.add_done_callback(self._exit_tasks.discard)

        def _attach_page(p: Any) -> None:
            try:
                p.on("close", _check_empty_pages)
            except Exception:
                pass

        for p in getattr(browser, "pages", []):
            _attach_page(p)

        try:
            browser.on("page", _attach_page)
        except Exception:
            pass

    async def _handle_exit(self, profile_id: str) -> None:
        """Tear down a session exactly once and notify the exit handler."""
        session = self.active_sessions.pop(profile_id, None)
        if session is None:
            return
        await session.terminate()
        # The browser is gone, so the lease must not outlive it. release_lease
        # is guarded on the holder id, so a lease already taken over by another
        # instance is left exactly where it is.
        await self._release_lease(profile_id)
        if session.on_exit is not None:
            try:
                await session.on_exit(profile_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"on_exit handler failed for {profile_id}: {exc}")

    async def close(self, profile_id: str) -> bool:
        """Close a single browser. Returns ``False`` if it was not running."""
        session = self.active_sessions.pop(profile_id, None)
        if session is None:
            return False
        await session.terminate()
        return True

    async def close_and_release(self, profile_id: str) -> bool:
        """Close a browser and hand its lease back, if we still hold it.

        Separate from :meth:`close` because one caller must not release: when
        the heartbeat finds a lease gone, the browser still has to be closed,
        and clearing the lease then would clear the *new* holder's.
        """
        closed = await self.close(profile_id)
        if closed:
            await self._release_lease(profile_id)
        return closed

    async def _release_lease(self, profile_id: str) -> None:
        """Best-effort lease release. Teardown must not fail on bookkeeping."""
        if self._storage is None or self._holder is None:
            return
        try:
            await self._storage.release_lease(profile_id, self._holder)
        except Exception as exc:  # noqa: BLE001 - a stuck release must not block cleanup
            logger.warning(f"Could not release the lease on {profile_id}: {exc}")

    async def close_all(self) -> int:
        """Close every active browser concurrently and return how many were closed."""
        profile_ids = list(self.active_sessions.keys())
        count = 0
        if profile_ids:
            tasks = [self.close_and_release(pid) for pid in profile_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            count = sum(1 for r in results if r is True)
        # Always run synchronous cleanup fallback to catch any unmanaged or orphaned browsers
        try:
            cleanup_all_browsers_sync()
        except Exception as exc:
            logger.warning(f"Error in close_all cleanup_all_browsers_sync: {exc}")
        return count


    async def _monitor(self, profile_id: str, process_id: int) -> None:
        """Fallback watchdog: clean up if the driver process disappears."""
        while psutil.pid_exists(process_id):
            await asyncio.sleep(10)
        await self._handle_exit(profile_id)

    async def _monitor_process(
        self, profile_id: str, proc: asyncio.subprocess.Process, cdp_port: int | None = None
    ) -> None:
        """Watchdog for Chromium subprocess: triggers exit handler immediately when all windows close."""
        import httpx

        has_had_page = False
        consecutive_empty = 0
        consecutive_errors = 0

        while proc.returncode is None:
            if cdp_port:
                try:
                    async with httpx.AsyncClient(timeout=1.0) as client:
                        resp = await client.get(f"http://127.0.0.1:{cdp_port}/json/list")
                        if resp.status_code == 200:
                            targets = resp.json()
                            pages = [t for t in targets if t.get("type") == "page"]
                            if pages:
                                has_had_page = True
                                consecutive_empty = 0
                                consecutive_errors = 0
                            elif has_had_page and not pages:
                                consecutive_empty += 1
                                if consecutive_empty >= 3:
                                    logger.info(
                                        f"All Chromium windows closed for profile {profile_id}. Terminating process."
                                    )
                                    try:
                                        proc.terminate()
                                    except Exception:
                                        pass
                                    break
                except Exception:
                    consecutive_errors += 1
                    if has_had_page and consecutive_errors >= 3:
                        # CDP endpoint closed after having pages; browser has closed
                        try:
                            proc.terminate()
                        except Exception:
                            pass
                        break

            # Check if process exited on its own
            try:
                await asyncio.wait_for(asyncio.shield(proc.wait()), timeout=1.5)
                break
            except (asyncio.TimeoutError, TimeoutError):
                pass

        try:
            await proc.wait()
        except Exception:
            pass
        await self._handle_exit(profile_id)


def cleanup_all_browsers_sync(data_dir: Path | str | None = None) -> None:
    """Synchronously force-terminate any orphaned Camoufox, Firefox, Chromium, or Google Chrome fingerprint browser processes."""
    curr_pid = psutil.Process().pid
    keywords = [
        "camoufox",
        "chromium",
        "chrome",
        "google chrome",
        "firefox",
        "cpm_anti_detect_extension",
        "cpm_radar_extension",
    ]

    data_dir_parts: list[str] = []
    if data_dir:
        d_path = Path(data_dir)
        if d_path.is_file() or str(d_path).endswith(".db"):
            d_path = d_path.parent
        data_dir_parts.append(str(d_path))
        data_dir_parts.append(str(d_path / "profiles"))
    else:
        try:
            from camoufox_pm.config import get_settings
            d_path = Path(get_settings().db_path).resolve().parent
            data_dir_parts.append(str(d_path))
            data_dir_parts.append(str(d_path / "profiles"))
        except Exception:
            pass
        try:
            from camoufox_pm.config import desktop_data_dir
            d_path = desktop_data_dir()
            data_dir_parts.append(str(d_path))
            data_dir_parts.append(str(d_path / "profiles"))
        except Exception:
            pass

    to_kill: dict[int, psutil.Process] = {}

    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.pid == curr_pid:
                continue
            cmdline = " ".join(p.info.get("cmdline") or [])
            cmdline_lower = cmdline.lower()
            name_lower = (p.info.get("name") or "").lower()

            is_browser_binary = any(kw in cmdline_lower or kw in name_lower for kw in keywords)
            if not is_browser_binary:
                continue

            # Ensure it is a fingerprint profile managed by CamouHub (never kill user's personal unmanaged browsers)
            is_cpm_browser = False
            if "camoufox profile manager" in cmdline_lower or "camouhub" in cmdline_lower:
                is_cpm_browser = True
            elif "cpm_anti_detect_extension" in cmdline or "cpm_radar_extension" in cmdline:
                is_cpm_browser = True
            elif "--user-data-dir=" in cmdline:
                if (
                    (data_dir_parts and any(dp in cmdline for dp in data_dir_parts))
                    or "/profiles/" in cmdline
                    or "\\profiles\\" in cmdline
                    or "data/profiles" in cmdline
                    or "cpm" in cmdline_lower
                    or "profile_" in cmdline
                ):
                    is_cpm_browser = True
            elif "-profile" in cmdline or "--profile" in cmdline:
                if (
                    (data_dir_parts and any(dp in cmdline for dp in data_dir_parts))
                    or "/profiles/" in cmdline
                    or "\\profiles\\" in cmdline
                    or "data/profiles" in cmdline
                    or "camoufox" in cmdline_lower
                    or "profile_" in cmdline
                ):
                    is_cpm_browser = True
            elif data_dir_parts and any(dp in cmdline for dp in data_dir_parts):
                is_cpm_browser = True

            if is_cpm_browser:
                to_kill[p.pid] = p
                try:
                    for child in p.children(recursive=True):
                        to_kill[child.pid] = child
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass

    if to_kill:
        logger.info(f"cleanup_all_browsers_sync: found {len(to_kill)} process(es) to terminate: {list(to_kill.keys())}")
        for proc in to_kill.values():
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        gone, alive = psutil.wait_procs(list(to_kill.values()), timeout=2.0)
        for proc in alive:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        logger.info(f"cleanup_all_browsers_sync: terminated {len(gone)} process(es)")

