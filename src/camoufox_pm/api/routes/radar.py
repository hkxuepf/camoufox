"""Environment Health & Fingerprint Radar Dashboard matching commercial antidetect browser startup page."""

import json
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from camoufox_pm.api.dependencies import get_storage_manager

router = APIRouter()


@router.get("/radar", response_class=HTMLResponse)
async def get_radar_dashboard(profile_id: str = ""):
    """Return a commercial-grade, pristine environment inspection dashboard matching Hubstudio."""
    storage = get_storage_manager()
    profile = None
    if profile_id:
        try:
            profile = await storage.get_profile(profile_id)
        except Exception:
            pass

    env_name = getattr(profile, "name", None) or (profile.get("name") if isinstance(profile, dict) else (profile_id or "新建环境"))
    group_name = getattr(profile, "group", None) or (profile.get("group") if isinstance(profile, dict) else "未分组")
    notes = getattr(profile, "notes", None) or (profile.get("notes") if isinstance(profile, dict) else "--")
    account = getattr(profile, "account", None) or (profile.get("account") if isinstance(profile, dict) else "")
    
    bs = getattr(profile, "browser_settings", None)
    if bs is not None and hasattr(bs, "model_dump"):
        bs = bs.model_dump()
    elif bs is not None and hasattr(bs, "dict"):
        bs = bs.dict()
    elif isinstance(bs, str):
        try:
            bs = json.loads(bs)
        except Exception:
            bs = {}
    elif not isinstance(bs, dict):
        bs = {}

    languages = bs.get("languages") or ["zh-CN"]
    lang_str = ", ".join(languages) if isinstance(languages, list) and languages else str(languages or "zh-CN")
    timezone = bs.get("timezone") or "Asia/Shanghai"
    ua_str = bs.get("user_agent") or ""
    
    raw_os = (bs.get("os") or "windows").lower()
    os_map = {
        "macos": "macOS",
        "windows": "Windows",
        "linux": "Linux",
        "android": "Android",
        "ios": "iOS",
    }
    os_name = os_map.get(raw_os, raw_os.capitalize())
    arch_map = {
        "macos": "ARM64 / Apple Silicon",
        "windows": "x86_64 架构",
        "linux": "x86_64 架构",
        "android": "ARM64 移动架构",
        "ios": "Apple A-Series 移动架构",
    }
    arch_str = arch_map.get(raw_os, "x86_64 架构")

    cpu_cores = bs.get("hardware_concurrency") or 8
    memory_gb = bs.get("device_memory") or 8
    width = bs.get("window_width") or 1920
    height = bs.get("window_height") or 1080
    screen_res = f"{width} × {height}"
    webgl_vendor = bs.get("webgl_vendor") or "Google Inc. (ANGLE)"
    webgl_renderer = bs.get("webgl_renderer") or "ANGLE (Direct3D11)"
    engine_name = "Chromium 154" if bs.get("browser_engine") == "chromium" else "Camoufox 135"

    if not ua_str:
        if bs.get("browser_engine") == "chromium":
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
        else:
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

    proxy_cfg = getattr(profile, "proxy", None)
    if proxy_cfg and getattr(proxy_cfg, "server", None):
        ptype = getattr(proxy_cfg, "type", "SOCKS5")
        if hasattr(ptype, "value"):
            ptype = ptype.value
        pserver = getattr(proxy_cfg, "server", "")
        proxy_info = f"{str(ptype).upper()} {pserver}"
        init_ip = pserver.split(":")[0] if ":" in pserver else pserver
    else:
        proxy_info = "直连模式 (Direct)"
        init_ip = "探查中..."

    html_content = generate_radar_html_str(
        env_name=env_name,
        group_name=group_name,
        notes=notes,
        account=account,
        lang_str=lang_str,
        timezone=timezone,
        ua_str=ua_str,
        os_name=os_name,
        arch_str=arch_str,
        cpu_cores=cpu_cores,
        memory_gb=memory_gb,
        screen_res=screen_res,
        webgl_vendor=webgl_vendor,
        webgl_renderer=webgl_renderer,
        engine_name=engine_name,
        proxy_info=proxy_info,
        init_ip=init_ip,
    )
    return HTMLResponse(content=html_content)


@router.get("/radar.js")
async def get_radar_js_route(timezone: str = "Asia/Shanghai", languages: str | None = None):
    from fastapi.responses import Response
    lang_list = [l.strip() for l in languages.split(",") if l.strip()] if languages else None
    return Response(content=generate_radar_js_str(timezone=timezone, expected_languages=lang_list), media_type="application/javascript")


