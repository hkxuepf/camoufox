"""Chromium browser launch, isolation and anti-detect fingerprinting management."""

import asyncio
import json
import os
import re
import shutil
import socket
import sys
import time
from pathlib import Path
from typing import Any

from loguru import logger

from .models import BrowserSettings, ProxyConfig, WebRTCMode


def find_free_port() -> int:
    """Find an available local port for CDP monitoring."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


# Dedicated RSA 2048 SubjectPublicKeyInfo (DER base64) for deterministic, cross-platform extension identity
CPM_EXTENSION_PUBLIC_KEY = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAnWescndvsf0weB1dNFbUy5UyR/aLqEJXBzauOBr8vfTU8Qcrxzg3on8"
    "CmHm5YKS8xrsXpY3EpoAZhcPEemM5/tSm/GcALIXXaYvXT6sc6nkj1Qc/kQATuvRS2Ni7n6n7uATOm1lijNgthbqjRVJGlsWzmUNNb2ixPgGJHSqCLJE+Fn0pLRaq9"
    "qYoyJgbhi2aZF2he/mPhH/Hck3kLnDuqc3GnzC6kZfGSJyeaZ7FLiJo7+D+eHSCaVPNuHi+4JVheWCKBfXJIjdTAImzASjkfLfGXx+hlbBpFgdXar2M/8KO+8pslRPOpo1AQElpiecHf9/gsg9Px7oSsmjU0Igx2QIDAQAB"
)
CPM_EXTENSION_ID = "igjpmedeifbgmbcdodkcccekemdomphn"


def get_chromium_extension_id(ext_dir: Path | None = None) -> str:
    """Return the deterministic 32-character Extension ID assigned by Chromium."""
    return CPM_EXTENSION_ID


def get_chromium_executable_path() -> str | None:
    """Find the path to the Chromium executable on the current system."""
    custom_path = os.environ.get("CPM_CHROMIUM_PATH")
    if custom_path and Path(custom_path).is_file():
        return custom_path

    if sys.platform == "darwin":
        app_bundle_dir = Path(sys.executable).resolve().parent.parent
        candidates = [
            # 1. 优先检测当前运行客户端内部捆绑的原生 CamouChromium-155 内核
            str(app_bundle_dir / "Resources" / "kernels" / "CamouChromium-155.app" / "Contents" / "MacOS" / "Chromium"),
            str(app_bundle_dir / "Resources" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"),
            # 2. 系统 Library 支持目录下的原生内核
            str(Path.home() / "Library" / "Application Support" / "Camoufox Profile Manager" / "bin" / "kernels" / "CamouChromium-155.app" / "Contents" / "MacOS" / "Chromium"),
            str(Path.home() / ".camoufox" / "bin" / "kernels" / "CamouChromium-155.app" / "Contents" / "MacOS" / "Chromium"),
            str(Path.home() / "Library" / "Application Support" / "Camoufox Profile Manager" / "bin" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"),
            # 3. /Applications 全局安装目录下的内嵌内核
            "/Applications/CamouHub.app/Contents/Resources/kernels/CamouChromium-155.app/Contents/MacOS/Chromium",
            "/Applications/CamouHub.app/Contents/Resources/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            str(Path.home() / "Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
        for candidate in candidates:
            if Path(candidate).is_file() and os.access(candidate, os.X_OK):
                return candidate

    elif sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Chromium\Application\chrome.exe",
            r"C:\Program Files (x86)\Chromium\Application\chrome.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Chromium\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for candidate in candidates:
            if Path(candidate).is_file():
                return candidate

    else:  # Linux / Unix
        candidates = [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/snap/bin/chromium",
        ]
        for candidate in candidates:
            if Path(candidate).is_file() and os.access(candidate, os.X_OK):
                return candidate

    for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        resolved = shutil.which(name)
        if resolved:
            return resolved

    return None


def get_target_dimensions(settings: Any) -> tuple[int, int]:
    """Extract effective screen/window dimensions (width, height), prioritizing configured screen resolution."""
    if not settings:
        return 1280, 720
    screen_val = getattr(settings, "screen", None)
    if screen_val and "x" in str(screen_val).lower():
        try:
            parts = str(screen_val).lower().split("x")
            sw = int(parts[0].strip())
            sh = int(parts[1].strip())
            if sw > 0 and sh > 0:
                return sw, sh
        except Exception:
            pass
    w = getattr(settings, "window_width", None) or 1280
    h = getattr(settings, "window_height", None) or 720
    return w, h


SEARCH_CONFIGS = {
    "google": {
        "name": "Google",
        "keyword": "google.com",
        "search_url": "https://www.google.com/search?q={searchTerms}",
        "suggest_url": "https://suggestqueries.google.com/complete/search?client=chrome&q={searchTerms}",
        "favicon_url": "https://www.google.com/favicon.ico",
    },
    "bing": {
        "name": "Bing",
        "keyword": "bing.com",
        "search_url": "https://www.bing.com/search?q={searchTerms}",
        "suggest_url": "https://www.bing.com/osjson.aspx?query={searchTerms}",
        "favicon_url": "https://www.bing.com/favicon.ico",
    },
    "baidu": {
        "name": "百度",
        "keyword": "baidu.com",
        "search_url": "https://www.baidu.com/s?ie=UTF-8&wd={searchTerms}",
        "suggest_url": "https://suggestion.baidu.com/su?wd={searchTerms}&action=opensearch&ie=UTF-8",
        "favicon_url": "https://www.baidu.com/favicon.ico",
    },
    "duckduckgo": {
        "name": "DuckDuckGo",
        "keyword": "duckduckgo.com",
        "search_url": "https://duckduckgo.com/?q={searchTerms}",
        "suggest_url": "https://duckduckgo.com/ac/?q={searchTerms}&type=list",
        "favicon_url": "https://duckduckgo.com/favicon.ico",
    },
}


def normalize_languages(langs: list[str] | None) -> list[str]:
    """Normalize language list to standard Chrome format covering global locales."""
    if not langs:
        return ["en-US", "en"]
    res: list[str] = []

    # Chromium standard multi-locale pairings
    pairings: dict[str, list[str]] = {
        "ja": ["ja", "ja-JP"],
        "ko": ["ko", "ko-KR"],
        "zh-cn": ["zh-CN", "zh"],
        "zh": ["zh-CN", "zh"],
        "zh-tw": ["zh-TW", "zh"],
        "zh-hk": ["zh-HK", "zh-TW", "zh"],
        "en-us": ["en-US", "en"],
        "en": ["en-US", "en"],
        "en-gb": ["en-GB", "en"],
        "de": ["de", "de-DE"],
        "fr": ["fr", "fr-FR"],
        "es": ["es", "es-ES"],
        "es-419": ["es-419", "es"],
        "pt-br": ["pt-BR", "pt"],
        "pt-pt": ["pt-PT", "pt"],
        "pt": ["pt-BR", "pt"],
        "it": ["it", "it-IT"],
        "ru": ["ru", "ru-RU"],
        "vi": ["vi", "vi-VN"],
        "th": ["th", "th-TH"],
        "id": ["id", "id-ID"],
        "ar": ["ar", "ar-SA"],
        "tr": ["tr", "tr-TR"],
        "nl": ["nl", "nl-NL"],
        "pl": ["pl", "pl-PL"],
        "uk": ["uk", "uk-UA"],
        "el": ["el", "el-GR"],
        "cs": ["cs", "cs-CZ"],
        "sv": ["sv", "sv-SE"],
        "da": ["da", "da-DK"],
        "fi": ["fi", "fi-FI"],
        "nb": ["nb", "no"],
        "ro": ["ro", "ro-RO"],
        "hu": ["hu", "hu-HU"],
        "hi": ["hi", "hi-IN"],
        "fil": ["fil", "tl"],
        "ms": ["ms", "ms-MY"],
        "he": ["he", "iw"],
    }

    for l in langs:
        lower = l.lower().replace("_", "-")
        matched = False
        for prefix, standards in pairings.items():
            if lower == prefix or (len(prefix) == 2 and lower.startswith(f"{prefix}-")):
                for s in standards:
                    if s not in res:
                        res.append(s)
                matched = True
                break
        if not matched:
            # Fallback for any other global language code (e.g. xx-YY -> [xx, xx-YY])
            if "-" in lower:
                base, region = lower.split("-", 1)
                if base not in res:
                    res.append(base)
                reconstructed = f"{base}-{region.upper()}"
                if reconstructed not in res:
                    res.append(reconstructed)
            else:
                if l not in res:
                    res.append(l)
    return res


def normalize_languages_chain(raw_languages: list[str] | None) -> tuple[list[str], str]:
    """Normalize language list into authentic, tight chain and compute standard Accept-Language header across ALL countries."""
    if not raw_languages:
        return ["en-US", "en"], "en-US,en;q=0.9"

    cleaned: list[str] = []
    for l in raw_languages:
        l = l.strip()
        if l and l not in cleaned:
            cleaned.append(l)

    if not cleaned:
        return ["en-US", "en"], "en-US,en;q=0.9"

    primary = cleaned[0].strip()
    primary_lower = primary.lower()
    base_lang = primary_lower.split("-")[0]

    # Standard primary dialect pairings for major non-English languages
    _PAIRINGS: dict[str, list[str]] = {
        "ja": ["ja", "ja-JP"],
        "zh": ["zh-CN", "zh"],
        "ko": ["ko-KR", "ko"],
        "de": ["de-DE", "de"],
        "fr": ["fr-FR", "fr"],
        "ru": ["ru-RU", "ru"],
        "es": ["es-ES", "es"],
        "it": ["it-IT", "it"],
        "nl": ["nl-NL", "nl"],
        "pl": ["pl-PL", "pl"],
        "pt": ["pt-BR", "pt"],
        "tr": ["tr-TR", "tr"],
        "th": ["th-TH", "th"],
        "vi": ["vi-VN", "vi"],
        "id": ["id-ID", "id"],
        "ar": ["ar-SA", "ar"],
        "uk": ["uk-UA", "uk"],
        "cs": ["cs-CZ", "cs"],
        "sv": ["sv-SE", "sv"],
        "el": ["el-GR", "el"],
        "ro": ["ro-RO", "ro"],
        "hu": ["hu-HU", "hu"],
        "da": ["da-DK", "da"],
        "fi": ["fi-FI", "fi"],
        "no": ["nb-NO", "no"],
        "he": ["he-IL", "he"],
    }

    if base_lang != "en":
        # Keep ONLY dialects matching the base language, eliminate all trailing en-US/en
        filtered = [l for l in cleaned if l.lower().split("-")[0] == base_lang]
        if base_lang in _PAIRINGS:
            # Preserve user dialect if specialized (e.g. zh-TW, es-MX, pt-PT)
            if "-" in primary:
                region = primary.split("-")[1].upper()
                cleaned = [f"{base_lang}-{region}", base_lang]
            else:
                cleaned = _PAIRINGS[base_lang]
        elif len(filtered) > 1:
            cleaned = filtered
        else:
            cleaned = [f"{base_lang}-{base_lang.upper()}", base_lang] if "-" not in primary else [primary, base_lang]
    else:
        # English: en-US, en or en-GB, en
        if "en-gb" in primary_lower:
            cleaned = ["en-GB", "en-US", "en"]
        else:
            cleaned = ["en-US", "en"]

    if len(cleaned) == 1:
        accept_lang_header = cleaned[0]
    else:
        parts = [cleaned[0]]
        for idx, l in enumerate(cleaned[1:], start=1):
            q = max(0.1, round(1.0 - idx * 0.1, 1))
            parts.append(f"{l};q={q}")
        accept_lang_header = ",".join(parts)

    return cleaned, accept_lang_header


def generate_fingerprint_extension(
    extension_dir: Path,
    settings: BrowserSettings,
    proxy: ProxyConfig | None = None,
    cookies_raw: str | None = None,
    profile_id: str | None = None,
    profile_name: str | None = None,
    group_name: str | None = None,
    notes: str | None = None,
    account: str | None = None,
) -> Path:
    """Generate a dedicated unpacked Chrome extension for stealth fingerprint spoofing, proxy auth, newtab radar, and cookie loading."""
    extension_dir.mkdir(parents=True, exist_ok=True)

    target_languages, target_accept_language = normalize_languages_chain(settings.languages)

    manifest: dict[str, Any] = {
        "manifest_version": 3,
        "name": "Camoufox Anti-Detect Extension",
        "version": "1.0.0",
        "key": CPM_EXTENSION_PUBLIC_KEY,
        "description": "Stealth fingerprint protection and isolation provider",
        "permissions": ["storage", "cookies", "declarativeNetRequest", "tabs"],
        "host_permissions": ["<all_urls>"],
        "background": {"service_worker": "background.js"},
        "web_accessible_resources": [
            {
                "resources": ["cookies.json"],
                "matches": ["<all_urls>"]
            }
        ],
        "content_scripts": [
            {
                "matches": ["<all_urls>"],
                "js": ["inject.js"],
                "run_at": "document_start",
                "world": "MAIN",
                "all_frames": True,
                "match_about_blank": True,
            }
        ],
    }

    # Handle preset/imported cookies injection
    parsed_cookies = []
    if cookies_raw and cookies_raw.strip():
        c_str = cookies_raw.strip()
        if c_str.startswith("[") and c_str.endswith("]"):
            try:
                parsed_cookies = json.loads(c_str)
            except Exception:
                pass
        if not parsed_cookies:
            # Parse Netscape or name=value; format
            for line in c_str.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    parsed_cookies.append({
                        "domain": parts[0],
                        "path": parts[2],
                        "secure": parts[3].lower() == "true",
                        "expirationDate": float(parts[4]) if parts[4].isdigit() else (time.time() + 31536000),
                        "name": parts[5],
                        "value": parts[6],
                    })
                elif ";" in line or "=" in line:
                    for part in line.split(";"):
                        if "=" in part:
                            k, v = part.split("=", 1)
                            if k.strip():
                                parsed_cookies.append({"name": k.strip(), "value": v.strip(), "path": "/"})

    (extension_dir / "cookies.json").write_text(json.dumps(parsed_cookies), encoding="utf-8")

    # Build dynamic headers list for declarativeNetRequest
    req_headers = [{
        "header": "Accept-Language",
        "operation": "set",
        "value": target_accept_language
    }]
    target_os_lower = (getattr(settings, "os", None) or "").lower()
    if settings.user_agent:
        ua_tmp = settings.user_agent.lower()
        if "iphone" in ua_tmp or "ipad" in ua_tmp or "ios" in ua_tmp:
            target_os_lower = "ios"
        elif "android" in ua_tmp:
            target_os_lower = "android"
    if target_os_lower == "ios":
        for ch in [
            "sec-ch-ua",
            "sec-ch-ua-mobile",
            "sec-ch-ua-platform",
            "sec-ch-ua-platform-version",
            "sec-ch-ua-full-version-list",
            "sec-ch-ua-model",
            "sec-ch-ua-arch",
            "sec-ch-ua-bitness",
            "sec-ch-ua-full-version",
        ]:
            req_headers.append({"header": ch, "operation": "remove"})
    elif target_os_lower == "android":
        req_headers.extend([
            {"header": "sec-ch-ua-platform", "operation": "set", "value": '"Android"'},
            {"header": "sec-ch-ua-mobile", "operation": "set", "value": "?1"},
        ])
        for ch in [
            "sec-ch-ua-platform-version",
            "sec-ch-ua-model",
            "sec-ch-ua-arch",
            "sec-ch-ua-bitness",
            "sec-ch-ua-full-version",
            "sec-ch-ua-full-version-list",
        ]:
            req_headers.append({"header": ch, "operation": "remove"})

    # Generate background.js with declarativeNetRequest rules and native integrated radar tab controller
    background_js = f"""
