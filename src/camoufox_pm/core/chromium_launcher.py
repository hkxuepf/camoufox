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


def get_chromium_executable_path() -> str | None:
    """Find the path to the Chromium executable on the current system."""
    custom_path = os.environ.get("CPM_CHROMIUM_PATH")
    if custom_path and Path(custom_path).is_file():
        return custom_path

    if sys.platform == "darwin":
        candidates = [
            str(Path.home() / "Library" / "Application Support" / "Camoufox Profile Manager" / "bin" / "Chromium.app" / "Contents" / "MacOS" / "Chromium"),
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

    # 1. Manifest V3 with world: MAIN for zero-latency in-page prototype interception
    manifest: dict[str, Any] = {
        "manifest_version": 3,
        "name": "Camoufox Anti-Detect Extension",
        "version": "1.0.0",
        "description": "Stealth fingerprint protection and isolation provider",
        "permissions": ["storage", "cookies"],
        "host_permissions": ["<all_urls>"],
        "content_scripts": [
            {
                "matches": ["<all_urls>"],
                "js": ["inject.js"],
                "run_at": "document_start",
                "world": "MAIN",
            }
        ],
    }

    # Handle preset/imported cookies injection
    if cookies_raw and cookies_raw.strip():
        parsed_cookies = []
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
                    # Netscape format: domain, flag, path, secure, expiry, name, value
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

        if parsed_cookies:
            (extension_dir / "cookies.json").write_text(json.dumps(parsed_cookies), encoding="utf-8")
            manifest["background"] = {"service_worker": "background.js"}
            background_js = """
chrome.runtime.onInstalled.addListener(async () => {
    try {
        const resp = await fetch(chrome.runtime.getURL('cookies.json'));
        if (!resp.ok) return;
        const cookies = await resp.json();
        for (const c of cookies) {
            try {
                let domain = (c.domain || '').replace(/^\\./, '');
                let url = c.url;
                if (!url) {
                    url = (c.secure ? 'https://' : 'http://') + (domain || 'localhost') + (c.path || '/');
                }
                await chrome.cookies.set({
                    url: url,
                    name: c.name,
                    value: c.value,
                    domain: c.domain || undefined,
                    path: c.path || '/',
                    secure: Boolean(c.secure),
                    httpOnly: Boolean(c.httpOnly),
                    sameSite: c.sameSite || 'lax',
                    expirationDate: c.expirationDate || c.expiry || (Date.now() / 1000 + 86400 * 365)
                });
            } catch (e) {}
        }
    } catch (e) {}
});
"""
            (extension_dir / "background.js").write_text(background_js.strip(), encoding="utf-8")

    # 2. Search Provider Override (Fixes Ungoogled Chromium "No Search" omnibox domain error)
    engine_key = (getattr(settings, "search_engine", None) or "google").lower()
    if engine_key != "none" and engine_key in SEARCH_CONFIGS:
        cfg = SEARCH_CONFIGS[engine_key]
        manifest["chrome_settings_overrides"] = {
            "search_provider": {
                "name": cfg["name"],
                "keyword": cfg["keyword"],
                "search_url": cfg["search_url"],
                "suggest_url": cfg["suggest_url"],
                "favicon_url": cfg["favicon_url"],
                "encoding": "UTF-8",
                "is_default": True,
            }
        }

    # 3. Injected JS for Fingerprint Spoofing & Stealth Prototype Protection
    target_os = (getattr(settings, "os", None) or "windows").lower()
    if settings.user_agent:
        ua_l = settings.user_agent.lower()
        if "windows" in ua_l:
            target_os = "windows"
        elif "mac" in ua_l:
            target_os = "macos"
        elif "linux" in ua_l:
            target_os = "linux"

    full_ver = "130.0.6723.69"
    major_ver = "130"
    if settings.user_agent:
        import re
        m_full = re.search(r"Chrome/(\d+\.\d+\.\d+\.\d+)", settings.user_agent)
        if m_full:
            full_ver = m_full.group(1)
            major_ver = full_ver.split(".")[0]
        else:
            m_maj = re.search(r"Chrome/(\d+)", settings.user_agent)
            if m_maj:
                major_ver = m_maj.group(1)
                full_ver = f"{major_ver}.0.0.0"

    coords = getattr(settings, "geolocation", None) or {}
    config_json = json.dumps({
        "targetOS": target_os,
        "majorVersion": major_ver,
        "fullVersion": full_ver,
        "webglVendor": settings.webgl_vendor,
        "webglRenderer": settings.webgl_renderer,
        "hardwareConcurrency": settings.hardware_concurrency,
        "deviceMemory": settings.device_memory,
        "canvasNoise": settings.canvas_noise,
        "audioNoise": settings.audio_noise,
        "clientRectsNoise": settings.client_rects_noise,
        "batterySpoofing": settings.battery_spoofing,
        "doNotTrack": settings.do_not_track,
        "fontMasking": getattr(settings, "font_masking", True),
        "clipboardIsolation": getattr(settings, "clipboard_isolation", True),
        "timezone": getattr(settings, "timezone", None),
        "languages": settings.languages or [],
        "latitude": coords.get("lat") if isinstance(coords, dict) else None,
        "longitude": coords.get("lon") if isinstance(coords, dict) else None,
    })

    inject_script = f"""(function() {{
    'use strict';
    const cfg = {config_json};

    // --- Native Function Prototype Masking (makeNative) ---
    const nativeToString = Function.prototype.toString;
    const fnToStringMap = new WeakMap();

    function makeNative(fn, name) {{
        if (!fn || typeof fn !== 'function') return fn;
        const nativeStr = 'function ' + (name || fn.name || '') + '() {{ [native code] }}';
        fnToStringMap.set(fn, nativeStr);
        try {{
            Object.defineProperty(fn, 'name', {{ value: name || fn.name, configurable: true }});
        }} catch(e) {{}}
        return fn;
    }}

    try {{
        Function.prototype.toString = new Proxy(nativeToString, {{
            apply(target, thisArg, args) {{
                if (fnToStringMap.has(thisArg)) {{
                    return fnToStringMap.get(thisArg);
                }}
                return Reflect.apply(target, thisArg, args);
            }}
        }});
        fnToStringMap.set(Function.prototype.toString, "function toString() {{ [native code] }}");
    }} catch(e) {{}}

    // --- 1. Navigator Platform & UserAgentData Alignment ---
    try {{
        const plat = cfg.targetOS === 'windows' ? 'Win32' : cfg.targetOS === 'macos' ? 'MacIntel' : 'Linux x86_64';
        Object.defineProperty(Navigator.prototype, 'platform', {{
            get: makeNative(() => plat, 'get platform'),
            enumerable: true,
            configurable: true
        }});

        if (cfg.languages && cfg.languages.length > 0) {{
            const primaryLang = cfg.languages[0];
            const langsList = Object.freeze([...cfg.languages]);
            Object.defineProperty(Navigator.prototype, 'language', {{
                get: makeNative(() => primaryLang, 'get language'),
                enumerable: true,
                configurable: true
            }});
            Object.defineProperty(Navigator.prototype, 'languages', {{
                get: makeNative(() => langsList, 'get languages'),
                enumerable: true,
                configurable: true
            }});

            // Intercept all Intl APIs to align resolved locale with primaryLang
            const intlKeys = ['DateTimeFormat', 'NumberFormat', 'Collator', 'PluralRules', 'RelativeTimeFormat', 'ListFormat'];
            for (const key of intlKeys) {{
                if (typeof Intl !== 'undefined' && Intl[key] && Intl[key].prototype && Intl[key].prototype.resolvedOptions) {{
                    const origFn = Intl[key].prototype.resolvedOptions;
                    Intl[key].prototype.resolvedOptions = makeNative(function() {{
                        const opts = origFn.apply(this, arguments);
                        opts.locale = primaryLang;
                        if (key === 'DateTimeFormat' && cfg.timezone) {{
                            opts.timeZone = cfg.timezone;
                        }}
                        return opts;
                    }}, 'resolvedOptions');
                }}
            }}
        }} else if (cfg.timezone) {{
            if (typeof Intl !== 'undefined' && Intl.DateTimeFormat && Intl.DateTimeFormat.prototype.resolvedOptions) {{
                const origResolved = Intl.DateTimeFormat.prototype.resolvedOptions;
                Intl.DateTimeFormat.prototype.resolvedOptions = makeNative(function() {{
                    const res = origResolved.apply(this, arguments);
                    res.timeZone = cfg.timezone;
                    return res;
                }}, 'resolvedOptions');
            }}
        }}

        const platName = cfg.targetOS === 'windows' ? 'Windows' : cfg.targetOS === 'macos' ? 'macOS' : 'Linux';
        const brands = [
            {{ brand: 'Chromium', version: cfg.majorVersion || '130' }},
            {{ brand: 'Google Chrome', version: cfg.majorVersion || '130' }},
            {{ brand: 'Not?A_Brand', version: '99' }}
        ];
        const uad = {{
            brands: brands,
            mobile: false,
            platform: platName,
            getHighEntropyValues: makeNative(function(hints) {{
                return Promise.resolve({{
                    brands: brands,
                    mobile: false,
                    platform: platName,
                    platformVersion: platName === 'Windows' ? '15.0.0' : '14.5.0',
                    architecture: 'x86',
                    bitness: '64',
                    model: '',
                    uaFullVersion: cfg.fullVersion || (cfg.majorVersion + '.0.0.0'),
                    fullVersionList: brands.map(b => ({{ brand: b.brand, version: b.brand.includes('Not') ? '99.0.0.0' : (cfg.fullVersion || (cfg.majorVersion + '.0.0.0')) }}))
                }});
            }}, 'getHighEntropyValues'),
            toJSON: makeNative(function() {{
                return {{ brands: brands, mobile: false, platform: platName }};
            }}, 'toJSON')
        }};
        Object.defineProperty(Navigator.prototype, 'userAgentData', {{
            get: makeNative(() => uad, 'get userAgentData'),
            enumerable: true,
            configurable: true
        }});
    }} catch(e) {{}}

    // --- 2. WebGL Vendor & Renderer Spoofing ---
    if (cfg.webglVendor || cfg.webglRenderer) {{
        const getParameterOriginals = [
            WebGLRenderingContext.prototype.getParameter,
            WebGL2RenderingContext.prototype.getParameter
        ];

        const overrideGetParameter = function(original) {{
            return makeNative(function(param) {{
                // 0x9245: UNMASKED_VENDOR_WEBGL
                if (param === 0x9245 && cfg.webglVendor) {{
                    return cfg.webglVendor;
                }}
                // 0x9246: UNMASKED_RENDERER_WEBGL
                if (param === 0x9246 && cfg.webglRenderer) {{
                    return cfg.webglRenderer;
                }}
                return original.apply(this, arguments);
            }}, 'getParameter');
        }};

        WebGLRenderingContext.prototype.getParameter = overrideGetParameter(getParameterOriginals[0]);
        WebGL2RenderingContext.prototype.getParameter = overrideGetParameter(getParameterOriginals[1]);

        // Filter out macOS-specific WebGL texture extensions when pretending to be Windows
        if (cfg.targetOS === 'windows') {{
            const filterExtensions = function(origFn) {{
                return makeNative(function() {{
                    const exts = origFn.apply(this, arguments);
                    if (!exts || !Array.isArray(exts)) return exts;
                    const macSpecific = ['WEBGL_compressed_texture_astc', 'WEBGL_compressed_texture_pvrtc'];
                    return exts.filter(e => !macSpecific.includes(e));
                }}, 'getSupportedExtensions');
            }};
            WebGLRenderingContext.prototype.getSupportedExtensions = filterExtensions(WebGLRenderingContext.prototype.getSupportedExtensions);
            WebGL2RenderingContext.prototype.getSupportedExtensions = filterExtensions(WebGL2RenderingContext.prototype.getSupportedExtensions);
        }}
    }}

    // --- 3. Hardware Concurrency (CPU Cores) ---
    if (cfg.hardwareConcurrency) {{
        try {{
            Object.defineProperty(Navigator.prototype, 'hardwareConcurrency', {{
                get: makeNative(() => cfg.hardwareConcurrency, 'get hardwareConcurrency'),
                enumerable: true,
                configurable: true
            }});
        }} catch(e) {{}}
    }}

    // --- 4. Device Memory (RAM) ---
    if (cfg.deviceMemory) {{
        try {{
            Object.defineProperty(Navigator.prototype, 'deviceMemory', {{
                get: makeNative(() => cfg.deviceMemory, 'get deviceMemory'),
                enumerable: true,
                configurable: true
            }});
        }} catch(e) {{}}
    }}

    // --- 5. Subtle Canvas Noise ---
    if (cfg.canvasNoise) {{
        const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = makeNative(function(sx, sy, sw, sh) {{
            const imgData = origGetImageData.apply(this, arguments);
            const data = imgData.data;
            const len = data.length;
            const step = Math.max(16, Math.floor(len / 200));
            for (let i = 0; i < len; i += step) {{
                const mod = i % 4;
                if (mod < 3) {{
                    data[i] = (data[i] + (i % 2 === 0 ? 1 : 255)) % 256;
                }}
            }}
            return imgData;
        }}, 'getImageData');

        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = makeNative(function() {{
            const ctx = this.getContext('2d');
            if (ctx && this.width > 0 && this.height > 0) {{
                try {{
                    const imgData = ctx.getImageData(0, 0, 1, 1);
                    imgData.data[0] = (imgData.data[0] + 1) % 256;
                    ctx.putImageData(imgData, 0, 0);
                }} catch(e) {{}}
            }}
            return origToDataURL.apply(this, arguments);
        }}, 'toDataURL');
    }}

    // --- 6. AudioContext Fingerprint Noise (Idempotent & Natural Noise Floor) ---
    if (cfg.audioNoise && typeof AudioBuffer !== 'undefined') {{
        const origGetChannelData = AudioBuffer.prototype.getChannelData;
        const modifiedBuffers = new WeakSet();
        AudioBuffer.prototype.getChannelData = makeNative(function(channel) {{
            const data = origGetChannelData.apply(this, arguments);
            // Idempotent protection: never re-apply noise on multiple calls to the same AudioBuffer
            if (!modifiedBuffers.has(this)) {{
                modifiedBuffers.add(this);
                const len = data.length;
                for (let i = 0; i < len; i += 64) {{
                    // Imperceptible physical micro-jitter (1e-8) without periodic step signature
                    const jitter = ((Math.sin(i * 12.9898) * 43758.5453) % 1) * 0.00000002;
                    data[i] += jitter;
                }}
            }}
            return data;
        }}, 'getChannelData');
    }}

    // --- 7. ClientRects Noise ---
    if (cfg.clientRectsNoise) {{
        const origGetBoundingClientRect = Element.prototype.getBoundingClientRect;
        Element.prototype.getBoundingClientRect = makeNative(function() {{
            const rect = origGetBoundingClientRect.apply(this, arguments);
            const delta = 0.00001;
            return new DOMRect(rect.x + delta, rect.y, rect.width, rect.height);
        }}, 'getBoundingClientRect');
    }}

    // --- 8. Battery API Spoofing ---
    if (cfg.batterySpoofing && navigator.getBattery) {{
        navigator.getBattery = makeNative(() => Promise.resolve({{
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: 1.0,
            addEventListener: makeNative(() => {{}}, 'addEventListener'),
            removeEventListener: makeNative(() => {{}}, 'removeEventListener')
        }}), 'getBattery');
    }}

    // --- 9. Timezone & Intl Consistency ---
    if (cfg.timezone) {{
        try {{
            const origResolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
            Intl.DateTimeFormat.prototype.resolvedOptions = makeNative(function() {{
                const res = origResolvedOptions.apply(this, arguments);
                res.timeZone = cfg.timezone;
                return res;
            }}, 'resolvedOptions');
        }} catch(e) {{}}
    }}

    // --- 10. Geolocation Coordinates Override ---
    if (cfg.latitude != null && cfg.longitude != null && navigator.geolocation) {{
        try {{
            navigator.geolocation.getCurrentPosition = makeNative(function(success, error, options) {{
                if (typeof success === 'function') {{
                    success({{
                        coords: {{
                            latitude: cfg.latitude,
                            longitude: cfg.longitude,
                            accuracy: 35.0,
                            altitude: null,
                            altitudeAccuracy: null,
                            heading: null,
                            speed: null
                        }},
                        timestamp: Date.now()
                    }});
                }}
            }}, 'getCurrentPosition');

            navigator.geolocation.watchPosition = makeNative(function(success, error, options) {{
                if (typeof success === 'function') {{
                    success({{
                        coords: {{
                            latitude: cfg.latitude,
                            longitude: cfg.longitude,
                            accuracy: 35.0,
                            altitude: null,
                            altitudeAccuracy: null,
                            heading: null,
                            speed: null
                        }},
                        timestamp: Date.now()
                    }});
                }}
                return 1;
            }}, 'watchPosition');
        }} catch(e) {{}}
    }}

    // --- 11. Virtual Media Devices (Audio/Video Hardware Isolation) ---
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {{
        try {{
            const virtualDevices = [
                {{
                    deviceId: "default",
                    kind: "audioinput",
                    label: "Default - Internal Microphone",
                    groupId: "virtual-audio-group-01"
                }},
                {{
                    deviceId: "virtual-mic-dev-01",
                    kind: "audioinput",
                    label: "Microphone (Realtek High Definition Audio)",
                    groupId: "virtual-audio-group-01"
                }},
                {{
                    deviceId: "default",
                    kind: "audiooutput",
                    label: "Default - Internal Speaker",
                    groupId: "virtual-audio-group-01"
                }},
                {{
                    deviceId: "virtual-spk-dev-01",
                    kind: "audiooutput",
                    label: "Speakers (Realtek High Definition Audio)",
                    groupId: "virtual-audio-group-01"
                }},
                {{
                    deviceId: "virtual-cam-dev-01",
                    kind: "videoinput",
                    label: "HD Webcam",
                    groupId: "virtual-video-group-01"
                }}
            ];
            navigator.mediaDevices.enumerateDevices = makeNative(function() {{
                return Promise.resolve(virtualDevices);
            }}, 'enumerateDevices');
        }} catch(e) {{}}
    }}

    // --- 12. Hardware Font Fingerprint Masking & Isolation ---
    if (cfg.fontMasking) {{
        const MAC_ONLY_FONTS = [
            'applegothic', 'apple color emoji', 'apple sd gothic neo', 'apple chancery', 'apple braille',
            'apple symbols', 'menlo', 'monaco', 'geneva', 'pingfang sc', 'pingfang tc', 'pingfang hk',
            'hiragino sans', 'hiragino kaku gothic pron', 'hiragino mincho pron', 'sf pro', 'sf mono',
            'sf compact', 'helvetica neue', 'baskerville', 'optima', 'gill sans', 'didot',
            'american typewriter', 'marker felt', 'chalkboard', 'zapfino', 'thonburi', 'avenir',
            'avenir next', 'al nile', 'big caslon', 'copperplate', 'cochin', 'iowan old style'
        ];
        const WIN_ONLY_FONTS = [
            'calibri', 'cambria', 'candara', 'consolas', 'constantia', 'corbel', 'ebrima',
            'franklin gothic medium', 'gabriola', 'gadugi', 'ink free', 'leelawadee ui',
            'lucida console', 'malgun gothic', 'marlett', 'microsoft jhenghei', 'microsoft yahei',
            'ms gothic', 'ms pgothic', 'ms ui gothic', 'mv boli', 'myanmar text', 'nirmala ui',
            'segoe print', 'segoe script', 'segoe ui', 'segoe ui emoji', 'segoe ui symbol',
            'simsun', 'nsimsun', 'sitka', 'sylfaen', 'yu gothic'
        ];
        const blacklist = cfg.targetOS === 'windows' ? MAC_ONLY_FONTS : (cfg.targetOS === 'macos' ? WIN_ONLY_FONTS : []);

        if (blacklist.length > 0) {{
            // Intercept document.fonts.check
            if (document.fonts && document.fonts.check) {{
                const origFontsCheck = document.fonts.check;
                document.fonts.check = makeNative(function(font) {{
                    if (typeof font === 'string') {{
                        const fLower = font.toLowerCase();
                        for (let i = 0; i < blacklist.length; i++) {{
                            if (fLower.includes(blacklist[i])) return false;
                        }}
                    }}
                    return origFontsCheck.apply(this, arguments);
                }}, 'check');
            }}

            // Intercept FontFaceSet.prototype.check
            if (typeof FontFaceSet !== 'undefined' && FontFaceSet.prototype.check) {{
                const origSetCheck = FontFaceSet.prototype.check;
                FontFaceSet.prototype.check = makeNative(function(font) {{
                    if (typeof font === 'string') {{
                        const fLower = font.toLowerCase();
                        for (let i = 0; i < blacklist.length; i++) {{
                            if (fLower.includes(blacklist[i])) return false;
                        }}
                    }}
                    return origSetCheck.apply(this, arguments);
                }}, 'check');
            }}

            // Intercept Canvas measureText font leakage
            const origMeasureText = CanvasRenderingContext2D.prototype.measureText;
            CanvasRenderingContext2D.prototype.measureText = makeNative(function(text) {{
                if (this.font) {{
                    const fontLower = this.font.toLowerCase();
                    for (let i = 0; i < blacklist.length; i++) {{
                        const bf = blacklist[i];
                        if (fontLower.includes(bf)) {{
                            const prevFont = this.font;
                            this.font = prevFont.replace(new RegExp(`['"]?${{bf}}['"]?`, 'gi'), 'sans-serif');
                            const metrics = origMeasureText.apply(this, arguments);
                            this.font = prevFont;
                            return metrics;
                        }}
                    }}
                }}
                return origMeasureText.apply(this, arguments);
            }}, 'measureText');

            // Intercept window.queryLocalFonts (Chrome 103+)
            if (typeof window.queryLocalFonts === 'function') {{
                const origQuery = window.queryLocalFonts;
                window.queryLocalFonts = makeNative(async function() {{
                    try {{
                        const list = await origQuery.apply(this, arguments);
                        return list.filter(f => !blacklist.some(b => (f.family || '').toLowerCase().includes(b)));
                    }} catch(e) {{
                        return [];
                    }}
                }}, 'queryLocalFonts');
            }}
        }}
    }}

    // --- 13. Anti-Automation Cleanup & Native Chrome Object ---
    try {{
        Object.defineProperty(Navigator.prototype, 'webdriver', {{
            get: makeNative(() => undefined, 'get webdriver'),
            enumerable: true,
            configurable: true
        }});
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_;
        if (!window.chrome) window.chrome = {{}};
        if (!window.chrome.app) {{
            window.chrome.app = {{
                isInstalled: false,
                InstallState: {{ DISABLED: "disabled", INSTALLED: "installed", NOT_INSTALLED: "not_installed" }},
                RunningState: {{ CANNOT_RUN: "cannot_run", READY_TO_RUN: "ready_to_run", RUNNING: "running" }},
                getIsInstalled: makeNative(() => false, 'getIsInstalled'),
                getDetails: makeNative(() => null, 'getDetails'),
                getInstallState: makeNative(() => "not_installed", 'getInstallState')
            }};
        }}
    }} catch(e) {{}}

    // --- 14. Virtual Isolated Clipboard Sandbox (Anti-Snoop) ---
    if (cfg.clipboardIsolation) {{
        let virtualClipText = "";
        if (navigator.clipboard) {{
            const origWriteText = navigator.clipboard.writeText;
            navigator.clipboard.writeText = makeNative(function(text) {{
                virtualClipText = String(text != null ? text : "");
                if (origWriteText) {{
                    try {{ origWriteText.apply(this, arguments); }} catch(e) {{}}
                }}
                return Promise.resolve();
            }}, 'writeText');

            navigator.clipboard.readText = makeNative(function() {{
                // Isolated per-profile virtual sandbox: never leaks desktop OS clipboard to malicious web probes
                return Promise.resolve(virtualClipText || "");
            }}, 'readText');
        }}
    }}
    }})();
    """

    # 15. Native Integrated Health & Environment Radar NewTab Override (Matching Hubstudio)
    if getattr(settings, "open_health_radar", True):
        manifest["chrome_url_overrides"] = {
            "newtab": "radar.html"
        }
        try:
            from camoufox_pm.api.routes.radar import generate_radar_html_str, generate_radar_js_str
            env_title = profile_name or profile_id or "新建环境"
            grp = group_name or "未分组"
            nts = notes or "--"
            acc = account or ""
            langs = settings.languages or ["zh-CN"]
            l_str = ", ".join(langs) if langs else "zh-CN"
            tz = settings.timezone or "Asia/Shanghai"
            raw_os = (getattr(settings, "os", None) or "windows").lower()
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
            cores = settings.hardware_concurrency or 8
            mem = settings.device_memory or 8
            w = settings.window_width or 1280
            h = settings.window_height or 720
            p_type_str = str(proxy.type.value if hasattr(proxy.type, "value") else proxy.type).upper() if proxy else ""
            proxy_display = f"{p_type_str} {proxy.server}" if proxy and proxy.server else "直连模式 (Direct)"

            ua_str = getattr(settings, "user_agent", None) or ""
            if not ua_str:
                if raw_os == "macos":
                    ua_str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8035.120 Safari/537.36"
                elif raw_os == "android":
                    ua_str = "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8035.120 Mobile Safari/537.36"
                elif raw_os == "ios":
                    ua_str = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/154.0.8035.120 Mobile/15E148 Safari/604.1"
                elif raw_os == "linux":
                    ua_str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8035.120 Safari/537.36"
                else:
                    ua_str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8035.120 Safari/537.36"

            radar_html_code = generate_radar_html_str(
                env_name=env_title,
                group_name=grp,
                notes=nts,
                account=acc,
                lang_str=l_str,
                timezone=tz,
                ua_str=ua_str,
                os_name=os_display,
                arch_str=arch_display,
                cpu_cores=cores,
                memory_gb=mem,
                screen_res=f"{w} × {h}",
                webgl_vendor=settings.webgl_vendor or "Google Inc. (ANGLE)",
                webgl_renderer=settings.webgl_renderer or "ANGLE (Direct3D11)",
                engine_name="Chromium 154",
                proxy_info=proxy_display,
                init_ip="探查中...",
            )
            radar_js_code = generate_radar_js_str(timezone=tz, expected_languages=settings.languages or None)
            (extension_dir / "radar.html").write_text(radar_html_code, encoding="utf-8")
            (extension_dir / "radar.js").write_text(radar_js_code, encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Failed to generate radar.html for extension: {exc}")

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
) -> list[str]:
    """Construct full command-line arguments for launching Chromium."""
    args = [
        f"--user-data-dir={storage_path}",
        "--no-first-run",
        "--no-default-browser-check",
        "--hide-crash-restore-bubble",
        "--disable-sync",
        "--password-store=basic",
        "--disable-features=Translate,OptimizationHints,MediaRouter",
        "--test-type",
    ]

    # Custom or spoofed User-Agent
    if settings.user_agent:
        args.append(f"--user-agent={settings.user_agent}")

    # Window geometry
    width = settings.window_width or 1280
    height = settings.window_height or 720
    args.append(f"--window-size={width},{height}")

    # Device Pixel Ratio
    if settings.device_pixel_ratio and settings.device_pixel_ratio != 1.0:
        args.append(f"--force-device-scale-factor={settings.device_pixel_ratio}")

    # Languages
    if settings.languages:
        args.append(f"--lang={settings.languages[0]}")
        args.append(f"--accept-lang={','.join(settings.languages)}")

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

    # Startup URL: if explicitly specified, launch it; otherwise, the extension newtab override handles start page
    startup_url = getattr(settings, "startup_url", None)
    if startup_url:
        args.append(startup_url)

    return args


def configure_search_engine(user_data_dir: Path, engine_name: str = "google", settings: BrowserSettings | None = None) -> None:
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

    # 1. Update or create Default/Web Data SQLite database
    db_path = default_dir / "Web Data"
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS meta(key LONGVARCHAR NOT NULL UNIQUE PRIMARY KEY, value LONGVARCHAR);")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY,
                short_name VARCHAR NOT NULL,
                keyword VARCHAR NOT NULL,
                favicon_url VARCHAR NOT NULL,
                url VARCHAR NOT NULL,
                safe_for_autoreplace INTEGER,
                originating_url VARCHAR,
                date_created INTEGER DEFAULT 0,
                usage_count INTEGER DEFAULT 0,
                input_encodings VARCHAR,
                suggest_url VARCHAR,
                prepopulate_id INTEGER DEFAULT 0,
                created_by_policy INTEGER DEFAULT 0,
                last_modified INTEGER DEFAULT 0,
                sync_guid VARCHAR,
                alternate_urls VARCHAR,
                image_url VARCHAR,
                search_url_post_params VARCHAR,
                suggest_url_post_params VARCHAR,
                image_url_post_params VARCHAR,
                new_tab_url VARCHAR,
                last_visited INTEGER DEFAULT 0,
                created_from_play_api INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                starter_pack_id INTEGER DEFAULT 0,
                enforced_by_policy INTEGER DEFAULT 0,
                featured_by_policy INTEGER DEFAULT 0,
                url_hash BLOB
            );
        """)
        meta_rows = [
            ("mmap_status", "-1"),
            ("version", "154"),
            ("last_compatible_version", "151"),
            ("Builtin Keyword Version", "211"),
            ("Builtin Keyword Country", "17230"),
            ("Is Prepopulated Engines Migration Enabled", "0"),
            ("Starter Pack Keyword Version", "13"),
        ]
        cur.executemany("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", meta_rows)

        # Check if prepopulate_id 1 exists
        row = cur.execute("SELECT id FROM keywords WHERE prepopulate_id = 1").fetchone()
        if row:
            cur.execute("""
                UPDATE keywords
                SET short_name = ?,
                    keyword = ?,
                    favicon_url = ?,
                    url = ?,
                    suggest_url = ?,
                    is_active = 1
                WHERE prepopulate_id = 1 OR short_name = 'No Search'
            """, (
                target_engine["name"],
                target_engine["keyword"],
                target_engine["favicon"],
                target_engine["url"],
                target_engine["suggest"],
            ))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO keywords (
                    id, short_name, keyword, favicon_url, url, safe_for_autoreplace,
                    originating_url, date_created, usage_count, input_encodings,
                    suggest_url, prepopulate_id, created_by_policy, last_modified,
                    sync_guid, alternate_urls, is_active
                ) VALUES (
                    1, ?, ?, ?,
                    ?, 1,
                    '', 13300000000000000, 1, 'UTF-8',
                    ?, 1, 0, 13300000000000000,
                    '485bf7d3-0215-45af-87dc-538868000001', '[]', 1
                )
            """, (
                target_engine["name"],
                target_engine["keyword"],
                target_engine["favicon"],
                target_engine["url"],
                target_engine["suggest"],
            ))
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning(f"Could not configure search engine in Web Data: {exc}")

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

        if settings and getattr(settings, "languages", None):
            intl_prefs = prefs_data.setdefault("intl", {})
            lang_str = ",".join(settings.languages)
            intl_prefs["accept_languages"] = lang_str
            intl_prefs["selected_languages"] = lang_str

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
            ls_intl = ls_data.setdefault("intl", {})
            ls_intl["app_locale"] = settings.languages[0].replace("-", "_")
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

    # Preconfigure search engine and language preferences
    configure_search_engine(user_data_dir, getattr(settings, "search_engine", "google"), settings=settings)

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

    extra_exts = launch_options.get("extensions", [])
    cmd_args = build_chromium_args(
        user_data_dir,
        ext_dir,
        settings,
        proxy,
        cdp_port=cdp_port,
        extra_extensions=extra_exts,
        profile_id=profile_id,
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
        # Set locale environment variables
        spawn_env["LANGUAGE"] = ":".join(settings.languages)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        env=spawn_env,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    pid = process.pid
    logger.info(f"Chromium process started for profile {profile_id} (pid={pid}, cdp_port={cdp_port})")
    return process, pid, cdp_port
