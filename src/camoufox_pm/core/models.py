"""Data models for the Camoufox profile management system."""

import json
import re
import secrets
import string
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from loguru import logger

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Characters used for short IDs, excluding visually confusing ones (0, o, 1, l, i).
_ID_ALPHABET = "".join(c for c in (string.ascii_lowercase + string.digits) if c not in "0o1li")


def generate_short_id(length: int = 8) -> str:
    """Generate a short, readable ID.

    Every character is random, drawn from an alphabet without visually confusing
    characters (0/o, 1/l/i), which gives 31**8 ≈ 8.5e11 possible IDs at the
    default length.

    This used to derive most of the ID from a microsecond timestamp and leave
    only two random characters. IDs minted in the same microsecond — which is
    what a bulk Excel import does — then had just 961 possible values, and
    because profiles are stored with INSERT OR REPLACE keyed on the ID, a
    collision silently overwrote an existing profile.
    """
    return "".join(secrets.choice(_ID_ALPHABET) for _ in range(length))


def generate_profile_id() -> str:
    """Generate a short ID for a profile."""
    return generate_short_id(8)


def generate_group_id() -> str:
    """Generate a short ID for a group."""
    return generate_short_id(8)


def generate_schedule_id() -> str:
    """Generate a short ID for a schedule."""
    return generate_short_id(8)