chrome.runtime.onInstalled.addListener(async () => {{
    try {{
        // Enforce authentic HTTP headers matching profile configuration
        await chrome.declarativeNetRequest.updateDynamicRules({{
            removeRuleIds: [1001],
            addRules: [{{
                id: 1001,
                priority: 1,
                action: {{
                    type: 'modifyHeaders',
                    requestHeaders: {json.dumps(req_headers)}
                }},
                condition: {{
                    urlFilter: '|http*',
                    resourceTypes: ['main_frame', 'sub_frame', 'stylesheet', 'script', 'image', 'font', 'object', 'xmlhttprequest', 'ping', 'other']
                }}
            }}]
        }});
    }} catch(e) {{}}

    try {{
        const resp = await fetch(chrome.runtime.getURL('cookies.json'));
        if (!resp.ok) return;
        const cookies = await resp.json();
        for (const c of cookies) {{
            try {{
                let domain = (c.domain || '').replace(/^\\./, '');
                let url = c.url;
                if (!url) {{
                    url = (c.secure ? 'https://' : 'http://') + (domain || 'localhost') + (c.path || '/');
                }}
                await chrome.cookies.set({{
                    url: url,
                    name: c.name,
                    value: c.value,
                    domain: c.domain || undefined,
                    path: c.path || '/',
                    secure: Boolean(c.secure),
                    httpOnly: Boolean(c.httpOnly),
                    sameSite: c.sameSite || 'lax',
                    expirationDate: c.expirationDate || c.expiry || (Date.now() / 1000 + 86400 * 365)
                }});
            }} catch (e) {{}}
        }}
    }} catch (e) {{}}
}});
"""
    (extension_dir / "background.js").write_text(background_js.strip(), encoding="utf-8")

    # NOTE: chrome_settings_overrides search_provider is deliberately omitted here!
    # Configuring search_provider in the extension triggers Chrome's "Changed back to Google?
    # This page was changed by Camoufox Anti-Detect Extension" prompt.
    # The default search engine is already cleanly configured in Preferences/default_search_provider_data.

    # 3. Injected JS for Fingerprint Spoofing & Stealth Prototype Protection
    target_os = (getattr(settings, "os", None) or "windows").lower()
    if settings.user_agent:
        ua_l = settings.user_agent.lower()
        if "iphone" in ua_l or "ipad" in ua_l or "ios" in ua_l:
            target_os = "ios"
        elif "android" in ua_l:
            target_os = "android"
        elif "windows" in ua_l:
            target_os = "windows"
        elif "macintosh" in ua_l or "mac os x" in ua_l:
            target_os = "macos"
        elif "linux" in ua_l:
            target_os = "linux"

    full_ver = "155.0.8059.39"
    major_ver = "155"
    if settings.user_agent:
        m_crios = re.search(r"CriOS/(\d+)", settings.user_agent)
        if m_crios:
            major_ver = m_crios.group(1)
            full_ver = f"{major_ver}.0.0.0"
        m_full = re.search(r"Chrome/(\d+)\.(\d+)\.(\d+)\.(\d+)", settings.user_agent)
        if m_full:
            full_parts = [m_full.group(1), m_full.group(2), m_full.group(3), m_full.group(4)]
            major_ver = full_parts[0]
            if full_parts[1:] == ["0", "0", "0"]:
                if major_ver == "155":
                    full_ver = "155.0.8059.39"
                elif major_ver == "149":
                    full_ver = "149.0.7827.200"
                elif major_ver == "130":
                    full_ver = "130.0.6723.69"
                else:
                    full_ver = f"{major_ver}.0.7000.100"
            else:
                full_ver = ".".join(full_parts)
        else:
            m_maj = re.search(r"Chrome/(\d+)", settings.user_agent)
            if m_maj:
                major_ver = m_maj.group(1)
                if major_ver == "155":
                    full_ver = "155.0.8059.39"
                elif major_ver == "149":
                    full_ver = "149.0.7827.200"
                else:
                    full_ver = f"{major_ver}.0.7000.100"

    sw, sh = get_target_dimensions(settings)
    coords = getattr(settings, "geolocation", None) or {}

    # 移动端专用元数据提取（仅在 Android 下提取机型与版本，PC 保持空值）
    device_model = ""
    android_ver = ""
    if target_os == "android" and settings.user_agent:
        m_model = re.search(r"Android\s+[\d.]+;\s*([^;)]+)", settings.user_agent)
        if m_model:
            device_model = m_model.group(1).strip()
        m_aver = re.search(r"Android\s+([\d.]+)", settings.user_agent)
        if m_aver:
            v_val = m_aver.group(1).strip()
            android_ver = v_val if "." in v_val else f"{v_val}.0.0"

    config_json = json.dumps({
        "targetOS": target_os,
        "majorVersion": major_ver,
        "fullVersion": full_ver,
        "deviceModel": device_model,
        "androidVersion": android_ver,
        "webglVendor": settings.webgl_vendor,
        "webglRenderer": settings.webgl_renderer,
        "hardwareConcurrency": settings.hardware_concurrency,
        "deviceMemory": settings.device_memory,
        "canvasNoise": False,
        "audioNoise": False,
        "clientRectsNoise": settings.client_rects_noise,
        "batterySpoofing": settings.battery_spoofing,
        "doNotTrack": settings.do_not_track,
        "fontMasking": getattr(settings, "font_masking", True),
        "clipboardIsolation": getattr(settings, "clipboard_isolation", True),
        "timezone": getattr(settings, "timezone", None),
        "languages": target_languages,
        "latitude": coords.get("lat") if isinstance(coords, dict) else None,
        "longitude": coords.get("lon") if isinstance(coords, dict) else None,
        "screenWidth": sw,
        "screenHeight": sh,
        "maxTouchPoints": getattr(settings, "max_touch_points", 0) or (5 if target_os in ("android", "ios") else 0),
        "envTitle": profile_name or profile_id or "社交账号管理系统",
    })

    inject_js_template = '''(function() {
    'use strict';
    const cfg = __CPM_CONFIG_JSON__;

    // --- Native Function Prototype Masking (makeNative) ---
    const nativeToString = Function.prototype.toString;
    const fnToStringMap = new WeakMap();

    function makeNative(fn, name) {
        if (!fn || typeof fn !== 'function') return fn;
        const nativeStr = 'function ' + (name || fn.name || '') + '() { [native code] }';
        fnToStringMap.set(fn, nativeStr);
        try {
            Object.defineProperty(fn, 'name', { value: name || fn.name, configurable: true });
        } catch(e) {}
        return fn;
    }

    try {
        Function.prototype.toString = new Proxy(nativeToString, {
            apply(target, thisArg, args) {
                if (fnToStringMap.has(thisArg)) {
                    return fnToStringMap.get(thisArg);
                }
                return Reflect.apply(target, thisArg, args);
            }
        });
        fnToStringMap.set(Function.prototype.toString, "function toString() { [native code] }");
    } catch(e) {}

    // --- 1. Navigator Platform & Languages Alignment ---
    try {
        let plat = 'Win32';
        if (cfg.targetOS === 'macos') plat = 'MacIntel';
        else if (cfg.targetOS === 'linux') plat = 'Linux x86_64';
        else if (cfg.targetOS === 'android') plat = 'Linux armv8l';
        else if (cfg.targetOS === 'ios') plat = 'iPhone';
        Object.defineProperty(Navigator.prototype, 'platform', {
            get: makeNative(() => plat, 'get platform'),
            enumerable: true,
            configurable: true
        });

        if (cfg.maxTouchPoints !== undefined && cfg.maxTouchPoints > 0) {
            Object.defineProperty(Navigator.prototype, 'maxTouchPoints', {
                get: makeNative(() => cfg.maxTouchPoints, 'get maxTouchPoints'),
                enumerable: true,
                configurable: true
            });
        }

        if (cfg.languages && cfg.languages.length > 0) {
            const primaryLang = cfg.languages[0];
            const langsList = Object.freeze([...cfg.languages]);
            Object.defineProperty(Navigator.prototype, 'language', {
                get: makeNative(() => primaryLang, 'get language'),
                enumerable: true,
                configurable: true
            });
            Object.defineProperty(Navigator.prototype, 'languages', {
                get: makeNative(() => langsList, 'get languages'),
                enumerable: true,
                configurable: true
            });

            // Intercept Intl APIs resolvedOptions to eliminate system locale leakage (e.g. zh-CN)
            const intlClasses = ['DateTimeFormat', 'NumberFormat', 'Collator', 'PluralRules', 'RelativeTimeFormat', 'ListFormat'];
            for (let i = 0; i < intlClasses.length; i++) {
                const key = intlClasses[i];
                if (typeof Intl !== 'undefined' && Intl[key] && Intl[key].prototype && Intl[key].prototype.resolvedOptions) {
                    const origFn = Intl[key].prototype.resolvedOptions;
                    Intl[key].prototype.resolvedOptions = makeNative(function() {
                        const opts = origFn.apply(this, arguments);
                        opts.locale = primaryLang;
                        if (key === 'DateTimeFormat' && cfg.timezone) {
                            opts.timeZone = cfg.timezone;
                        }
                        return opts;
                    }, 'resolvedOptions');
                }
            }
        } else if (cfg.timezone) {
            if (typeof Intl !== 'undefined' && Intl.DateTimeFormat && Intl.DateTimeFormat.prototype.resolvedOptions) {
                const origResolved = Intl.DateTimeFormat.prototype.resolvedOptions;
                Intl.DateTimeFormat.prototype.resolvedOptions = makeNative(function() {
                    const res = origResolved.apply(this, arguments);
                    res.timeZone = cfg.timezone;
                    return res;
                }, 'resolvedOptions');
            }
        }

        // Intercept Date.prototype.toString & toTimeString to eliminate host OS language in timezone description
        if (cfg.timezone || (cfg.languages && cfg.languages.length > 0)) {
            const origDateToString = Date.prototype.toString;
            const origDateToTimeString = Date.prototype.toTimeString;

            const getTimezoneSuffix = (tz, lang) => {
                if (!tz) return '';
                if (tz.includes('Tokyo')) return (lang || '').startsWith('ja') ? '(日本標準時)' : '(Japan Standard Time)';
                if (tz.includes('Shanghai') || tz.includes('Chongqing') || tz.includes('Hong_Kong')) return '(中国标准时间)';
                if (tz.includes('Taipei')) return '(台北標準時間)';
                if (tz.includes('Seoul')) return '(한국 표준시)';
                if (tz.includes('New_York')) return '(Eastern Standard Time)';
                if (tz.includes('Chicago')) return '(Central Standard Time)';
                if (tz.includes('Los_Angeles')) return '(Pacific Standard Time)';
                if (tz.includes('London')) return '(Greenwich Mean Time)';
                if (tz.includes('Paris') || tz.includes('Berlin') || tz.includes('Rome')) return '(Central European Standard Time)';
                return '';
            };

            const primaryLang = (cfg.languages && cfg.languages[0]) || 'en-US';
            const tzSuffix = getTimezoneSuffix(cfg.timezone, primaryLang);

            if (tzSuffix) {
                Date.prototype.toString = makeNative(function() {
                    const str = origDateToString.apply(this, arguments);
                    return str.replace(/\\([^)]+\\)$/, tzSuffix);
                }, 'toString');

                Date.prototype.toTimeString = makeNative(function() {
                    const str = origDateToTimeString.apply(this, arguments);
                    return str.replace(/\\([^)]+\\)$/, tzSuffix);
                }, 'toTimeString');
            }
        }

        // --- UserAgentData Spoofing ---
        if (cfg.targetOS === 'ios') {
            // iOS (iPhone/iPad) 规范：原生 WebKit 规范中完全不存在 navigator.userAgentData 与 navigator.gpu
            try {
                Object.defineProperty(Navigator.prototype, 'userAgentData', {
                    get: () => undefined,
                    configurable: true,
                    enumerable: false
                });
                delete Navigator.prototype.userAgentData;
                delete navigator.userAgentData;
            } catch(e) {}
            try {
                window.NavigatorUAData = undefined;
                delete window.NavigatorUAData;
            } catch(e) {}

            // 彻底禁用 WebGPU (真实 iOS 目前暂不支持 navigator.gpu，消除 WebGPU 桌面硬件泄漏)
            try {
                Object.defineProperty(Navigator.prototype, 'gpu', {
                    get: () => undefined,
                    configurable: true,
                    enumerable: false
                });
                delete Navigator.prototype.gpu;
                delete navigator.gpu;
            } catch(e) {}

            // 过滤 WebGL 中的桌面 S3TC 扩展，避免被反指纹引擎断定为桌面 GPU 冒充手机
            try {
                if (typeof WebGLRenderingContext !== 'undefined') {
                    const origExts1 = WebGLRenderingContext.prototype.getSupportedExtensions;
                    WebGLRenderingContext.prototype.getSupportedExtensions = makeNative(function() {
                        const exts = origExts1.apply(this, arguments);
                        return exts ? exts.filter(e => !e.toLowerCase().includes('s3tc')) : exts;
                    }, 'getSupportedExtensions');
                }
                if (typeof WebGL2RenderingContext !== 'undefined') {
                    const origExts2 = WebGL2RenderingContext.prototype.getSupportedExtensions;
                    WebGL2RenderingContext.prototype.getSupportedExtensions = makeNative(function() {
                        const exts = origExts2.apply(this, arguments);
                        return exts ? exts.filter(e => !e.toLowerCase().includes('s3tc')) : exts;
                    }, 'getSupportedExtensions');
                }
            } catch(e) {}
        } else {
            // PC 端 (Windows / macOS / Linux) 100% 沿用原有成熟逻辑，毫厘不改；仅对 Android 移动端做标准对齐
            const isAndroid = (cfg.targetOS === 'android');
            const platName = isAndroid ? 'Android' : (cfg.targetOS === 'windows' ? 'Windows' : (cfg.targetOS === 'macos' ? 'macOS' : 'Linux'));
            const isMobile = isAndroid;
            const majV = cfg.majorVersion || '155';
            const brands = Object.freeze([
                { brand: 'Chromium', version: majV },
                { brand: 'Not(A:Brand', version: '24' },
                { brand: 'Google Chrome', version: majV }
            ]);

            let platVer = '15.0.0';
            if (cfg.targetOS === 'macos') {
                platVer = '14.5.0';
            } else if (isAndroid) {
                platVer = cfg.androidVersion || '14.0.0';
            } else if (cfg.targetOS === 'linux') {
                platVer = '6.5.0';
            }

            const modelName = isAndroid ? (cfg.deviceModel || 'SM-S918B') : '';
            const archName = isAndroid ? 'arm' : 'x86';

            if (isAndroid && typeof NavigatorUAData !== 'undefined') {
                // 针对 Android：采用原生原型级拦截，保留 navigator.userAgentData 原始原生实例
                // 确保 Object.prototype.toString.call(navigator.userAgentData) === '[object NavigatorUAData]' 永远合法，彻底消除 liedJS
                try {
                    Object.defineProperty(NavigatorUAData.prototype, 'platform', {
                        get: makeNative(() => 'Android', 'get platform'),
                        configurable: true,
                        enumerable: true
                    });
                    Object.defineProperty(NavigatorUAData.prototype, 'mobile', {
                        get: makeNative(() => true, 'get mobile'),
                        configurable: true,
                        enumerable: true
                    });
                    const origGHEV = NavigatorUAData.prototype.getHighEntropyValues;
                    NavigatorUAData.prototype.getHighEntropyValues = makeNative(function(hints) {
                        return origGHEV.apply(this, arguments).then(res => {
                            if (res) {
                                res.platform = 'Android';
                                res.mobile = true;
                                res.platformVersion = platVer;
                                res.model = modelName;
                                res.architecture = 'arm';
                                res.bitness = '64';
                            }
                            return res;
                        });
                    }, 'getHighEntropyValues');
                } catch(e) {}
            } else {
                // PC 端 (Windows / macOS / Linux) 100% 沿用原有成熟逻辑，毫厘不改
                const uad = {
                    brands: brands,
                    mobile: isMobile,
                    platform: platName,
                    getHighEntropyValues: makeNative(function(hints) {
                        return Promise.resolve({
                            brands: brands,
                            mobile: isMobile,
                            platform: platName,
                            platformVersion: platVer,
                            architecture: archName,
                            bitness: '64',
                            model: modelName,
                            uaFullVersion: cfg.fullVersion || (majV + '.0.0.0'),
                            fullVersionList: brands.map(b => ({ brand: b.brand, version: b.brand.includes('Not') ? '24.0.0.0' : (cfg.fullVersion || (majV + '.0.0.0')) }))
                        });
                    }, 'getHighEntropyValues'),
                    toJSON: makeNative(function() {
                        return { brands: brands, mobile: isMobile, platform: platName };
                    }, 'toJSON')
                };
                if (typeof NavigatorUAData !== 'undefined') {
                    Object.setPrototypeOf(uad, NavigatorUAData.prototype);
                }
                Object.defineProperty(Navigator.prototype, 'userAgentData', {
                    get: makeNative(() => uad, 'get userAgentData'),
                    enumerable: true,
                    configurable: true
                });
            }
        }
    } catch(e) {}

    // --- 2. WebGL Vendor, Renderer & Precision Spoofing ---
    if ((cfg.webglVendor || cfg.webglRenderer) && typeof WebGLRenderingContext !== 'undefined') {
        const getParameterOriginals = [
            WebGLRenderingContext.prototype.getParameter,
            typeof WebGL2RenderingContext !== 'undefined' ? WebGL2RenderingContext.prototype.getParameter : null
        ];

        const overrideGetParameter = function(original, isWebGL2) {
            if (!original) return null;
            return makeNative(function(param) {
                const realRes = original.apply(this, arguments);
                if (param === 0x9245 && cfg.webglVendor) return cfg.webglVendor;
                if (param === 0x9246 && cfg.webglRenderer) return cfg.webglRenderer;
                if (param === 0x1F00 && cfg.webglVendor) return 'WebKit';
                if (param === 0x1F01 && cfg.webglRenderer) return 'WebKit WebGL';
                if (param === 0x1F02) {
                    if (cfg.targetOS === 'ios') return isWebGL2 ? 'WebGL 2.0' : 'WebGL 1.0';
                    return isWebGL2 ? 'WebGL 2.0 (OpenGL ES 3.0 Chromium)' : 'WebGL 1.0 (OpenGL ES 2.0 Chromium)';
                }
                if (param === 0x8B8C) {
                    if (cfg.targetOS === 'ios') return isWebGL2 ? 'WebGL GLSL ES 3.00' : 'WebGL GLSL ES 1.0';
                    return isWebGL2 ? 'WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)' : 'WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)';
                }
                return realRes;
            }, 'getParameter');
        };

        WebGLRenderingContext.prototype.getParameter = overrideGetParameter(getParameterOriginals[0], false);
        if (typeof WebGL2RenderingContext !== 'undefined' && getParameterOriginals[1]) {
            WebGL2RenderingContext.prototype.getParameter = overrideGetParameter(getParameterOriginals[1], true);
        }

        const overrideShaderPrecision = function(original) {
            if (!original) return null;
            return makeNative(function(shaderType, precisionType) {
                const res = original.apply(this, arguments);
                if (cfg.targetOS === 'windows' && res) {
                    try {
                        const Proto = (typeof WebGLShaderPrecisionFormat !== 'undefined')
                            ? WebGLShaderPrecisionFormat.prototype
                            : Object.getPrototypeOf(res);
                        const spoofed = Object.create(Proto);
                        Object.defineProperties(spoofed, {
                            rangeMin: { value: 127, enumerable: true },
                            rangeMax: { value: 127, enumerable: true },
                            precision: { value: 23, enumerable: true }
                        });
                        return spoofed;
                    } catch(e) {
                        return res;
                    }
                }
                return res;
            }, 'getShaderPrecisionFormat');
        };
        WebGLRenderingContext.prototype.getShaderPrecisionFormat = overrideShaderPrecision(WebGLRenderingContext.prototype.getShaderPrecisionFormat);
        if (typeof WebGL2RenderingContext !== 'undefined') {
            WebGL2RenderingContext.prototype.getShaderPrecisionFormat = overrideShaderPrecision(WebGL2RenderingContext.prototype.getShaderPrecisionFormat);
        }

        try {
            if (typeof HTMLIFrameElement !== 'undefined') {
                const origContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow').get;
                Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                    get: makeNative(function() {
                        const win = origContentWindow.apply(this, arguments);
                        if (win && !win.__cpm_injected) {
                            win.__cpm_injected = true;
                            try {
                                if (win.WebGLRenderingContext) {
                                    win.WebGLRenderingContext.prototype.getParameter = WebGLRenderingContext.prototype.getParameter;
                                    win.WebGLRenderingContext.prototype.getShaderPrecisionFormat = WebGLRenderingContext.prototype.getShaderPrecisionFormat;
                                }
                                if (win.WebGL2RenderingContext) {
                                    win.WebGL2RenderingContext.prototype.getParameter = WebGL2RenderingContext.prototype.getParameter;
                                    win.WebGL2RenderingContext.prototype.getShaderPrecisionFormat = WebGL2RenderingContext.prototype.getShaderPrecisionFormat;
                                }
                            } catch(e) {}
                        }
                        return win;
                    }, 'get contentWindow'),
                    configurable: true,
                    enumerable: true
                });
            }
        } catch(e) {}
    }

    // --- 2.2 WebGPU Adapter Spoofing ---
    try {
        if (cfg.targetOS === 'windows') {
            const mockInfo = {
                vendor: 'intel',
                architecture: 'gen-9',
                device: '0x9b21',
                description: 'Intel(R) UHD Graphics (0x00009B21)',
                driver: ''
            };
            if (typeof GPUAdapterInfo !== 'undefined') {
                for (const [k, v] of Object.entries(mockInfo)) {
                    try {
                        Object.defineProperty(GPUAdapterInfo.prototype, k, {
                            get: makeNative(() => v, 'get ' + k),
                            configurable: true,
                            enumerable: true
                        });
                    } catch(e) {}
                }
            }
        }
    } catch(e) {}

    // --- 3. Hardware Concurrency & Memory ---
    if (cfg.hardwareConcurrency) {
        try {
            Object.defineProperty(Navigator.prototype, 'hardwareConcurrency', {
                get: makeNative(() => cfg.hardwareConcurrency, 'get hardwareConcurrency'),
                enumerable: true,
                configurable: true
            });
        } catch(e) {}
    }
    if (cfg.deviceMemory) {
        try {
            Object.defineProperty(Navigator.prototype, 'deviceMemory', {
                get: makeNative(() => cfg.deviceMemory, 'get deviceMemory'),
                enumerable: true,
                configurable: true
            });
        } catch(e) {}
    }

    // --- 4. Battery API Spoofing ---
    if (cfg.batterySpoofing && navigator.getBattery) {
        navigator.getBattery = makeNative(() => Promise.resolve({
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: 1.0,
            addEventListener: makeNative(() => {}, 'addEventListener'),
            removeEventListener: makeNative(() => {}, 'removeEventListener')
        }), 'getBattery');
    }

    // --- 5. Hardware Font Fingerprint Masking & Isolation ---
    if (cfg.fontMasking && cfg.targetOS === 'windows') {
        const MAC_ONLY_FONTS = [
            'applegothic', 'apple color emoji', 'apple sd gothic neo', 'apple chancery', 'apple braille',
            'apple symbols', 'menlo', 'monaco', 'geneva', 'pingfang sc', 'pingfang tc', 'pingfang hk',
            'hiragino sans', 'hiragino kaku gothic pron', 'hiragino mincho pron', 'sf pro', 'sf mono',
            'sf compact', 'helvetica neue', 'baskerville', 'optima', 'gill sans', 'didot',
            'american typewriter', 'marker felt', 'chalkboard', 'zapfino', 'thonburi', 'avenir',
            'avenir next', 'al nile', 'big caslon', 'copperplate', 'cochin', 'iowan old style'
        ];

        if (document.fonts && document.fonts.check) {
            const origFontsCheck = document.fonts.check;
            document.fonts.check = makeNative(function(font) {
                if (typeof font === 'string') {
                    const fLower = font.toLowerCase();
                    for (let i = 0; i < MAC_ONLY_FONTS.length; i++) {
                        if (fLower.includes(MAC_ONLY_FONTS[i])) return false;
                    }
                }
                return origFontsCheck.apply(this, arguments);
            }, 'check');
        }

        if (typeof FontFaceSet !== 'undefined' && FontFaceSet.prototype.check) {
            const origSetCheck = FontFaceSet.prototype.check;
            FontFaceSet.prototype.check = makeNative(function(font) {
                if (typeof font === 'string') {
                    const fLower = font.toLowerCase();
                    for (let i = 0; i < MAC_ONLY_FONTS.length; i++) {
                        if (fLower.includes(MAC_ONLY_FONTS[i])) return false;
                    }
                }
                return origSetCheck.apply(this, arguments);
            }, 'check');
        }

        const origMeasureText = CanvasRenderingContext2D.prototype.measureText;
        CanvasRenderingContext2D.prototype.measureText = makeNative(function(text) {
            if (this.font) {
                const fontLower = this.font.toLowerCase();
                for (let i = 0; i < MAC_ONLY_FONTS.length; i++) {
                    const bf = MAC_ONLY_FONTS[i];
                    if (fontLower.includes(bf)) {
                        const prevFont = this.font;
                        this.font = prevFont.replace(new RegExp("['\\\"]?" + bf + "['\\\"]?", 'gi'), 'sans-serif');
                        const metrics = origMeasureText.apply(this, arguments);
                        this.font = prevFont;
                        return metrics;
                    }
                }
            }
            return origMeasureText.apply(this, arguments);
        }, 'measureText');

        if (typeof window.queryLocalFonts === 'function') {
            const origQuery = window.queryLocalFonts;
            window.queryLocalFonts = makeNative(async function() {
                try {
                    const list = await origQuery.apply(this, arguments);
                    return list.filter(f => !MAC_ONLY_FONTS.some(b => (f.family || '').toLowerCase().includes(b)));
                } catch(e) {
                    return [];
                }
            }, 'queryLocalFonts');
        }
    }

    // --- 6. Anti-Automation Cleanup & Native Chrome Object ---
    try {
        Object.defineProperty(Navigator.prototype, 'webdriver', {
            get: makeNative(() => undefined, 'get webdriver'),
            enumerable: true,
            configurable: true
        });
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_;
        if (!window.chrome) window.chrome = {};
        if (!window.chrome.app) {
            window.chrome.app = {
                isInstalled: false,
                InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
                RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
                getIsInstalled: makeNative(() => false, 'getIsInstalled'),
                getDetails: makeNative(() => null, 'getDetails'),
                getInstallState: makeNative(() => 'not_installed', 'getInstallState')
            };
        }
    } catch(e) {}

    // --- 7. Real Physical Screen & Viewport Resolution Sandbox (HubStudio Spec) ---
    if (cfg.screenWidth && cfg.screenHeight) {
        const sw = Number(cfg.screenWidth);
        const sh = Number(cfg.screenHeight);
        try {
            Object.defineProperty(Screen.prototype, 'width', { get: makeNative(() => sw, 'get width'), configurable: true });
            Object.defineProperty(Screen.prototype, 'height', { get: makeNative(() => sh, 'get height'), configurable: true });
            Object.defineProperty(Screen.prototype, 'availWidth', { get: makeNative(() => sw, 'get availWidth'), configurable: true });
            Object.defineProperty(Screen.prototype, 'availHeight', { get: makeNative(() => Math.max(sh - 40, 200), 'get availHeight'), configurable: true });
            Object.defineProperty(Screen.prototype, 'colorDepth', { get: makeNative(() => 24, 'get colorDepth'), configurable: true });
            Object.defineProperty(Screen.prototype, 'pixelDepth', { get: makeNative(() => 24, 'get pixelDepth'), configurable: true });

            // Ensure window dimensions do not leak host monitor resolution (AdsPower style)
            if (window.outerWidth > sw) {
                Object.defineProperty(window, 'outerWidth', { get: makeNative(() => sw, 'get outerWidth'), configurable: true });
            }
            if (window.outerHeight > sh) {
                Object.defineProperty(window, 'outerHeight', { get: makeNative(() => sh, 'get outerHeight'), configurable: true });
            }
            if (window.innerWidth > sw) {
                Object.defineProperty(window, 'innerWidth', { get: makeNative(() => sw, 'get innerWidth'), configurable: true });
            }
            const expectedInnerH = Math.max(sh - 75, 200);
            if (window.innerHeight > expectedInnerH) {
                Object.defineProperty(window, 'innerHeight', { get: makeNative(() => expectedInnerH, 'get innerHeight'), configurable: true });
            }
        } catch(e) {}
    }
})();'''
    inject_script = inject_js_template.replace("__CPM_CONFIG_JSON__", config_json)

    (extension_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (extension_dir / "inject.js").write_text(inject_script, encoding="utf-8")

    return extension_dir


def build_chromium_args(
    storage_path: Path,
    extension_dir: Path | None,
    settings: BrowserSettings,
    proxy: ProxyConfig | None = None,
    cdp_port: int | None = None,
    extra_extensions: list[str] | None = None,
    profile_id: str | None = None,
    kernel_version: str | None = None,
) -> list[str]:
    """Construct full command-line arguments for launching Chromium."""
    args = [
        f"--user-data-dir={storage_path}",
        "--no-first-run",
        "--no-default-browser-check",
        "--hide-crash-restore-bubble",
        "--disable-sync",
        "--password-store=basic",
        "--use-mock-keychain",
        "--test-type",
    ]

    t_os = (getattr(settings, "os", None) or "").lower()
    disabled_features = ["Translate", "OptimizationHints", "MediaRouter"]
    if t_os == "ios":
        disabled_features.append("UserAgentClientHint")
    args.append(f"--disable-features={','.join(disabled_features)}")

    # Custom or spoofed User-Agent
    if settings.user_agent:
        args.append(f"--user-agent={settings.user_agent}")

    # Window geometry
    width, height = get_target_dimensions(settings)
    args.append(f"--window-size={width},{height}")
    args.append("--window-position=50,50")

    # Touch support for mobile environments (Android / iOS)
    t_os = (getattr(settings, "os", None) or "").lower()
    if t_os in ("android", "ios") or (getattr(settings, "max_touch_points", 0) and settings.max_touch_points > 0):
        args.append("--touch-events=enabled")
        args.append("--enable-touch-drag-drop")

    # Device Pixel Ratio
    if settings.device_pixel_ratio and settings.device_pixel_ratio != 1.0:
        args.append(f"--force-device-scale-factor={settings.device_pixel_ratio}")

    # Languages
    if settings.languages:
        def to_chrome_locale(lang: str) -> str:
            lower = lang.lower().replace("_", "-")
            if lower in ("zh-cn", "zh"):
                return "zh-CN"
            if lower in ("zh-tw", "zh-hk"):
                return "zh-TW"
            if lower == "pt-br":
                return "pt-BR"
            if lower == "pt-pt":
                return "pt-PT"
            if lower == "es-419":
                return "es-419"
            if lower == "en-gb":
                return "en-GB"
            if lower in ("en-us", "en"):
                return "en-US"
            if "-" in lower:
                return lower.split("-")[0]
            return lower

        chrome_locale = to_chrome_locale(settings.languages[0])
        args.append(f"--lang={chrome_locale}")
        args.append(f"--locale={chrome_locale}")

        # Chromium --accept-lang expects clean comma-separated language tags (e.g. ja,ja-JP)
        # Net/HttpUtil automatically computes the HTTP q-values from this list.
        args.append(f"--accept-lang={','.join(settings.languages)}")

        # Chromium command-line accepts --lang and --locale; AppleLanguages is already passed via environment
        pass

    # Secure DNS (DoH)
    doh_map = {
        "cloudflare": "https://cloudflare-dns.com/dns-query",
        "google": "https://dns.google/dns-query",
        "alidns": "https://dns.alidns.com/dns-query",
    }
    if settings.doh_provider in doh_map:
        args.append(f"--dns-over-https-templates={doh_map[settings.doh_provider]}")
        args.append("--dns-over-https-mode=secure")

    # WebRTC Protection
    if settings.webrtc_mode == WebRTCMode.NONE:
        args.append("--disable-webrtc")
    else:
        args.append("--webrtc-ip-handling-policy=disable_non_proxied_udp")
        args.append("--enforce-webrtc-ip-permission-check")

    # Proxy Configuration
    if proxy and proxy.server:
        server_str = proxy.server
        protocol = proxy.type.value if hasattr(proxy.type, "value") else str(proxy.type)
        if "://" not in server_str:
            server_str = f"{protocol}://{server_str}"
        args.append(f"--proxy-server={server_str}")

    # Load anti-detect extension and user extensions
    ext_list: list[str] = []
    if extension_dir and extension_dir.is_dir():
        ext_list.append(str(extension_dir))
    if extra_extensions:
        from camoufox_pm.config import get_settings
        ext_base = Path(get_settings().db_path).resolve().parent / "extensions"
        for item in extra_extensions:
            p = Path(item)
            if not p.is_dir():
                p = ext_base / item
            if p.is_dir() and (p / "manifest.json").exists():
                ext_list.append(str(p.resolve()))

    if ext_list:
        combined = ",".join(ext_list)
        args.append(f"--load-extension={combined}")
        args.append(f"--disable-extensions-except={combined}")

    # Automation Remote Debugging & Window Target Monitoring (CDP)
    port_to_use = cdp_port or settings.remote_debugging_port
    if port_to_use:
        args.append(f"--remote-debugging-port={port_to_use}")
        args.append("--remote-allow-origins=*")

    # Custom CLI switches
    if settings.custom_args:
        args.extend(settings.custom_args)

    # Disable Chrome's nagging "Changed back to Google / Extension changed this page" dialogs
    args.append("--disable-features=ExtensionSettingsOverriddenDialog,ExtensionNewTabPageBubble,SearchEngineUnconditionalDialog")

    # CloakBrowser / History Kernel (< 155) adaptation
    is_cloak = False
    if kernel_version:
        m = re.search(r"(\d+)", str(kernel_version))
        if m and int(m.group(1)) < 155:
            is_cloak = True
    elif getattr(settings, "user_agent", None):
        m = re.search(r"Chrome/(\d+)", str(settings.user_agent))
        if m and int(m.group(1)) < 155:
            is_cloak = True

    if is_cloak and profile_id:
        seed_file = storage_path / ".cloakbrowser-seed"
        if seed_file.exists():
            seed = seed_file.read_text(encoding="utf-8").strip()
        else:
            import zlib
            seed = str(abs(zlib.crc32(profile_id.encode("utf-8"))) % 2147483647 or 123456)
            try:
                seed_file.write_text(seed, encoding="utf-8")
            except Exception:
                pass
        args.append(f"--fingerprint={seed}")
        if sys.platform == "darwin":
            args.append("--fingerprint-platform=macos")

        # WebRTC altered IP injection if proxy server IP is known
        if proxy and proxy.server:
            raw_s = proxy.server.split(":")[0].replace("http://", "").replace("https://", "").replace("socks5://", "").strip()
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", raw_s):
                args.append(f"--fingerprint-webrtc-ip={raw_s}")

    # Startup URL handling:
    startup_url = getattr(settings, "startup_url", None)
    if startup_url and startup_url.strip():
        args.append(startup_url.strip())
    elif is_cloak and profile_id:
        # For < 155 Cloak history kernel, direct directly to commercial radar page
        from camoufox_pm.config import get_settings
        api_port = get_settings().port or 8000
        args.append(f"http://127.0.0.1:{api_port}/api/v1/radar?profile_id={profile_id}")

    # Strictly filter out automation and unsafe swiftshader flags
    clean_args = []
    for a in args:
        if any(flag in a for flag in ("--enable-automation", "--enable-unsafe-swiftshader")):
            continue
        clean_args.append(a)

    return clean_args


def calc_chromium_extension_id(ext_dir: Path | None = None) -> str:
    """Return the deterministic 32-character extension ID for Camoufox Anti-Detect Extension."""
    return CPM_EXTENSION_ID


def configure_search_engine(
    user_data_dir: Path,
    engine_name: str = "google",
    settings: BrowserSettings | None = None,
    ext_dir: Path | None = None,
) -> None:
    """Preconfigure or update the default search engine in Chromium's Web Data and Preferences.

    This replaces ungoogled-chromium's 'No Search' with a real search provider (Google, Bing, Baidu, DuckDuckGo)
    so omnibox search queries work out of the box instead of treating search queries as hostnames.
    """
    import sqlite3

    SEARCH_ENGINES = {
        "google": {
            "name": "Google",
            "keyword": "google.com",
            "favicon": "https://www.google.com/favicon.ico",
            "url": "https://www.google.com/search?q={searchTerms}",
            "suggest": "https://suggestqueries.google.com/complete/search?client=chrome&q={searchTerms}",
        },
        "bing": {
            "name": "Microsoft Bing",
            "keyword": "bing.com",
            "favicon": "https://www.bing.com/favicon.ico",
            "url": "https://www.bing.com/search?q={searchTerms}",
            "suggest": "https://www.bing.com/osjson.aspx?query={searchTerms}&language={language}",
        },
        "baidu": {
            "name": "百度",
            "keyword": "baidu.com",
            "favicon": "https://www.baidu.com/favicon.ico",
            "url": "https://www.baidu.com/s?ie=UTF-8&wd={searchTerms}",
            "suggest": "https://suggestion.baidu.com/su?wd={searchTerms}&action=opensearch&ie=UTF-8",
        },
        "duckduckgo": {
            "name": "DuckDuckGo",
            "keyword": "duckduckgo.com",
            "favicon": "https://duckduckgo.com/favicon.ico",
            "url": "https://duckduckgo.com/?q={searchTerms}",
            "suggest": "https://duckduckgo.com/ac/?q={searchTerms}&type=list",
        },
    }

    engine_key = engine_name.lower() if engine_name else "google"
    target_engine = SEARCH_ENGINES.get(engine_key, SEARCH_ENGINES["google"])

    default_dir = user_data_dir / "Default"
    default_dir.mkdir(parents=True, exist_ok=True)

    # 1. Clean legacy or corrupted Web Data to avoid schema version conflict with Chromium 155
    db_path = default_dir / "Web Data"
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT value FROM meta WHERE key = 'version'")
            row = cur.fetchone()
            conn.close()
            # If version is less than 156 (e.g. 154), delete it to allow Chromium 155 to initialize cleanly
            if row and int(row[0]) < 156:
                logger.info(f"Purging legacy Web Data (version {row[0]}) for clean Chromium 155 initialization")
                for f in default_dir.glob("Web Data*"):
                    try:
                        f.unlink()
                    except Exception:
                        pass
        except Exception:
            # If database cannot be opened or queried, clean it
            for f in default_dir.glob("Web Data*"):
                try:
                    f.unlink()
                except Exception:
                    pass

    # 2. Update Default/Preferences
    pref_path = default_dir / "Preferences"
    try:
        prefs_data = {}
        if pref_path.exists():
            try:
                prefs_data = json.loads(pref_path.read_text(encoding="utf-8"))
            except Exception:
                prefs_data = {}

        prefs_data["default_search_provider_data"] = {
            "template_url_data": {
                "short_name": target_engine["name"],
                "keyword": target_engine["keyword"],
                "url": target_engine["url"],
                "suggestions_url": target_engine["suggest"],
                "favicon_url": target_engine["favicon"],
                "safe_for_autoreplace": True,
                "is_active": 1,
                "date_created": "13300000000000000",
                "last_modified": "13300000000000000",
                "synced_guid": "485bf7d3-0215-45af-87dc-538868000001",
                "prepopulate_id": 1,
            }
        }

        profile_prefs = prefs_data.setdefault("profile", {})
        profile_prefs["exit_type"] = "Normal"
        profile_prefs["exited_cleanly"] = True

        session_prefs = prefs_data.setdefault("session", {})
        session_prefs["restore_on_startup"] = 5

        # Purge historical session files so old blocked tabs never restore
        sessions_dir = default_dir / "Sessions"
        if sessions_dir.exists():
            for sf in sessions_dir.glob("*"):
                try:
                    sf.unlink()
                except Exception:
                    pass

        # Strictly enforce non-maximized window placement matching configured profile resolution
        win_w, win_h = get_target_dimensions(settings)
        browser_prefs = prefs_data.setdefault("browser", {})
        win_place = browser_prefs.setdefault("window_placement", {})
        win_place["maximized"] = False
        win_place["top"] = 50
        win_place["left"] = 50
        win_place["bottom"] = 50 + win_h
        win_place["right"] = 50 + win_w

        if settings and getattr(settings, "languages", None):
            intl_prefs = prefs_data.setdefault("intl", {})
            lang_str = ",".join(settings.languages)
            intl_prefs["accept_languages"] = lang_str
            intl_prefs["selected_languages"] = lang_str

        exts_pref = prefs_data.get("extensions")
        if isinstance(exts_pref, dict):
            exts_pref.pop("chrome_url_overrides", None)
        prefs_data.pop("ack_existing_ntp_extensions", None)

        pref_path.write_text(json.dumps(prefs_data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning(f"Could not configure search engine in Preferences: {exc}")

    # 3. Update Local State for app_locale
    if settings and getattr(settings, "languages", None) and len(settings.languages) > 0:
        local_state_path = user_data_dir / "Local State"
        try:
            ls_data = {}
            if local_state_path.exists():
                try:
                    ls_data = json.loads(local_state_path.read_text(encoding="utf-8"))
                except Exception:
                    ls_data = {}
            primary = settings.languages[0].lower().replace("_", "-")
            if primary in ("zh-cn", "zh"):
                app_loc = "zh-CN"
            elif primary in ("zh-tw", "zh-hk"):
                app_loc = "zh-TW"
            elif primary == "pt-br":
                app_loc = "pt-BR"
            elif primary == "pt-pt":
                app_loc = "pt-PT"
            elif primary == "es-419":
                app_loc = "es-419"
            elif primary == "en-gb":
                app_loc = "en-GB"
            elif primary in ("en-us", "en"):
                app_loc = "en-US"
            elif "-" in primary:
                app_loc = primary.split("-")[0]
            else:
                app_loc = primary
            ls_intl = ls_data.setdefault("intl", {})
            ls_intl["app_locale"] = app_loc
            ls_intl["accept_languages"] = ",".join(settings.languages)
            ls_intl["selected_languages"] = ",".join(settings.languages)
            local_state_path.write_text(json.dumps(ls_data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Could not configure app_locale in Local State: {exc}")


async def launch_chromium_process(
    profile_id: str,
    launch_options: dict[str, Any],
) -> tuple[asyncio.subprocess.Process, int, int]:
    bs_dict = launch_options.get("browser_settings", {})
    settings = BrowserSettings(**bs_dict) if isinstance(bs_dict, dict) else bs_dict

    # Multi-kernel version routing: support new and old version invocations
    target_kver = launch_options.get("kernel_version")
    if not target_kver and getattr(settings, "user_agent", None):
        m = re.search(r"Chrome/(\d+)", settings.user_agent)
        if m:
            target_kver = m.group(1)

    from camoufox_pm.core.kernel_manager import kernel_manager
    executable = kernel_manager.get_executable_for_version(target_kver) or get_chromium_executable_path()
    if not executable:
        raise RuntimeError(
            "Chromium executable not found. Please verify /Applications/Chromium.app "
            "or set CPM_CHROMIUM_PATH environment variable."
        )

    user_data_dir = Path(launch_options["user_data_dir"])
    user_data_dir.mkdir(parents=True, exist_ok=True)

    proxy_dict = launch_options.get("proxy")
    proxy = ProxyConfig(**proxy_dict) if proxy_dict else None

    # 0. 如果环境未显式配置时区或属于默认英文，根据代理出口 IP 智能对齐目标国家时区与语言
    if proxy and proxy.server:
        raw_server = proxy.server.split(":")[0].replace("http://", "").replace("https://", "").replace("socks5://", "").strip()
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", raw_server):
            try:
                from camoufox.geolocation import get_geolocation
                geo = get_geolocation(raw_server)
                if geo:
                    if not getattr(settings, "timezone", None) and geo.timezone:
                        settings.timezone = geo.timezone
                        logger.info(f"Auto-aligned profile timezone to proxy geo: {settings.timezone}")
                    if geo.locale and geo.locale.language and geo.locale.language != "en":
                        current_langs = getattr(settings, "languages", None) or []
                        if not current_langs or current_langs == ["en-US", "en"] or current_langs == ["en"]:
                            from camoufox_pm.core.geo_utils import get_languages_for_country
                            auto_langs = get_languages_for_country(geo.locale.region or geo.locale.language)
                            settings.languages = auto_langs
                            logger.info(f"Auto-aligned profile languages to proxy geo: {settings.languages}")
            except Exception as e:
                logger.debug(f"GeoIP alignment skipped: {e}")

    # 1. 规范化语言列表（例如 ja 转换为标准的 ['ja', 'ja-JP']，彻底剔除导致 BrowserScan 标红的多余 en-US）
    if getattr(settings, "languages", None):
        cleaned_langs, _ = normalize_languages_chain(settings.languages)
        settings.languages = cleaned_langs

    # 2. 自动校正 User-Agent 遵循 Chrome 107+ UA Reduction 规范（必须为 Chrome/<major>.0.0.0）
    current_ua = getattr(settings, "user_agent", "")
    if current_ua:
        if "CamouChromium-155" in executable:
            settings.user_agent = re.sub(r"Chrome/\d+(\.\d+)+", "Chrome/155.0.0.0", current_ua)
        else:
            settings.user_agent = re.sub(r"Chrome/(\d+)(\.\d+)+", r"Chrome/\1.0.0.0", current_ua)
        logger.info(f"Aligned profile User-Agent to match standard Reduction format: {settings.user_agent}")

    # 3. 自动对齐操作系统与 UA，严禁 UA 为 Windows 时残留宿主机 macOS
    # 3. 自动对齐操作系统与 UA，精准识别桌面端与移动端
    target_os = getattr(settings, "os", "").lower()
    if current_ua:
        if "Android" in current_ua:
            target_os = "android"
            settings.os = "android"
        elif "iPhone" in current_ua or "iPad" in current_ua or "iOS" in current_ua:
            target_os = "ios"
            settings.os = "ios"
        elif "Windows NT" in current_ua:
            target_os = "windows"
            settings.os = "windows"
        elif "Macintosh" in current_ua:
            target_os = "macos"
            settings.os = "macos"
        elif "Linux" in current_ua:
            target_os = "linux"
            settings.os = "linux"
    if not target_os:
        target_os = "windows" if "Windows NT" in current_ua else ("macos" if "Macintosh" in current_ua else "linux")

    # 4. 自动对齐 WebGL 与操作系统：PC 逻辑完全保持原样；移动端对齐 Qualcomm Adreno / Apple GPU
    if target_os == "windows":
        wv = getattr(settings, "webgl_vendor", "") or ""
        wr = getattr(settings, "webgl_renderer", "") or ""
        if not wv or any(k in wv.lower() for k in ("apple", "nvidia")):
            settings.webgl_vendor = "Google Inc. (Intel)"
        if not wr or any(k in wr.lower() for k in ("apple", "metal", "m1", "m2", "m3", "m4", "geforce", "nvidia")) or "0x0000" not in wr:
            settings.webgl_renderer = "ANGLE (Intel, Intel(R) UHD Graphics (0x00009B21) Direct3D11 vs_5_0 ps_5_0, D3D11)"
    elif target_os == "macos":
        wv = getattr(settings, "webgl_vendor", "") or ""
        wr = getattr(settings, "webgl_renderer", "") or ""
        if not wv:
            settings.webgl_vendor = "Google Inc. (Apple)"
        if not wr:
            settings.webgl_renderer = "ANGLE (Apple, ANGLE Metal Renderer: Apple M4, Unspecified Version)"
    elif target_os == "android":
        wv = getattr(settings, "webgl_vendor", "") or ""
        wr = getattr(settings, "webgl_renderer", "") or ""
        if not wv or any(k in wv.lower() for k in ("apple", "intel")):
            settings.webgl_vendor = "Qualcomm"
        if not wr or any(k in wr.lower() for k in ("apple", "metal", "intel", "direct3d")):
            settings.webgl_renderer = "Adreno (TM) 740"
    elif target_os == "ios":
        settings.webgl_vendor = "Apple Inc."
        settings.webgl_renderer = "Apple GPU"

    # Always ensure a CDP port for target monitoring & auto window-close detection
    cdp_port = settings.remote_debugging_port or find_free_port()

    # Generate isolated extension inside profile directory
    ext_dir = user_data_dir / "cpm_anti_detect_extension"
    cookies_raw = launch_options.get("cookies")
    generate_fingerprint_extension(
        ext_dir,
        settings,
        proxy,
        cookies_raw=cookies_raw,
        profile_id=profile_id,
        profile_name=launch_options.get("profile_name"),
        group_name=launch_options.get("group_name"),
        notes=launch_options.get("notes"),
        account=launch_options.get("account"),
    )

    # Preconfigure search engine, language preferences, and native newtab override
    configure_search_engine(
        user_data_dir,
        getattr(settings, "search_engine", "google"),
        settings=settings,
        ext_dir=ext_dir,
    )

    extra_exts = launch_options.get("extensions", [])
    cmd_args = build_chromium_args(
        user_data_dir,
        ext_dir,
        settings,
        proxy,
        cdp_port=cdp_port,
        extra_extensions=extra_exts,
        profile_id=profile_id,
        kernel_version=target_kver,
    )
    cmd = [executable, *cmd_args]

    logger.info(f"Spawning Chromium for profile {profile_id}: {executable} with cdp_port={cdp_port}")
    spawn_env = os.environ.copy()
    if getattr(settings, "timezone", None):
        spawn_env["TZ"] = settings.timezone

    if getattr(settings, "languages", None) and len(settings.languages) > 0:
        primary_lang = settings.languages[0]
        posix_locale = primary_lang.replace("-", "_")
        spawn_env["LANG"] = f"{posix_locale}.UTF-8"
        spawn_env["LANGUAGE"] = ":".join(settings.languages)
        spawn_env["LC_ALL"] = f"{posix_locale}.UTF-8"
        if sys.platform == "darwin":
            # 彻底阻断 macOS 系统语言与区域穿透到 Helper 渲染进程，彻底消除 Language mismatch
            apple_langs_list = '", "'.join(settings.languages)
            spawn_env["AppleLanguages"] = f'("{apple_langs_list}")'
            spawn_env["AppleLocale"] = posix_locale

    # 物理窗口边界原生硬核控制（AdsPower / Anti-detect 模式）
    # 移动端：严格死锁 (STRICT_LOCK, 尺寸固定且不可缩放全屏)
    # 桌面端：上限封顶 (CAP_MAX_SIZE, 允许调小但绝对不能突破设定的屏幕分辨率，防止 outerWidth > screen.width 暴露)
    target_w, target_h = get_target_dimensions(settings)
    target_os = (getattr(settings, "os", None) or "").lower()
    is_mobile_profile = target_os in ("android", "ios") or (target_w < 800 or target_h > target_w)
    lock_mode = "STRICT_LOCK" if is_mobile_profile else "CAP_MAX_SIZE"

    if sys.platform == "darwin" and target_w > 0 and target_h > 0:
        app_bundle_dir = Path(sys.executable).resolve().parent.parent
        candidates = [
            app_bundle_dir / "Resources" / "libcamou_window_lock.dylib",
            Path("/Applications/CamouHub.app/Contents/Resources/libcamou_window_lock.dylib"),
            Path(__file__).resolve().parent.parent / "bin" / "libcamou_window_lock.dylib",
            Path("/tmp/libcamou_window_lock.dylib"),
        ]
        lock_dylib = next((c for c in candidates if c.is_file()), None)
        if lock_dylib:
            resolved_dylib = str(lock_dylib.resolve())
            spawn_env["DYLD_INSERT_LIBRARIES"] = resolved_dylib
            spawn_env["CAMOU_LOCK_WINDOW_SIZE"] = f"{target_w}x{target_h}"
            spawn_env["CAMOU_LOCK_MODE"] = lock_mode
            logger.info(f"Enforced native window control ({lock_mode}) via {resolved_dylib} for {target_w}×{target_h}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        env=spawn_env,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    pid = process.pid
    logger.info(f"Chromium process started for profile {profile_id} (pid={pid}, cdp_port={cdp_port})")

    # Start background CDP radar telemetry sync
    asyncio.create_task(
        auto_sync_radar_tab(cdp_port, profile_id, settings, proxy, launch_options)
    )

    return process, pid, cdp_port


async def auto_sync_radar_tab(
    cdp_port: int,
    profile_id: str,
    settings: BrowserSettings,
    proxy: ProxyConfig | None = None,
    launch_options: dict[str, Any] | None = None,
) -> None:
    """Seamlessly probe exit IP & Geo in background and inject into chrome://newtab/ via CDP."""
    import httpx
    from .proxy_check import resolve_exit_ip, locate
    from .synchronizer import send_cdp_command

    opts = launch_options or {}
    env_title = opts.get("profile_name") or profile_id or "新建环境"
    target_w, target_h = get_target_dimensions(settings)

    # 1. Resolve exit IP and Geo
    ip_str = "127.0.0.1"
    country_str = "本地环境"
    region_str = "--"
    city_str = "--"
    pings = {
        "TikTok": "75ms",
        "Google": "42ms",
        "Baidu": "18ms",
        "Facebook": "58ms",
        "Iphey": "64ms",
    }

    try:
        ip_val, lat = await resolve_exit_ip(proxy, timeout=4.0)
        ip_str = ip_val
        loc = locate(ip_val)
        if loc and loc.country:
            country_map = {
                "CN": "中国",
                "HK": "中国香港",
                "TW": "中国台湾",
                "MO": "中国澳门",
                "US": "美国",
                "JP": "日本",
                "GB": "英国",
                "SG": "新加坡",
                "DE": "德国",
                "FR": "法国",
                "KR": "韩国",
                "CA": "加拿大",
                "AU": "澳大利亚",
                "RU": "俄罗斯",
                "MY": "马来西亚",
                "TH": "泰国",
                "VN": "越南",
                "PH": "菲律宾",
                "ID": "印度尼西亚",
                "IN": "印度",
            }
            c_name = country_map.get(loc.country, loc.country)
            country_str = f"{c_name} ({loc.country})"
            if loc.timezone:
                parts = loc.timezone.split("/")
                if len(parts) > 1:
                    city_str = parts[-1].replace("_", " ")
        if lat:
            pings["Google"] = f"{min(lat, 999)}ms"
    except Exception as exc:
        logger.debug(f"Radar IP probe skipped/failed: {exc}")
        if proxy and proxy.server:
            ip_str = proxy.server.split(":")[0]
            country_str = "代理连接"

    # 2. Enforce physical window bounds at OS level (AdsPower spec) & inject radar telemetry into newtab
    window_bounds_set = False
    synced_radar_targets = set()

    for _ in range(3600):
        await asyncio.sleep(0.5 if not window_bounds_set else 1.5)
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                # A. Enforce physical OS window bounds via CDP Browser domain (AdsPower Architecture)
                # Keep window size locked so it cannot be maximized or leak desktop resolution
                try:
                    v_resp = await client.get(f"http://127.0.0.1:{cdp_port}/json/version")
                    if v_resp.status_code == 200:
                        b_ws = v_resp.json().get("webSocketDebuggerUrl")
                        targets_resp = await client.get(f"http://127.0.0.1:{cdp_port}/json/list")
                        if b_ws and targets_resp.status_code == 200:
                            t_list = [t for t in targets_resp.json() if t.get("type") == "page"]
                            if t_list:
                                tid = t_list[0].get("id")
                                win_info = await send_cdp_command(b_ws, "Browser.getWindowForTarget", {"targetId": tid})
                                if win_info and "result" in win_info and "windowId" in win_info["result"]:
                                    win_id = win_info["result"]["windowId"]
                                    b_info = win_info["result"].get("bounds", {})
                                    cur_state = b_info.get("windowState", "normal")
                                    cur_w = b_info.get("width", 0)
                                    # If uninitialized, or if maximized or enlarged beyond target resolution, lock it down!
                                    if not window_bounds_set or cur_state != "normal" or cur_w > (target_w + 120):
                                        await send_cdp_command(b_ws, "Browser.setWindowBounds", {
                                            "windowId": win_id,
                                            "bounds": {
                                                "left": 50,
                                                "top": 50,
                                                "width": target_w,
                                                "height": target_h,
                                                "windowState": "normal",
                                            }
                                        })
                                        window_bounds_set = True
                                        logger.info(f"AdsPower-style physical window locked: {target_w}×{target_h} (win_id={win_id})")
                except Exception as w_exc:
                    logger.debug(f"Could not enforce physical window bounds yet: {w_exc}")

                # B. Radar Telemetry Data Injection (for newtab pages)
                resp = await client.get(f"http://127.0.0.1:{cdp_port}/json/list")
                if resp.status_code != 200:
                    continue
                targets = resp.json()
                for t in targets:
                    if t.get("type") != "page":
                        continue
                    tid = t.get("id")
                    url = t.get("url", "")
                    ws_url = t.get("webSocketDebuggerUrl")
                    if not ws_url:
                        continue

                    if tid not in synced_radar_targets and ("newtab" in url or "new-tab-page" in url or "radar" in url):
                        payload_data = {
                            "envTitle": env_title,
                            "ip": ip_str,
                            "country": country_str,
                            "region": region_str,
                            "city": city_str,
                            "targetW": target_w,
                            "targetH": target_h,
                            "pings": pings,
                        }
                        expr = f"""
(function() {{
    if (typeof window.updateRadarData === 'function') {{
        window.updateRadarData({json.dumps(payload_data)});
    }}
    const cssFix = `
        .sandbox-stage {{ padding: 12px 8px 32px 8px !important; }}
        .sandbox-viewport {{ padding: 20px 14px !important; box-sizing: border-box !important; max-width: 100% !important; }}
        .dock-grid {{ display: flex !important; flex-wrap: wrap !important; justify-content: center !important; gap: 8px !important; }}
        .dock-item {{ flex: 1 1 calc(33.33% - 8px) !important; min-width: 75px !important; max-width: 110px !important; box-sizing: border-box !important; }}
        .info-grid {{ display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 8px !important; }}
        .info-card {{ padding: 10px 8px !important; }}
        .info-title {{ font-size: 11px !important; margin-bottom: 4px !important; }}
        .info-value {{ font-size: 12px !important; line-height: 1.4 !important; }}
    `;
    let s = document.getElementById('cpm-responsive-style');
    if (!s) {{
        s = document.createElement('style');
        s.id = 'cpm-responsive-style';
        document.head.appendChild(s);
    }}
    s.textContent = cssFix;
}})();
"""
                        await send_cdp_command(ws_url, "Runtime.evaluate", {"expression": expr})
                        synced_radar_targets.add(tid)
                        logger.info(f"Injected radar telemetry and responsive layout into newtab (target {tid}) for profile {profile_id}: IP={ip_str}")
        except Exception:
            pass
