"""Native desktop launcher with persistent storage and a private local server."""

import contextlib
import html
import os
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
import psutil
from loguru import logger

_app_terminate_observer = None


class AlreadyRunningError(RuntimeError):
    """The same desktop data directory is already open in another process."""


@contextlib.contextmanager
def _instance_lock(data_dir: Path):
    """Hold an OS lock for the process lifetime; crashes release it automatically."""
    data_dir.mkdir(parents=True, exist_ok=True)
    with (data_dir / "desktop.lock").open("a+b") as lock:
        lock.seek(0)
        if lock.read(1) == b"":
            lock.write(b"\0")
            lock.flush()
        lock.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise AlreadyRunningError(
                "Camoufox Profile Manager is already open. Switch to its existing window."
            ) from exc
        try:
            yield
        finally:
            lock.seek(0)
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _wait_until_serving(
    server: uvicorn.Server, thread: threading.Thread, timeout: float = 30
) -> bool:
    """Wait for this server's lifespan startup, never for an unrelated open port."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and thread.is_alive():
        if server.started:
            return True
        time.sleep(0.05)
    return False


def run_desktop(
    host: str = "127.0.0.1", port: int = 0, title: str = "CamouHub"
) -> None:
    """Serve on a reserved socket and stop browsers/server when the window closes."""
    try:
        import webview
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Desktop mode needs pywebview. From source, run: uv sync --extra desktop"
        ) from exc

    from camoufox_pm.config import bootstrap_desktop, get_settings

    bootstrap_desktop()
    settings = get_settings()
    data_dir = Path(settings.db_path).resolve().parent
    with _instance_lock(data_dir):
        # Prefer a fixed port (e.g. 18888) so that browser origin, cookies,
        # and localStorage remain stable across app restarts.
        # Fall back to an ephemeral port (0) if the preferred port is occupied.
        preferred_port = int(os.environ.get("CPM_PORT") or (settings.port if settings.port != 8000 else 18888))
        ports_to_try = [preferred_port, 0] if port == 0 else [port]
        listener = None
        actual_port = 0
        for p in ports_to_try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sys.platform == "win32":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, p))
                sock.listen(128)
                actual_port = sock.getsockname()[1]
                listener = sock
                break
            except OSError:
                sock.close()
                if p == ports_to_try[-1]:
                    raise RuntimeError(
                        f"Cannot start on {host}:{preferred_port}. Close the app using that port, "
                        "or start CamouHub without a fixed port."
                    ) from None

        with listener:
            os.environ["CPM_HOST"] = host
            os.environ["CPM_PORT"] = str(actual_port)
            get_settings.cache_clear()
            from camoufox_pm.main import app

            server = uvicorn.Server(
                uvicorn.Config(app, host=host, port=actual_port, log_level="info")
            )
            thread = threading.Thread(
                target=server.run, kwargs={"sockets": [listener]}, daemon=True
            )
            thread.start()

            # Optional HubStudio compatibility port 6873 forwarder
            def _fwd_traffic(s1, s2):
                try:
                    while True:
                        buf = s1.recv(4096)
                        if not buf:
                            break
                        s2.sendall(buf)
                except Exception:
                    pass
                finally:
                    s1.close()
                    s2.close()

            def _hub_forwarder_loop(target_p: int):
                try:
                    h_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    h_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    h_sock.bind(("127.0.0.1", 6873))
                    h_sock.listen(64)
                    logger.info(f"HubStudio compat listener active: 127.0.0.1:6873 -> {target_p}")
                    while True:
                        c_sock, _ = h_sock.accept()
                        try:
                            b_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            b_sock.connect(("127.0.0.1", target_p))
                            threading.Thread(target=_fwd_traffic, args=(c_sock, b_sock), daemon=True).start()
                            threading.Thread(target=_fwd_traffic, args=(b_sock, c_sock), daemon=True).start()
                        except Exception:
                            c_sock.close()
                except Exception:
                    pass

            threading.Thread(target=_hub_forwarder_loop, args=(actual_port,), daemon=True).start()

            try:
                if not _wait_until_serving(server, thread):

                    raise RuntimeError(
                        "The local server could not start. See desktop.log in your data folder."
                    )
                ui_host = "127.0.0.1" if host in ("0.0.0.0", "127.0.0.1") else host
                webview_storage = data_dir / "webview"
                webview_storage.mkdir(parents=True, exist_ok=True)
                icon_path = None
                for cand in (
                    Path(sys.executable).parent.parent / "Resources" / "CamouHub.icns",
                    Path(sys.executable).parent / "CamouHub.icns",
                    Path(__file__).resolve().parent.parent.parent / "packaging" / "CamouHub.icns",
                    Path(__file__).resolve().parent.parent.parent / "packaging" / "master_1024.png",
                ):
                    if cand.exists():
                        icon_path = str(cand)
                        break
                window = webview.create_window(
                    title, f"http://{ui_host}:{actual_port}/", width=1280, height=800
                )

                def on_closing():
                    logger.info("Main desktop window closing: terminating all active fingerprint browsers...")
                    try:
                        import urllib.request
                        req = urllib.request.Request(
                            f"http://{ui_host}:{actual_port}/api/v1/system/close-all-browsers",
                            method="POST",
                            headers={"Content-Type": "application/json"}
                        )
                        urllib.request.urlopen(req, timeout=3.0)
                        logger.info("HTTP close-all-browsers succeeded")
                    except Exception as exc:
                        logger.warning(f"HTTP close-all failed ({exc}); falling back to in-memory & OS process kill")

                    # In-memory session cleanup fallback for immediate process tree termination
                    try:
                        from camoufox_pm.api.dependencies import get_profile_manager
                        pm = get_profile_manager()
                        if pm and hasattr(pm, "browser_sessions") and pm.browser_sessions:
                            for session in list(pm.browser_sessions.active_sessions.values()):
                                try:
                                    target_pid = getattr(session, "process_id", None)
                                    if not target_pid and getattr(session, "process", None):
                                        target_pid = getattr(session.process, "pid", None)
                                    if target_pid:
                                        p_obj = psutil.Process(target_pid)
                                        for c in p_obj.children(recursive=True):
                                            try:
                                                c.kill()
                                            except Exception:
                                                pass
                                        p_obj.kill()
                                except Exception as exc:
                                    logger.warning(f"Failed to kill session process: {exc}")
                    except Exception as exc:
                        logger.warning(f"In-memory session cleanup fallback failed: {exc}")

                    try:
                        from camoufox_pm.core.browser_session import cleanup_all_browsers_sync
                        cleanup_all_browsers_sync(data_dir)
                    except Exception as exc:
                        logger.error(f"cleanup_all_browsers_sync failed in on_closing: {exc}")

                def on_closed():
                    logger.info("Main desktop window closed. Ensuring complete application exit...")
                    try:
                        on_closing()
                    except Exception:
                        pass
                    if sys.platform == "darwin":
                        try:
                            import os
                            os._exit(0)
                        except Exception:
                            pass

                window.events.closing += on_closing
                window.events.closed += on_closed

                if sys.platform == "darwin":
                    try:
                        from Foundation import NSNotificationCenter, NSObject
                        from AppKit import NSApplicationWillTerminateNotification

                        class _AppTerminateObserver(NSObject):
                            def onTerminate_(self, notification):
                                try:
                                    logger.info("Received NSApplicationWillTerminateNotification, shutting down browsers...")
                                    on_closing()
                                except Exception as exc:
                                    logger.error(f"Error handling NSApplicationWillTerminateNotification: {exc}")

                        global _app_terminate_observer
                        _app_terminate_observer = _AppTerminateObserver.new()
                        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
                            _app_terminate_observer, "onTerminate:", NSApplicationWillTerminateNotification, None
                        )
                    except Exception as exc:
                        logger.warning(f"Failed to register NSApplicationWillTerminateNotification: {exc}")

                try:
                    import signal
                    def _sig_handler(sig, frame):
                        logger.info(f"Process received signal {sig}, terminating browsers...")
                        try:
                            on_closing()
                        except Exception:
                            pass
                        sys.exit(0)
                    signal.signal(signal.SIGTERM, _sig_handler)
                    signal.signal(signal.SIGINT, _sig_handler)
                except Exception:
                    pass

                webview.start(private_mode=False, storage_path=str(webview_storage), icon=icon_path)
            finally:
                try:
                    on_closing()
                except Exception as exc:
                    logger.warning(f"Error in desktop finally on_closing: {exc}")
                server.should_exit = True
                # Lifespan closes running browser sessions and the database.
                thread.join(timeout=3)
                if thread.is_alive():
                    server.force_exit = True
                    thread.join(timeout=2)
                try:
                    from camoufox_pm.core.browser_session import cleanup_all_browsers_sync
                    cleanup_all_browsers_sync(data_dir)
                except Exception:
                    pass



def _show_error(message: str) -> None:
    """Windowed builds need a visible error even though no console is attached."""
    try:
        import webview

        webview.create_window(
            "Camoufox Profile Manager",
            html=(
                "<html><body style='font:18px system-ui;padding:24px'>"
                "<h1>Camoufox Profile Manager</h1><p>" + html.escape(message) + "</p></body></html>"
            ),
            width=600,
            height=300,
        )
        webview.start()
    except Exception:
        if sys.stderr is not None:
            print(message, file=sys.stderr)


def main() -> None:
    """Double-click entry point; ordinary ``camoufox-pm`` keeps its CLI behavior."""
    import multiprocessing
    multiprocessing.freeze_support()

    if len(sys.argv) > 1 and ("-c" in sys.argv or "--multiprocessing-fork" in sys.argv):
        if "-c" in sys.argv:
            idx = sys.argv.index("-c")
            if idx + 1 < len(sys.argv):
                cmd = sys.argv[idx + 1]
                exec(cmd)
        return

    try:
        from camoufox_pm.config import bootstrap_desktop, get_settings

        bootstrap_desktop()
        import atexit
        from camoufox_pm.core.browser_session import cleanup_all_browsers_sync
        atexit.register(cleanup_all_browsers_sync)
        # PyInstaller windowed apps have no stdout/stderr. Keep logs writable
        # outside the immutable .app / installation directory.
        log_path = Path(get_settings().db_path).resolve().parent / "desktop.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if getattr(sys, "frozen", False) or sys.stdout is None or sys.stderr is None:
            log = log_path.open("a", encoding="utf-8", buffering=1)
            sys.stdout = log
            sys.stderr = log
        run_desktop()
    except Exception as exc:
        import traceback

        if sys.stderr is not None:
            traceback.print_exc(file=sys.stderr)
        _show_error(str(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