class ProfileStatus(str, Enum):
    """Profile status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    MAINTENANCE = "maintenance"


class ProxyType(str, Enum):
    """Proxy protocol."""

    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class WebRTCMode(str, Enum):
    """WebRTC IP spoofing mode."""

    FORWARD = "forward"  # Forward the real IP
    REPLACE = "replace"  # Replace with the proxy IP
    REAL = "real"  # Use the real IP
    NONE = "none"  # Disable WebRTC


class ProxyConfig(BaseModel):
    """Proxy configuration."""

    type: ProxyType
    server: str
    username: str | None = None
    password: str | None = None
    country: str | None = None

    def to_camoufox_format(self) -> dict[str, str]:
        """Convert to the proxy dict Camoufox/Playwright expects."""
        config = {"server": f"{self.type.value}://{self.server}"}
        if self.username:
            config["username"] = self.username
        if self.password:
            config["password"] = self.password
        return config


class BrowserSettings(BaseModel):
    """Browser fingerprint and behaviour settings.

    High-level fields (os, screen, languages, fonts) are handed to Camoufox,
    which generates a consistent fingerprint. Only explicit overrides that
    Camoufox cannot derive on its own are emitted via :meth:`to_camoufox_config`.
    """

    # Browser chrome only; fingerprint and privacy settings remain independent.
    browser_ui: Literal["desktop", "camoufox"] = "desktop"
    browser_engine: Literal["chromium", "camoufox"] = "camoufox"

    # Base settings
    os: str = "macos" if sys.platform == "darwin" else "windows"  # windows, linux, macos
    screen: str = "1920x1080"
    user_agent: str | None = None
    languages: list[str] = ["en-US", "en"]
    timezone: str | None = None
    locale: str | None = None

    # Browser window & display
    window_width: int | None = 1280
    window_height: int | None = 720
    device_pixel_ratio: float = 1.0

    # Geolocation
    geolocation: dict[str, float] | None = None

    # WebRTC
    webrtc_mode: WebRTCMode = WebRTCMode.REPLACE
    webrtc_public_ip: str | None = None
    webrtc_local_ips: list[str] | None = None

    # Device characteristics
    hardware_concurrency: int | None = None
    device_memory: int | None = None
    max_touch_points: int = 0

    # Fingerprint noise preferences. Camoufox applies canvas/WebGL/audio spoofing
    # itself; these flags are stored intent and are not forwarded as config keys.
    canvas_noise: bool = True
    webgl_noise: bool = True
    audio_noise: bool = True
    client_rects_noise: bool = True
    battery_spoofing: bool = True
    do_not_track: bool = False

    # WebGL vendor & renderer spoofing
    webgl_vendor: str | None = None
    webgl_renderer: str | None = None

    # Secure DNS (DoH)
    doh_provider: str | None = None

    # Default Search Engine (google, bing, baidu, duckduckgo)
    search_engine: str = "google"

    # Automation / Remote Debugging Port (CDP)
    remote_debugging_port: int | None = None

    # Custom CLI arguments
    custom_args: list[str] = Field(default_factory=list)

    # Make the canvas reproducible across launches instead of randomised per
    # session. Off by default: it trades cross-site unlinkability for a canvas
    # that behaves like real hardware. See to_camoufox_launch_options().
    stable_canvas: bool = False

    # Advanced stealth: OS-specific Font Masking & Isolation
    font_masking: bool = True

    # Virtual Isolated Clipboard Sandbox (Anti-Snoop)
    clipboard_isolation: bool = True

    # Custom startup URL & Health Radar Start Page
    startup_url: str | None = None
    open_health_radar: bool = True

    # Fonts
    fonts: list[str] | None = None

    def has_geography(self) -> bool:
        """Whether this profile states where it is instead of following its proxy."""
        return bool(self.timezone or self.geolocation)

    def clear_geography(self) -> bool:
        """Drop the stated location so the proxy's exit address supplies it again.

        Only the two fields Camoufox derives from that address. Languages and
        locale are left alone: they are not geography — Camoufox applies them
        after its IP lookup regardless, and an English browser is unremarkable
        from any country — so clearing them would change the profile's identity
        rather than free it to follow the proxy.
        """
        if not self.has_geography():
            return False
        self.timezone = None
        self.geolocation = None
        return True

    def to_camoufox_config(self) -> dict[str, Any]:
        """Build Camoufox ``config`` property overrides.

        Only values Camoufox does not derive itself are included; the browser's
        own generator owns user-agent, WebGL, canvas and audio to keep the
        fingerprint internally consistent.
        """
        config: dict[str, Any] = {"disableTheming": self.browser_ui == "desktop"}
        if self.browser_ui == "desktop":
            config["showcursor"] = False
        if self.geolocation:
            config["geolocation:latitude"] = self.geolocation["lat"]
            config["geolocation:longitude"] = self.geolocation["lon"]
            if "accuracy" in self.geolocation:
                config["geolocation:accuracy"] = self.geolocation["accuracy"]
        if self.timezone:
            config["timezone"] = self.timezone
        if self.hardware_concurrency:
            config["navigator.hardwareConcurrency"] = self.hardware_concurrency
        if self.max_touch_points:
            config["navigator.maxTouchPoints"] = self.max_touch_points
        # webrtc_local_ips is intentionally not emitted. The webrtc:localipv4 key
        # does exist, but setting it replaces the mDNS candidate a real Firefox
        # sends with a literal address. Leaving it alone keeps the real behaviour.
        if self.webrtc_public_ip:
            config["webrtc:ipv4"] = self.webrtc_public_ip

        # Ensure screen resolution is realistic and aligned with chosen OS
        sw, sh = (1512, 982) if self.os == "macos" else (1920, 1080)
        if getattr(self, "screen", None) and "x" in self.screen:
            try:
                sw, sh = (int(p) for p in self.screen.split("x"))
            except Exception:
                pass
        elif self.window_width and self.window_height:
            sw, sh = self.window_width, self.window_height

        config["screen.width"] = sw
        config["screen.height"] = sh
        config["screen.availWidth"] = sw
        avail_h = max(sh - 38, 600) if self.os == "macos" else max(sh - 40, 600)
        config["screen.availHeight"] = avail_h
        color_depth = 30 if self.os == "macos" and sw == 1512 else 24
        config["screen.colorDepth"] = color_depth
        config["screen.pixelDepth"] = color_depth
        return config


# What a finding means, defined here because both the live check and the record
# kept on a profile carry one — two definitions would be two types for the same
# value in the same API response.
Level = Literal["error", "warning", "info"]


class ProxyCheckFinding(BaseModel):
    """One thing worth telling the user about this proxy and this profile."""

    level: Level
    field: str
    message: str


class ProxyCheckRecord(BaseModel):
    """The last answer a profile's proxy gave, kept so the list can show it.

    Deliberately smaller than the live check: no coordinates, because the list
    shows where the proxy comes out, not where on the map. Whether the dot is
    green, amber or red is derived from `reachable` and the findings rather than
    stored, so an old row cannot disagree with the rules that read it.
    """

    checked_at: datetime
    reachable: bool
    error: str | None = None
    latency_ms: int | None = None
    ip: str | None = None
    country: str | None = None
    timezone: str | None = None
    findings: list[ProxyCheckFinding] = Field(default_factory=list)


class Profile(BaseModel):
    """Browser profile."""

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=generate_profile_id)
    name: str
    user_id: str | None = None
    group: str | None = None
    status: ProfileStatus = ProfileStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_used: datetime | None = None
    deleted_at: datetime | None = None

    browser_settings: BrowserSettings = Field(default_factory=BrowserSettings)
    proxy: ProxyConfig | None = None
    extensions: list[str] = Field(default_factory=list)
    storage_path: str | None = None
    notes: str | None = None
    cookies: str | None = None
    account: str | None = None
    is_favorite: bool = False
    tags: list[str] = Field(default_factory=list)

    # The machine this profile pretends to be, resolved once on first launch and
    # replayed from then on so the profile does not look like new hardware every
    # session. See core/fingerprint_store.py for what is frozen and what is not.
    fingerprint: dict[str, Any] | None = None

    # The last time this profile's proxy was checked, so the list can show it
    # without checking again. Cleared when the proxy changes: an answer from the
    # old proxy says nothing about the new one.
    proxy_check: ProxyCheckRecord | None = None

    # Optimistic-concurrency counter, bumped by every version-checked save. A
    # caller reads a profile, edits it, and writes back against the version it
    # read; a save that landed in between makes the write fail loudly instead of
    # reverting it. Storage bookkeeping rather than profile data, but the API
    # exposes it so a client editing a form can pass back the version it loaded.
    row_version: int = 0

    def get_storage_path(self, base_path: str = "data/profiles") -> str:
        """Return (and lazily assign) the on-disk path for this profile's data."""
        if not self.storage_path:
            self.storage_path = f"{base_path}/profile_{self.id}"
        return self.storage_path

    def to_camoufox_launch_options(self) -> dict[str, Any]:
        """Build the keyword arguments passed to ``AsyncCamoufox``.

        Passes high-level constraints and lets Camoufox generate the fingerprint;
        does not inject a manual user-agent or WebGL renderer.
        """
        bs = self.browser_settings
        bs_dict = bs.model_dump()
        if self.proxy_check:
            if not bs_dict.get("timezone") and self.proxy_check.timezone:
                bs_dict["timezone"] = self.proxy_check.timezone
            if self.proxy_check.country:
                from .geo_utils import get_languages_for_country
                country_langs = get_languages_for_country(self.proxy_check.country)
                cur_langs = bs_dict.get("languages") or []
                if not cur_langs or cur_langs == ["en-US", "en"] or cur_langs == ["zh-CN", "zh"]:
                    bs_dict["languages"] = country_langs

        target_os = bs.os
        if sys.platform == "darwin" and target_os == "windows":
            # On macOS host, setting Windows platform causes Cocoa UI font/character codepage corruption.
            # Using macos preserves pristine native Cocoa fonts and prevents corrupted URL bar typing.
            target_os = "macos"

        effective_langs = bs_dict.get("languages") or bs.languages or ["en-US"]
        options: dict[str, Any] = {
            "os": target_os,
            "locale": ",".join(effective_langs) if effective_langs else "en-US",
            "config": bs.to_camoufox_config(),
            "user_data_dir": self.get_storage_path(),
            "persistent_context": True,
            "humanize": True,
            "i_know_what_im_doing": True,
            # Let Camoufox derive geo/timezone from the proxy IP unless we set coordinates.
            "geoip": not bool(bs.geolocation),
        }
        # "none" fully disables WebRTC; other modes use Camoufox's default handling
        # (which reports the proxy's public IP when a proxy is set).
        if bs.webrtc_mode == WebRTCMode.NONE:
            options["block_webrtc"] = True

        # Allow extensions to control new tab / tabs
        config = options.setdefault("config", {})
        config["allowAddonNewtab"] = True

        ff_prefs = options.setdefault("firefox_user_prefs", {})
        ff_prefs.setdefault("browser.startup.page", 1)
        startup_target = getattr(bs, "startup_url", None)
        if startup_target:
            ff_prefs["browser.startup.homepage"] = startup_target
        else:
            ff_prefs.setdefault("browser.startup.homepage", "about:newtab")
        ff_prefs.setdefault("browser.sessionstore.resume_from_crash", False)
        ff_prefs.setdefault("browser.sessionstore.max_resumed_crashes", 0)
        ff_prefs.setdefault("browser.urlbar.suggest.searches", True)

        # 1. Native Firefox Radar WebExtension Integration (Matching Hubstudio NewTab Override)
        open_radar = getattr(bs, "open_health_radar", True)
        if open_radar:
            try:
                from camoufox_pm.api.routes.radar import generate_radar_html_str, generate_radar_js_str
                profile_dir = Path(self.storage_path or self.get_storage_path())
                addon_dir = profile_dir / "cpm_radar_extension"
                addon_dir.mkdir(parents=True, exist_ok=True)

                manifest_data = {
                    "manifest_version": 2,
                    "name": "Camoufox Environment Radar",
                    "version": "1.0.0",
                    "description": "Native integrated health radar tab",
                    "chrome_url_overrides": {
                        "newtab": "radar.html"
                    },
                    "background": {
                        "scripts": ["background.js"]
                    },
                    "permissions": [
                        "tabs"
                    ],
                    "browser_specific_settings": {
                        "gecko": {
                            "id": f"radar-{self.id}@camoufox.local"
                        }
                    }
                }
                (addon_dir / "manifest.json").write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

                bg_js = """const radarUrl = browser.runtime.getURL("radar.html");

async function initStartupTab() {
  try {
    const tabs = await browser.tabs.query({ active: true, currentWindow: true });
    if (tabs && tabs.length > 0) {
      const tab = tabs[0];
      if (!tab.url || tab.url === "about:blank" || tab.url.includes("about:newtab") || tab.url.includes("about:home")) {
        await browser.tabs.update(tab.id, { url: radarUrl });
      }
    }
  } catch (e) {
    console.error("Init startup tab error:", e);
  }
}

initStartupTab();

browser.tabs.onCreated.addListener((tab) => {
  // If tab was opened from an existing page (link click, window.open, etc), NEVER intercept!
  if (tab.openerTabId) {
    return;
  }
  // If tab has a destination URL assigned or pending, NEVER intercept!
  if (tab.pendingUrl && !tab.pendingUrl.startsWith("about:")) {
    return;
  }
  if (tab.url && !tab.url.startsWith("about:")) {
    return;
  }
  // Only override pure new-tab pages without openers
  if (tab.url === "about:newtab" || tab.url === "about:home") {
    browser.tabs.update(tab.id, { url: radarUrl });
  }
});
"""
                (addon_dir / "background.js").write_text(bg_js, encoding="utf-8")

                langs = bs_dict.get("languages") or bs.languages or ["zh-CN"]
                l_str = ", ".join(langs) if isinstance(langs, list) and langs else str(langs or "zh-CN")
                tz = bs_dict.get("timezone") or bs.timezone or "Asia/Shanghai"
                raw_os = (getattr(bs, "os", None) or "windows").lower()
                os_map = {
                    "macos": "macOS",
                    "windows": "Windows",
                    "linux": "Linux",
                    "android": "Android",
                    "ios": "iOS",
                }
                os_display = os_map.get(raw_os, raw_os.capitalize())
                arch_map = {
                    "macos": "ARM64 / Apple Silicon",
                    "windows": "x86_64 架构",
                    "linux": "x86_64 架构",
                    "android": "ARM64 移动架构",
                    "ios": "Apple A-Series 移动架构",
                }
                arch_display = arch_map.get(raw_os, "x86_64 架构")
                cores = bs.hardware_concurrency or 8
                mem = bs.device_memory or 8
                w = bs.window_width or 1280
                h = bs.window_height or 720
                proxy_cfg = self.proxy
                p_type_str = str(proxy_cfg.type.value if hasattr(proxy_cfg.type, "value") else proxy_cfg.type).upper() if proxy_cfg else ""
                proxy_display = f"{p_type_str} {proxy_cfg.server}" if proxy_cfg and proxy_cfg.server else "直连模式 (Direct)"

                ua_str = getattr(bs, "user_agent", None) or ""
                if not ua_str:
                    if raw_os == "macos":
                        ua_str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0"
                    elif raw_os == "android":
                        ua_str = "Mozilla/5.0 (Android 14; Mobile; rv:135.0) Gecko/135.0 Firefox/135.0"
                    elif raw_os == "ios":
                        ua_str = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/135.0 Mobile/15E148 Safari/605.1.15"
                    elif raw_os == "linux":
                        ua_str = "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0"
                    else:
                        ua_str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0"

                radar_html = generate_radar_html_str(
                    env_name=self.name or self.id,
                    group_name=getattr(self, "group", None) or "未分组",
                    notes=self.notes or "--",
                    account=self.account or "",
                    lang_str=l_str,
                    timezone=tz,
                    ua_str=ua_str,
                    os_name=os_display,
                    arch_str=arch_display,
                    cpu_cores=cores,
                    memory_gb=mem,
                    screen_res=f"{w} × {h}",
                    webgl_vendor=bs.webgl_vendor or "Google Inc. (ANGLE)",
                    webgl_renderer=bs.webgl_renderer or "ANGLE (Direct3D11)",
                    engine_name="Camoufox 135",
                    proxy_info=proxy_display,
                    init_ip="探查中...",
                )
                radar_js = generate_radar_js_str(timezone=tz, expected_languages=langs)
                (addon_dir / "radar.html").write_text(radar_html, encoding="utf-8")
                (addon_dir / "radar.js").write_text(radar_js, encoding="utf-8")

                # Pre-confirm extension newTabNotification in extension-settings.json to prevent doorhanger prompt
                try:
                    ext_id = f"radar-{self.id}@camoufox.local"
                    settings_file = profile_dir / "extension-settings.json"
                    s_data = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.exists() else {}
                    s_data.setdefault("version", 3)
                    s_data.setdefault("commands", {})
                    s_data.setdefault("prefs", {})
                    s_data.setdefault("url_overrides", {})
                    s_data.setdefault("default_search", {})
                    s_data.setdefault("homepageNotification", {})
                    s_data.setdefault("tabHideNotification", {})
                    new_tab_notif = s_data.setdefault("newTabNotification", {})
                    new_tab_notif[ext_id] = {
                        "initialValue": None,
                        "precedenceList": [
                            {
                                "id": ext_id,
                                "installDate": 1791871149000,
                                "value": True,
                                "enabled": True,
                            }
                        ],
                    }
                    settings_file.write_text(json.dumps(s_data, indent=2), encoding="utf-8")
                except Exception:
                    pass

                addons_list = options.setdefault("addons", [])
                if str(addon_dir) not in addons_list:
                    addons_list.append(str(addon_dir))
            except Exception as exc:
                logger.warning(f"Failed to generate radar extension for Camoufox: {exc}")

        # 2. Clean Toolbars without annoying spring spaces and disable taskbarTabs
        customization_state = {
            "placements": {
                "widget-overflow-fixed-list": [],
                "unified-extensions-area": [],
                "nav-bar": [
                    "back-button",
                    "forward-button",
                    "stop-reload-button",
                    "urlbar-container",
                    "downloads-button",
                    "unified-extensions-button",
                    "ublock0_raymondhill_net-browser-action",
                ],
                "TabsToolbar": [
                    "tabbrowser-tabs",
                    "new-tab-button",
                ],
                "vertical-tabs": [],
                "PersonalToolbar": ["personal-bookmarks"],
            },
            "seen": ["developer-button"],
            "dirtyAreaCache": ["nav-bar", "TabsToolbar", "PersonalToolbar"],
            "currentVersion": 26,
            "newElementCount": 0,
        }
        ff_prefs["browser.uiCustomization.state"] = json.dumps(customization_state)
        ff_prefs["browser.tabs.closeTabByDblclick"] = False
        ff_prefs["browser.newtabpage.enabled"] = True
        ff_prefs["browser.tabs.loadInBackground"] = True
        ff_prefs["browser.taskbarTabs.enabled"] = False
        ff_prefs["toolkit.legacyUserProfileCustomizations.stylesheets"] = True

        # 3. Inject userChrome.css to place + next to tabs, remove taskbar-tabs, and suppress alerts
        try:
            profile_dir = Path(self.storage_path or self.get_storage_path())
            chrome_dir = profile_dir / "chrome"
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
        except Exception:
            pass

        if bs.stable_canvas:
            ff_prefs["privacy.baselineFingerprintingProtection"] = False
        if bs.window_width and bs.window_height:
            options["window"] = (bs.window_width, bs.window_height)
        if bs.fonts:
            options["fonts"] = bs.fonts
        if self.proxy:
            options["proxy"] = self.proxy.to_camoufox_format()
            options["raw_proxy"] = self.proxy
        options["startup_url"] = startup_target
        options["open_health_radar"] = getattr(bs, "open_health_radar", True)
        return options

    def to_chromium_launch_options(self) -> dict[str, Any]:
        """Build options for launching Chromium with isolated data directory and fingerprint flags."""
        bs = self.browser_settings
        storage_path = self.get_storage_path()

        # Auto-align proxy location (timezone & language) if available and not manually overridden
        bs_dict = bs.model_dump()
        if self.proxy_check:
            if not bs_dict.get("timezone") and self.proxy_check.timezone:
                bs_dict["timezone"] = self.proxy_check.timezone
            if self.proxy_check.country:
                from .geo_utils import get_languages_for_country
                country_langs = get_languages_for_country(self.proxy_check.country)
                cur_langs = bs_dict.get("languages") or []
                if not cur_langs or cur_langs == ["en-US", "en"] or cur_langs == ["zh-CN", "zh"]:
                    bs_dict["languages"] = country_langs

        return {
            "profile_id": self.id,
            "profile_name": self.name,
            "group_name": self.group,
            "notes": self.notes,
            "account": getattr(self, "account", ""),
            "user_data_dir": storage_path,
            "browser_settings": bs_dict,
            "proxy": self.proxy.model_dump() if self.proxy else None,
            "raw_proxy": self.proxy,
            "window_size": (bs.window_width or 1280, bs.window_height or 720),
            "remote_debugging_port": bs.remote_debugging_port,
            "custom_args": bs.custom_args,
            "extensions": self.extensions or [],
            "cookies": self.cookies,
        }