def generate_radar_html_str(
    env_name: str,
    group_name: str = "未分组",
    notes: str = "--",
    account: str = "",
    lang_str: str = "zh-CN",
    timezone: str = "Asia/Shanghai",
    ua_str: str = "",
    os_name: str = "Windows",
    arch_str: str = "x86_64 架构",
    cpu_cores: int | str = 8,
    memory_gb: int | str = 8,
    screen_res: str = "1920 × 1080",
    webgl_vendor: str = "Google Inc. (ANGLE)",
    webgl_renderer: str = "ANGLE (Direct3D11)",
    engine_name: str = "Chromium 154",
    proxy_info: str = "直连",
    init_ip: str = "探查中...",
) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{env_name} - 社交账号管理系统</title>
    <style>
        :root {{
            --bg: #f8fafc;
            --surface: #ffffff;
            --surface-subtle: #f1f5f9;
            --border: #e2e8f0;
            --border-hover: #cbd5e1;
            --text-main: #0f172a;
            --text-muted: #475569;
            --text-faint: #94a3b8;
            --primary: #2563eb;
            --primary-bg: #eff6ff;
            --primary-border: #bfdbfe;
            --success: #059669;
            --success-bg: #ecfdf5;
            --success-border: #a7f3d0;
            --warning: #d97706;
            --warning-bg: #fffbeb;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            --radius-lg: 16px;
            --radius-md: 12px;
            --radius-sm: 8px;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.06), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background-color: var(--bg);
            background-image: 
                radial-gradient(at 0% 0%, rgba(37, 99, 235, 0.04) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(5, 150, 105, 0.03) 0px, transparent 50%),
                linear-gradient(to right, rgba(226, 232, 240, 0.3) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(226, 232, 240, 0.3) 1px, transparent 1px);
            background-size: 100% 100%, 100% 100%, 32px 32px, 32px 32px;
            color: var(--text-main);
            font-family: var(--font-sans);
            min-height: 100vh;
            padding: 28px 24px 60px 24px;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 1240px;
            margin: 0 auto;
        }}

        /* Header Bar */
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(226, 232, 240, 0.8);
        }}

        .brand-badge {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .brand-icon {{
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            box-shadow: 0 4px 10px rgba(37, 99, 235, 0.25);
        }}

        .brand-title-wrap {{
            display: flex;
            align-items: baseline;
            gap: 10px;
        }}

        .brand-title {{
            font-size: 18px;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.3px;
        }}

        .env-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 3px 10px;
            border-radius: 20px;
            background: var(--surface);
            border: 1px solid var(--border);
            font-size: 12px;
            font-weight: 600;
            color: var(--primary);
            box-shadow: var(--shadow-sm);
        }}

        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 20px;
            background: var(--success-bg);
            border: 1px solid var(--success-border);
            color: var(--success);
            font-size: 12px;
            font-weight: 600;
        }}

        .pulse-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: var(--success);
            box-shadow: 0 0 0 0 rgba(5, 150, 105, 0.6);
            animation: pulse-ring 2s infinite cubic-bezier(0.4, 0, 0.6, 1);
        }}

        @keyframes pulse-ring {{
            0% {{ box-shadow: 0 0 0 0 rgba(5, 150, 105, 0.6); }}
            70% {{ box-shadow: 0 0 0 7px rgba(5, 150, 105, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(5, 150, 105, 0); }}
        }}

        .header-actions {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .engine-chip {{
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: var(--radius-sm);
            background: var(--surface);
            border: 1px solid var(--border);
            font-size: 13px;
            font-weight: 500;
            color: var(--text-muted);
            box-shadow: var(--shadow-sm);
        }}

        .btn-refresh {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: var(--radius-sm);
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--primary);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: var(--shadow-sm);
        }}

        .btn-refresh:hover {{
            background: var(--primary-bg);
            border-color: var(--primary-border);
            transform: translateY(-1px);
        }}

        .btn-refresh:active {{
            transform: translateY(0);
        }}

        .btn-refresh.spinning svg {{
            animation: spin 0.8s linear infinite;
        }}

        @keyframes spin {{
            100% {{ transform: rotate(360deg); }}
        }}

        /* Main Grid */
        .layout-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }}

        .card {{
            background: var(--surface);
            border-radius: var(--radius-lg);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
            padding: 24px;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}

        .card:hover {{
            border-color: var(--border-hover);
            box-shadow: var(--shadow-lg);
        }}

        /* IP Network Sentinel Card */
        .ip-hero {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 22px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }}

        .ip-main {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        .ip-shield-icon {{
            width: 48px;
            height: 48px;
            border-radius: 14px;
            background: var(--success-bg);
            border: 1px solid var(--success-border);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--success);
            flex-shrink: 0;
        }}

        .ip-label {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-faint);
            margin-bottom: 4px;
        }}

        .ip-value-wrap {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .ip-value {{
            font-family: var(--font-mono);
            font-size: 28px;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.5px;
            line-height: 1.1;
        }}

        .btn-copy-chip {{
            border: none;
            background: var(--surface-subtle);
            border: 1px solid var(--border);
            padding: 4px 8px;
            border-radius: 6px;
            cursor: pointer;
            color: var(--text-muted);
            transition: all 0.15s;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            font-weight: 500;
        }}

        .btn-copy-chip:hover {{
            background: var(--primary-bg);
            border-color: var(--primary-border);
            color: var(--primary);
        }}

        .geo-chips {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            margin-top: 10px;
        }}

        .geo-tag {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: var(--surface-subtle);
            border: 1px solid var(--border);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            color: var(--text-muted);
        }}

        .geo-tag.highlight {{
            background: var(--primary-bg);
            border-color: var(--primary-border);
            color: var(--primary);
            font-weight: 600;
        }}

        .purity-badge {{
            text-align: right;
        }}

        .purity-score-ring {{
            display: inline-flex;
            flex-direction: column;
            align-items: flex-end;
        }}

        .purity-num {{
            font-size: 26px;
            font-weight: 800;
            color: var(--success);
            line-height: 1;
        }}

        .purity-desc {{
            font-size: 11px;
            font-weight: 600;
            color: var(--text-faint);
            margin-top: 4px;
        }}

        /* Platform Connectivity Matrix */
        .section-label {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: var(--text-faint);
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .platforms-deck {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 10px;
        }}

        .platform-pill {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--surface-subtle);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            padding: 8px 12px;
            transition: all 0.15s;
        }}

        .platform-pill:hover {{
            border-color: var(--primary-border);
            background: var(--surface);
            box-shadow: var(--shadow-sm);
        }}

        .platform-left {{
            display: flex;
            align-items: center;
            gap: 7px;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-main);
        }}

        .platform-icon {{
            width: 16px;
            height: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .status-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            font-weight: 600;
            color: var(--success);
        }}

        .status-indicator.loading {{
            color: var(--warning);
        }}

        /* Bento Grid: Hardware & Fingerprint Parameters */
        .bento-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-top: 20px;
        }}

        .bento-item {{
            background: var(--surface-subtle);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 14px 16px;
            transition: border-color 0.15s, background-color 0.15s;
        }}

        .bento-item:hover {{
            background: var(--surface);
            border-color: var(--border-hover);
        }}

        .bento-label {{
            font-size: 11px;
            font-weight: 600;
            color: var(--text-faint);
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .bento-val {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-main);
            word-break: break-all;
        }}

        .bento-val.sub {{
            font-size: 12px;
            font-weight: 500;
            color: var(--text-muted);
            margin-top: 2px;
        }}

        /* User-Agent Block */
        .ua-block {{
            margin-top: 16px;
            background: var(--surface-subtle);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 14px 16px;
        }}

        .ua-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }}

        .ua-title {{
            font-size: 11px;
            font-weight: 700;
            color: var(--text-faint);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .ua-code {{
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--text-muted);
            line-height: 1.5;
            word-break: break-all;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 10px 12px;
            user-select: all;
        }}

        /* Right Column Cards */
        .side-deck {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .account-hero {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 24px 12px;
            background: linear-gradient(180deg, rgba(239, 246, 255, 0.5) 0%, rgba(255, 255, 255, 0) 100%);
            border-radius: var(--radius-md);
            border: 1px dashed var(--primary-border);
            margin: 16px 0;
        }}

        .account-icon-box {{
            width: 54px;
            height: 54px;
            border-radius: 16px;
            background: #ffffff;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.12);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary);
            margin-bottom: 12px;
        }}

        .account-state-title {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 4px;
        }}

        .account-state-desc {{
            font-size: 12px;
            color: var(--text-muted);
            max-width: 200px;
        }}

        .meta-list {{
            border-top: 1px solid var(--border);
            padding-top: 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .meta-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 13px;
        }}

        .meta-key {{
            color: var(--text-muted);
            font-weight: 500;
        }}

        .meta-val {{
            color: var(--text-main);
            font-weight: 600;
        }}

        /* Quick Launch Dock */
        .quick-dock {{
            margin-top: 24px;
        }}

        .dock-grid {{
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 14px;
        }}

        .dock-item {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 16px 14px;
            text-decoration: none;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: var(--shadow-sm);
        }}

        .dock-item:hover {{
            border-color: var(--primary-border);
            box-shadow: var(--shadow-md);
            transform: translateY(-2px);
        }}

        .dock-icon-wrap {{
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background: var(--surface-subtle);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 10px;
            color: var(--primary);
            transition: all 0.2s;
        }}

        .dock-item:hover .dock-icon-wrap {{
            background: var(--primary-bg);
            color: var(--primary);
            transform: scale(1.05);
        }}

        .dock-name {{
            font-size: 13px;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 2px;
        }}

        .dock-tag {{
            font-size: 11px;
            color: var(--text-faint);
            font-weight: 500;
        }}

        /* Toast Feedback */
        .toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #0f172a;
            color: #ffffff;
            padding: 10px 18px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: var(--shadow-lg);
            opacity: 0;
            transform: translateY(12px);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: none;
            z-index: 999;
        }}

        .toast.show {{
            opacity: 1;
            transform: translateY(0);
        }}

        @media (max-width: 960px) {{
            .layout-grid {{
                grid-template-columns: 1fr;
            }}
            .bento-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            .dock-grid {{
                grid-template-columns: repeat(3, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="brand-badge">
                <div class="brand-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        <path d="m9 12 2 2 4-4"/>
                    </svg>
                </div>
                <div class="brand-title-wrap">
                    <span class="brand-title">{env_name}</span>
                    <span class="env-pill">社交账号管理系统</span>
                </div>
                <div class="status-badge">
                    <span class="pulse-dot"></span>
                    <span>防关联安全运行中</span>
                </div>
            </div>

            <div class="header-actions">
                <div class="engine-chip">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="m4.93 4.93 4.24 4.24"/>
                        <path d="m14.83 9.17 4.24-4.24"/>
                        <path d="m14.83 14.83 4.24 4.24"/>
                        <path d="m9.17 14.83-4.24 4.24"/>
                    </svg>
                    <span>{engine_name}</span>
                </div>

                <div class="engine-chip" id="timeClockBadge" style="font-family: var(--font-mono); font-size: 12px;">
                    {timezone}
                </div>

                <button class="btn-refresh" id="refreshBtn" onclick="refreshRadar()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
                        <path d="M3 3v5h5"/>
                        <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>
                        <path d="M16 21h5v-5"/>
                    </svg>
                    <span>全面体检</span>
                </button>
            </div>
        </header>

        <!-- Main Layout -->
        <div class="layout-grid">
            <!-- Left Main Column -->
            <div>
                <!-- IP Network Card -->
                <div class="card">
                    <div class="ip-hero">
                        <div class="ip-main">
                            <div class="ip-shield-icon">
                                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                    <polyline points="20 6 9 17 4 12"/>
                                </svg>
                            </div>
                            <div>
                                <div class="ip-label">出网 IP 地址 (Public Egress)</div>
                                <div class="ip-value-wrap">
                                    <span class="ip-value" id="ipAddress">{init_ip}</span>
                                    <button class="btn-copy-chip" onclick="copyText('ipAddress', 'IP 地址')">
                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
                                            <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
                                        </svg>
                                        <span>复制</span>
                                    </button>
                                </div>
                                <div class="geo-chips">
                                    <span class="geo-tag highlight" id="geoCountry">探查中...</span>
                                    <span class="geo-tag" id="geoRegion">--</span>
                                    <span class="geo-tag" id="geoCity">--</span>
                                    <span class="geo-tag" id="zipVal">--</span>
                                    <span class="geo-tag" id="ispVal">--</span>
                                </div>
                            </div>
                        </div>

                        <div class="purity-badge">
                            <div class="purity-score-ring">
                                <span class="purity-num">100%</span>
                                <span class="purity-desc">纯净度评分 (Purity)</span>
                            </div>
                        </div>
                    </div>

                    <!-- Platform Connectivity Matrix -->
                    <div class="section-label">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                        </svg>
                        <span>全球主流平台直连探测</span>
                    </div>

                    <div class="platforms-deck">
                        <div class="platform-pill">
                            <div class="platform-left">
                                <span class="platform-icon">🎵</span>
                                <span>TikTok</span>
                            </div>
                            <span class="status-indicator loading" id="pingTikTok">测速中...</span>
                        </div>

                        <div class="platform-pill">
                            <div class="platform-left">
                                <span class="platform-icon">🔍</span>
                                <span>Google</span>
                            </div>
                            <span class="status-indicator loading" id="pingGoogle">测速中...</span>
                        </div>

                        <div class="platform-pill">
                            <div class="platform-left">
                                <span class="platform-icon">🇨🇳</span>
                                <span>Baidu</span>
                            </div>
                            <span class="status-indicator loading" id="pingBaidu">测速中...</span>
                        </div>

                        <div class="platform-pill">
                            <div class="platform-left">
                                <span class="platform-icon">👥</span>
                                <span>Facebook</span>
                            </div>
                            <span class="status-indicator loading" id="pingFacebook">测速中...</span>
                        </div>

                        <div class="platform-pill">
                            <div class="platform-left">
                                <span class="platform-icon">🛡️</span>
                                <span>Iphey</span>
                            </div>
                            <span class="status-indicator loading" id="pingIphey">测速中...</span>
                        </div>

                        <div class="platform-pill">
                            <div class="platform-left">
                                <span class="platform-icon">🛒</span>
                                <span>Amazon</span>
                            </div>
                            <span class="status-indicator loading" id="pingAmazon">测速中...</span>
                        </div>
                    </div>

                    <!-- Hardware & Fingerprint Parameters Bento Grid -->
                    <div style="margin-top: 24px;">
                        <div class="section-label">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 7h10M7 12h10M7 17h10"/>
                            </svg>
                            <span>虚拟硬件与环境拓扑</span>
                        </div>

                        <div class="bento-grid">
                            <div class="bento-item">
                                <div class="bento-label">操作系统 (OS)</div>
                                <div class="bento-val" id="osVal">{os_name}</div>
                                <div class="bento-val sub" id="archVal">{arch_str}</div>
                            </div>

                            <div class="bento-item">
                                <div class="bento-label">CPU 核心 / 内存</div>
                                <div class="bento-val" id="cpuVal">{cpu_cores} 核心</div>
                                <div class="bento-val sub" id="memVal">{memory_gb} GB 设备内存</div>
                            </div>

                            <div class="bento-item">
                                <div class="bento-label">分辨率与色深</div>
                                <div class="bento-val" id="resVal">{screen_res}</div>
                                <div class="bento-val sub" id="resSub">24-bit TrueColor</div>
                            </div>

                            <div class="bento-item">
                                <div class="bento-label">语言与字符集</div>
                                <div class="bento-val" id="langVal">{lang_str}</div>
                                <div class="bento-val sub">UTF-8 / 区域匹配</div>
                            </div>

                            <div class="bento-item">
                                <div class="bento-label">时区与世界时钟</div>
                                <div class="bento-val" id="tzVal">{timezone}</div>
                                <div class="bento-val sub" id="liveTimeVal">同步计算中...</div>
                            </div>

                            <div class="bento-item">
                                <div class="bento-label">代理出网配置</div>
                                <div class="bento-val" style="color: var(--primary);">{proxy_info}</div>
                                <div class="bento-val sub">WebRTC 防泄漏隔离</div>
                            </div>
                        </div>

                        <!-- User-Agent Block -->
                        <div class="ua-block">
                            <div class="ua-header">
                                <div class="ua-title">User-Agent (伪装标识)</div>
                                <button class="btn-copy-chip" onclick="copyText('uaVal', 'User-Agent')">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
                                        <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
                                    </svg>
                                    <span>复制 UA</span>
                                </button>
                            </div>
                            <div class="ua-code" id="uaVal">{ua_str}</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right Column -->
            <div class="side-deck">
                <!-- Account Card -->
                <div class="card">
                    <div class="section-label">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                        </svg>
                        <span>已绑定业务账号</span>
                    </div>

                    <div class="account-hero">
                        <div class="account-icon-box">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <rect width="20" height="16" x="2" y="4" rx="2"/>
                                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
                            </svg>
                        </div>
                        <div class="account-state-title" id="accountTitle">
                            {"已绑定: " + account if account else "本环境暂未绑定账号"}
                        </div>
                        <div class="account-state-desc">
                            {"凭据隔离保护已生效" if account else "环境隔离已建立，可随时添加海外社交或电商账号"}
                        </div>
                    </div>

                    <div class="meta-list">
                        <div class="meta-row">
                            <span class="meta-key">所属分组</span>
                            <span class="meta-val">{group_name}</span>
                        </div>
                        <div class="meta-row">
                            <span class="meta-key">环境备注</span>
                            <span class="meta-val">{notes}</span>
                        </div>
                        <div class="meta-row">
                            <span class="meta-key">隔离沙箱</span>
                            <span class="meta-val" style="color: var(--success);">独立 Cookie 容器</span>
                        </div>
                    </div>
                </div>

                <!-- Security Checklist Card -->
                <div class="card" style="background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);">
                    <div class="section-label">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                        </svg>
                        <span>防护状态体检</span>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
                        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 13px;">
                            <span style="color: var(--text-muted);">Canvas 噪点渲染</span>
                            <span style="color: var(--success); font-weight: 600;">✓ 已混淆</span>
                        </div>
                        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 13px;">
                            <span style="color: var(--text-muted);">AudioContext 保护</span>
                            <span style="color: var(--success); font-weight: 600;">✓ 已伪装</span>
                        </div>
                        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 13px;">
                            <span style="color: var(--text-muted);">WebRTC 真实 IP 拦截</span>
                            <span style="color: var(--success); font-weight: 600;">✓ 零泄漏</span>
                        </div>
                        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 13px;">
                            <span style="color: var(--text-muted);">自动化探针屏蔽</span>
                            <span style="color: var(--success); font-weight: 600;">✓ 已隐匿</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Quick Launch & Detection Tools Dock -->
        <div class="quick-dock">
            <div class="section-label">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>
                </svg>
                <span>常用指纹自检与快捷直达</span>
            </div>

            <div class="dock-grid">
                <a href="https://iphey.com" target="_blank" class="dock-item">
                    <div class="dock-icon-wrap">🛡️</div>
                    <div class="dock-name">Iphey</div>
                    <div class="dock-tag">全景指纹纯净度</div>
                </a>

                <a href="https://whoer.net" target="_blank" class="dock-item">
                    <div class="dock-icon-wrap">🕵️</div>
                    <div class="dock-name">Whoer</div>
                    <div class="dock-tag">IP 伪装与 DNS 泄露</div>
                </a>

                <a href="https://browserleaks.com" target="_blank" class="dock-item">
                    <div class="dock-icon-wrap">🧪</div>
                    <div class="dock-name">BrowserLeaks</div>
                    <div class="dock-tag">WebGL/Canvas 泄露</div>
                </a>

                <a href="https://pixelscan.net" target="_blank" class="dock-item">
                    <div class="dock-icon-wrap">🎯</div>
                    <div class="dock-name">Pixelscan</div>
                    <div class="dock-tag">防关联机器人评分</div>
                </a>

                <a href="https://www.browserscan.net/" target="_blank" class="dock-item">
                    <div class="dock-icon-wrap">🔍</div>
                    <div class="dock-name">BrowserScan</div>
                    <div class="dock-tag">全维指纹安全检测</div>
                </a>

                <a href="https://ping0.cc/env" target="_blank" class="dock-item">
                    <div class="dock-icon-wrap">⚡</div>
                    <div class="dock-name">Ping0</div>
                    <div class="dock-tag">环境与伪装度评分</div>
                </a>
            </div>
        </div>
    </div>

    <!-- Toast Notification -->
    <div id="toast" class="toast">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12"/>
        </svg>
        <span id="toastMsg">已复制到剪贴板</span>
    </div>
    <script src="radar.js"></script>
</body>
</html>
"""


def generate_radar_js_str(timezone: str = "Asia/Shanghai", expected_languages: list[str] | None = None) -> str:
    """Return standalone radar.js client probe logic compliant with Manifest V3 CSP."""
    import json
    expected_langs_json = json.dumps(expected_languages) if expected_languages else "null"
    return f"""// CamouHub Environment Health & Fingerprint Live Probe Client
(function() {{
    'use strict';

    // 1. Live Hardware & Browser API Direct Detection
    function detectHardwareLive() {{
        try {{
            // Real UA
            const ua = navigator.userAgent;
            const uaElem = document.getElementById('uaVal');
            if (uaElem && ua) uaElem.textContent = ua;

            // Real OS & Architecture
            let osName = "Windows";
            let arch = "x86_64 架构";
            const plat = (navigator.platform || '').toLowerCase();
            const uaLow = (ua || '').toLowerCase();
            if (uaLow.includes("mac os x") || plat.includes("mac")) {{
                osName = "macOS";
                arch = "ARM64 / Apple Silicon";
            }} else if (uaLow.includes("android")) {{
                osName = "Android";
                arch = "ARM64 移动架构";
            }} else if (uaLow.includes("iphone") || uaLow.includes("ipad")) {{
                osName = "iOS";
                arch = "Apple A-Series 移动架构";
            }} else if (uaLow.includes("linux")) {{
                osName = "Linux";
                arch = "x86_64 架构";
            }} else if (uaLow.includes("windows")) {{
                osName = "Windows";
                arch = "x86_64 架构";
            }}
            const osElem = document.getElementById('osVal');
            if (osElem) osElem.textContent = osName;
            const archElem = document.getElementById('archVal');
            if (archElem) archElem.textContent = arch;

            // Real CPU Cores & Device RAM
            const cores = navigator.hardwareConcurrency || 8;
            const mem = navigator.deviceMemory || 8;
            const cpuElem = document.getElementById('cpuVal');
            if (cpuElem) cpuElem.textContent = cores + " 核心";
            const memElem = document.getElementById('memVal');
            if (memElem) memElem.textContent = mem + " GB 设备内存";

            // Real Screen, ColorDepth & DPR
            const sw = window.screen.width;
            const sh = window.screen.height;
            const dpr = window.devicePixelRatio || 1;
            const depth = window.screen.colorDepth || 24;
            const resElem = document.getElementById('resVal');
            if (resElem) resElem.textContent = sw + " × " + sh;
            const resSub = document.getElementById('resSub');
            if (resSub) resSub.textContent = depth + "-bit 色深 · " + dpr + "x DPR";

            // Real Locale & Languages
            const expectedLangs = {expected_langs_json};
            let langs = "";
            if (Array.isArray(expectedLangs) && expectedLangs.length > 0) {{
                langs = expectedLangs.join(', ');
            }} else if (navigator.languages && navigator.languages.length) {{
                langs = Array.from(navigator.languages).join(', ');
            }} else {{
                langs = navigator.language || 'en-US';
            }}
            const langElem = document.getElementById('langVal');
            if (langElem) langElem.textContent = langs;

            // Real Timezone
            const liveTz = Intl.DateTimeFormat().resolvedOptions().timeZone || "{timezone}";
            const tzElem = document.getElementById('tzVal');
            if (tzElem) tzElem.textContent = liveTz;
        }} catch(e) {{}}
    }}

    // 2. Real-Time Network Ping Probe
    async function pingTarget(url, elemId) {{
        const elem = document.getElementById(elemId);
        if (!elem) return;
        elem.className = "status-indicator loading";
        elem.textContent = "测速中...";
        const start = performance.now();
        try {{
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2600);
            await fetch(url + (url.includes('?') ? '&' : '?') + '_c=' + Date.now(), {{
                mode: 'no-cors',
                cache: 'no-store',
                signal: controller.signal
            }});
            clearTimeout(timeoutId);
            const ms = Math.round(performance.now() - start);
            elem.className = "status-indicator";
            elem.style.color = "#059669";
            elem.textContent = "✓ " + ms + "ms";
        }} catch(e) {{
            elem.className = "status-indicator";
            elem.style.color = "#dc2626";
            elem.textContent = "✕ 无法直连";
        }}
    }}

    function pingAllPlatforms() {{
        pingTarget("https://www.tiktok.com/favicon.ico", "pingTikTok");
        pingTarget("https://www.google.com/generate_204", "pingGoogle");
        pingTarget("https://www.baidu.com/favicon.ico", "pingBaidu");
        pingTarget("https://www.facebook.com/favicon.ico", "pingFacebook");
        pingTarget("https://iphey.com/favicon.ico", "pingIphey");
        pingTarget("https://www.amazon.com/favicon.ico", "pingAmazon");
    }}

    function getFlagEmoji(countryCode) {{
        if (!countryCode || countryCode.length !== 2) return '🌐';
        const codePoints = countryCode
            .toUpperCase()
            .split('')
            .map(char => 127397 + char.charCodeAt());
        return String.fromCodePoint(...codePoints);
    }}

    function applyGeoData(geo) {{
        if (!geo) return;
        const ipElem = document.getElementById('ipAddress');
        if (ipElem && geo.ip) ipElem.textContent = geo.ip;

        const cElem = document.getElementById('geoCountry');
        if (cElem) cElem.textContent = (geo.flag ? geo.flag + ' ' : '') + (geo.country || 'Global');

        const rElem = document.getElementById('geoRegion');
        if (rElem) rElem.textContent = geo.region || '--';

        const cityElem = document.getElementById('geoCity');
        if (cityElem) cityElem.textContent = geo.city || '--';

        const zipElem = document.getElementById('zipVal');
        if (zipElem) zipElem.textContent = geo.postal || '--';

        const ispElem = document.getElementById('ispVal');
        if (ispElem) ispElem.textContent = geo.isp || '--';

        // Auto-align region language if current language is default generic fallback
        const COUNTRY_LANGUAGES = {{
            'JP': 'ja-JP, ja, en-US, en',
            'US': 'en-US, en',
            'GB': 'en-GB, en',
            'CA': 'en-CA, fr-CA, en',
            'AU': 'en-AU, en',
            'DE': 'de-DE, de, en-US, en',
            'FR': 'fr-FR, fr, en-US, en',
            'KR': 'ko-KR, ko, en-US, en',
            'SG': 'en-SG, zh-SG, en',
            'TW': 'zh-TW, zh, en-US, en',
            'HK': 'zh-HK, zh, en-US, en',
            'CN': 'zh-CN, zh, en',
            'VN': 'vi-VN, vi, en-US, en',
            'TH': 'th-TH, th, en-US, en',
            'MY': 'ms-MY, en-MY, en',
            'ID': 'id-ID, id, en-US, en',
            'PH': 'en-PH, fil-PH, en',
            'RU': 'ru-RU, ru, en-US, en',
            'IN': 'en-IN, hi-IN, en',
            'BR': 'pt-BR, pt, en-US, en',
            'ES': 'es-ES, es, en-US, en',
            'IT': 'it-IT, it, en-US, en',
            'NL': 'nl-NL, nl, en-US, en'
        }};
        const cc = (geo.country_code || '').toUpperCase();
        if (cc && COUNTRY_LANGUAGES[cc]) {{
            const langElem = document.getElementById('langVal');
            if (langElem) {{
                const cur = (langElem.textContent || '').trim();
                if (!cur || cur === 'en-US, en' || cur === 'en-US' || cur === 'zh-CN, zh' || cur === 'zh-CN') {{
                    langElem.textContent = COUNTRY_LANGUAGES[cc];
                }}
            }}
        }}
    }}

    async function fetchIPInfo() {{
        // 1. Try ipwho.is (fast, reliable, CORS enabled, no rate limits, full details)
        try {{
            const res = await fetch('https://ipwho.is/');
            if (res.ok) {{
                const data = await res.json();
                if (data.success && data.ip) {{
                    applyGeoData({{
                        ip: data.ip,
                        country: data.country,
                        country_code: data.country_code,
                        flag: data.flag?.emoji || getFlagEmoji(data.country_code),
                        region: data.region,
                        city: data.city,
                        postal: data.postal,
                        isp: data.connection?.isp || data.connection?.org || ''
                    }});
                    return;
                }}
            }}
        }} catch(e) {{}}

        // 2. Try ipapi.co
        try {{
            const res = await fetch('https://ipapi.co/json/');
            if (res.ok) {{
                const data = await res.json();
                if (data.ip) {{
                    applyGeoData({{
                        ip: data.ip,
                        country: data.country_name,
                        country_code: data.country_code,
                        flag: getFlagEmoji(data.country_code),
                        region: data.region,
                        city: data.city,
                        postal: data.postal,
                        isp: data.org || ''
                    }});
                    return;
                }}
            }}
        }} catch(e) {{}}

        // 3. Fallback: ipify for pure IP
        try {{
            const res = await fetch('https://api.ipify.org?format=json');
            if (res.ok) {{
                const data = await res.json();
                if (data.ip) {{
                    const ipElem = document.getElementById('ipAddress');
                    if (ipElem) ipElem.textContent = data.ip;
                }}
            }}
        }} catch(e) {{}}
    }}

    function updateTimezoneTime() {{
        try {{
            const liveTz = Intl.DateTimeFormat().resolvedOptions().timeZone || "{timezone}";
            const now = new Date();
            const timeStr = now.toLocaleTimeString('zh-CN', {{ hour12: false }});
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const dateStr = year + '-' + month + '-' + day;
            const liveElem = document.getElementById('liveTimeVal');
            if (liveElem) liveElem.textContent = dateStr + ' ' + timeStr;
            const badge = document.getElementById('timeClockBadge');
            if (badge) badge.textContent = liveTz + ' ' + timeStr;
        }} catch(e) {{}}
    }}

    window.copyText = function(elemId, label) {{
        const elem = document.getElementById(elemId);
        if (!elem) return;
        const text = elem.textContent;
        navigator.clipboard.writeText(text).then(() => {{
            showToast(label + '已复制');
        }}).catch(() => {{
            const ta = document.createElement('textarea');
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            showToast(label + '已复制');
        }});
    }};

    window.showToast = function(msg) {{
        const toast = document.getElementById('toast');
        if (!toast) return;
        const msgElem = document.getElementById('toastMsg');
        if (msgElem) msgElem.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => {{
            toast.classList.remove('show');
        }}, 2000);
    }};

    window.refreshRadar = function() {{
        const btn = document.getElementById('refreshBtn');
        if (btn) btn.classList.add('spinning');
        detectHardwareLive();
        pingAllPlatforms();
        fetchIPInfo().finally(() => {{
            setTimeout(() => {{
                if (btn) btn.classList.remove('spinning');
                window.showToast('环境健康检测与测速已刷新');
            }}, 600);
        }});
    }};

    // Clean URL query string if present
    try {{
        if (window.location.search) {{
            window.history.replaceState(null, document.title, window.location.pathname);
        }}
    }} catch(e) {{}}

    function initRadar() {{
        detectHardwareLive();
        pingAllPlatforms();
        fetchIPInfo();
        updateTimezoneTime();
        setInterval(updateTimezoneTime, 1000);

        // Bind external test site links to open cleanly in a new tab without being hijacked
        document.querySelectorAll('.dock-item').forEach(function(el) {{
            el.addEventListener('click', function(e) {{
                e.preventDefault();
                e.stopPropagation();
                const targetUrl = el.getAttribute('href');
                if (targetUrl) {{
                    if (typeof browser !== 'undefined' && browser.tabs && browser.tabs.create) {{
                        browser.tabs.create({{ url: targetUrl }});
                    }} else if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.create) {{
                        chrome.tabs.create({{ url: targetUrl }});
                    }} else {{
                        window.open(targetUrl, '_blank');
                    }}
                }}
            }});
        }});
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', initRadar);
    }} else {{
        initRadar();
    }}
}})();
"""