class ProfileGroup(BaseModel):
    """A group of profiles."""

    id: str = Field(default_factory=generate_group_id)
    name: str
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    profile_count: int = 0


class UsageStats(BaseModel):
    """Profile usage record."""

    id: int | None = None
    profile_id: str
    action: str
    timestamp: datetime = Field(default_factory=datetime.now)
    duration: int | None = None  # seconds
    success: bool = True
    details: dict[str, Any] | None = None


class ProxyTestResult(BaseModel):
    """Result of testing a proxy."""

    proxy_id: str
    success: bool
    response_time: int | None = None  # milliseconds
    error_message: str | None = None
    ip_address: str | None = None
    country: str | None = None
    tested_at: datetime = Field(default_factory=datetime.now)


class SystemStatus(BaseModel):
    """System status snapshot."""

    total_profiles: int
    active_profiles: int
    running_browsers: int
    total_groups: int
    system_load: float
    memory_usage: float
    disk_usage: float
    uptime_seconds: int


class ScheduleAction(str, Enum):
    """What a schedule does to its profile when it fires.

    Deliberately absent: regenerating the hardware fingerprint. The pinned
    machine exists so a profile stays the same computer between sessions;
    swapping its GPU, screen and cores on a timer would hand a warmed-up
    account new hardware overnight — the one thing the pin prevents. Hardware
    regeneration stays a manual action (reset-fingerprint), which warns about
    the cost. REFRESH_BROWSER is the honest scheduled rotation: it moves only
    the browser version, which is what a real machine does when it updates.
    """

    LAUNCH = "launch"
    REFRESH_BROWSER = "refresh_browser"


class ScheduleKind(str, Enum):
    """How a schedule's fire times are expressed."""

    INTERVAL = "interval"  # every N minutes
    DAILY = "daily"  # at HH:MM on the chosen weekdays


class ScheduleRunOutcome(str, Enum):
    """How one firing of a schedule ended."""

    OK = "ok"
    SKIPPED = "skipped"  # e.g. the browser was already running
    ERROR = "error"
    MISSED = "missed"  # fell due while the process was down; not replayed


_TIME_OF_DAY = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class Schedule(BaseModel):
    """A recurring task against one profile.

    ``at_time`` is read on the server's own clock: this is a single-process
    tool that runs next to its browsers, so "09:00" means 09:00 where the
    process runs, with no timezone bookkeeping to get wrong. ``days`` uses
    Python's weekday numbering, 0 = Monday … 6 = Sunday; empty means every day.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=generate_schedule_id)
    profile_id: str
    action: ScheduleAction
    kind: ScheduleKind
    interval_minutes: int | None = Field(None, ge=1)
    at_time: str | None = None
    days: list[int] | None = None
    # Launch schedules only: close the browser this long after opening it, so a
    # warming session ends by itself instead of staying open until the next run
    # finds it and skips.
    run_minutes: int | None = Field(None, ge=1)
    enabled: bool = True
    next_run_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="after")
    def _expression_is_complete(self) -> "Schedule":
        if self.kind == ScheduleKind.INTERVAL:
            if not self.interval_minutes:
                raise ValueError("An interval schedule needs interval_minutes")
        else:
            if not self.at_time or not _TIME_OF_DAY.match(self.at_time):
                raise ValueError("A daily schedule needs at_time as HH:MM (24-hour)")
        if self.days is not None:
            if any(day < 0 or day > 6 for day in self.days):
                raise ValueError("days entries are weekdays, 0 (Monday) to 6 (Sunday)")
            self.days = sorted(set(self.days)) or None
        if self.action == ScheduleAction.REFRESH_BROWSER and self.run_minutes:
            raise ValueError("run_minutes only applies to launch schedules")
        return self


class ScheduleRun(BaseModel):
    """The record of one firing of a schedule."""

    id: int | None = None
    schedule_id: str
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = None
    outcome: ScheduleRunOutcome
    message: str | None = None

    model_config = ConfigDict(use_enum_values=True)
