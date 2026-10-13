"""Preset extension definitions and self-contained vector icons.

Provides embedded base64 SVG icons so that presets display crystal-clear icons
offline without relying on third-party CDNs that can return 404/hotlink errors.
"""

import base64

def _svg_to_data_uri(svg_xml: str) -> str:
    encoded = base64.b64encode(svg_xml.strip().encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"

PRESET_ICONS = {
    "metamask": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#FFF6EB"/>
  <path fill="#E2761B" d="M54 18l-5-12-16 10 13 10z"/>
  <path fill="#E4761B" d="M10 18l5-12 16 10-13 10z"/>
  <path fill="#E4761B" d="M48 42l-13 14 17-4z"/>
  <path fill="#E4761B" d="M16 42l13 14-17-4z"/>
  <path fill="#CD6116" d="M44 26L32 17 20 26l4 18 8 5 8-5z"/>
  <circle cx="25" cy="33" r="3" fill="#161616"/>
  <circle cx="39" cy="33" r="3" fill="#161616"/>
  <ellipse cx="32" cy="41" rx="4" ry="2" fill="#D7C1B3"/>
</svg>
"""),

    "okx-wallet": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#000000"/>
  <rect x="15" y="15" width="14" height="14" rx="3" fill="#FFFFFF"/>
  <rect x="35" y="15" width="14" height="14" rx="3" fill="#FFFFFF"/>
  <rect x="25" y="25" width="14" height="14" rx="3" fill="#FFFFFF"/>
  <rect x="15" y="35" width="14" height="14" rx="3" fill="#FFFFFF"/>
  <rect x="35" y="35" width="14" height="14" rx="3" fill="#FFFFFF"/>
</svg>
"""),

    "phantom": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#AB9FF2"/>
  <path fill="#4F46E5" d="M16 34c0-8.8 7.2-16 16-16s16 7.2 16 16v12c0 1.5-1.5 2.5-2.8 1.8L39 40l-7 7-7-7-6.2 3.8C17.5 48.5 16 47.5 16 46V34z"/>
  <circle cx="27" cy="32" r="3.5" fill="#FFFFFF"/>
  <circle cx="37" cy="32" r="3.5" fill="#FFFFFF"/>
</svg>
"""),

    "rabby-wallet": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#8697FF"/>
  <ellipse cx="32" cy="38" rx="16" ry="13" fill="#FFFFFF"/>
  <ellipse cx="24" cy="20" rx="5" ry="12" fill="#FFFFFF"/>
  <ellipse cx="40" cy="20" rx="5" ry="12" fill="#FFFFFF"/>
  <ellipse cx="24" cy="20" rx="2.5" ry="8" fill="#FFB3C6"/>
  <ellipse cx="40" cy="20" rx="2.5" ry="8" fill="#FFB3C6"/>
  <circle cx="26" cy="35" r="2.5" fill="#222222"/>
  <circle cx="38" cy="35" r="2.5" fill="#222222"/>
  <ellipse cx="32" cy="41" rx="2.5" ry="1.5" fill="#FF6B8B"/>
</svg>
"""),

    "tronlink": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#FF0018"/>
  <path fill="#FFFFFF" d="M16 16l32 4-18 28-14-32zm4 7l9 20 12-19-21-1z"/>
  <path fill="#FFFFFF" d="M29 43l19-23-2 16-17 7z"/>
</svg>
"""),

    "google-translate": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#1A73E8"/>
  <rect x="10" y="14" width="28" height="28" rx="6" fill="#4285F4"/>
  <text x="24" y="34" fill="#FFFFFF" font-size="18" font-family="Arial, sans-serif" font-weight="bold" text-anchor="middle">G</text>
  <rect x="26" y="22" width="28" height="28" rx="6" fill="#FFFFFF"/>
  <text x="40" y="42" fill="#1A73E8" font-size="18" font-family="Arial, sans-serif" font-weight="bold" text-anchor="middle">文</text>
</svg>
"""),

    "tampermonkey": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#1E293B"/>
  <rect x="14" y="14" width="36" height="36" rx="8" fill="#0F172A" stroke="#334155" stroke-width="2"/>
  <circle cx="25" cy="30" r="5" fill="#FFFFFF"/>
  <circle cx="39" cy="30" r="5" fill="#FFFFFF"/>
  <circle cx="25" cy="30" r="2.5" fill="#000000"/>
  <circle cx="39" cy="30" r="2.5" fill="#000000"/>
  <path d="M23 41c2 3 5 4 9 4s7-1 9-4" stroke="#EF4444" stroke-width="3" stroke-linecap="round" fill="none"/>
</svg>
"""),

    "authenticator": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#0284C7"/>
  <circle cx="32" cy="32" r="20" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-dasharray="95 20"/>
  <rect x="28" y="16" width="8" height="5" rx="2" fill="#FFFFFF"/>
  <circle cx="32" cy="32" r="7" fill="#FFFFFF"/>
  <rect x="30" y="32" width="4" height="9" rx="1" fill="#FFFFFF"/>
</svg>
"""),

    "switchyomega": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#0284C7"/>
  <circle cx="32" cy="32" r="18" fill="none" stroke="#38BDF8" stroke-width="4"/>
  <circle cx="32" cy="14" r="6" fill="#38BDF8"/>
  <circle cx="48" cy="40" r="6" fill="#38BDF8"/>
  <circle cx="16" cy="40" r="6" fill="#38BDF8"/>
  <path d="M32 20v12l10 6" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" fill="none"/>
</svg>
"""),

    "cookie-editor": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#FFFBEB"/>
  <circle cx="32" cy="32" r="21" fill="#D97706"/>
  <circle cx="25" cy="24" r="3.5" fill="#78350F"/>
  <circle cx="39" cy="26" r="3" fill="#78350F"/>
  <circle cx="30" cy="34" r="2.5" fill="#78350F"/>
  <circle cx="23" cy="40" r="3" fill="#78350F"/>
  <circle cx="41" cy="38" r="3.5" fill="#78350F"/>
</svg>
"""),

    "ublock-origin": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#881337"/>
  <path fill="#FFFFFF" d="M32 14l16 6v14c0 10-6.8 19.3-16 22-9.2-2.7-16-12-16-22V20l16-6z"/>
  <text x="32" y="41" fill="#881337" font-size="20" font-family="Arial, sans-serif" font-weight="900" text-anchor="middle">uo</text>
</svg>
"""),

    "lastpass": _svg_to_data_uri("""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#DC2626"/>
  <circle cx="20" cy="32" r="4" fill="#FFFFFF"/>
  <circle cx="32" cy="32" r="4" fill="#FFFFFF"/>
  <circle cx="44" cy="32" r="4" fill="#FFFFFF"/>
  <rect x="48" y="16" width="3" height="8" rx="1.5" fill="#FFFFFF" transform="rotate(45 49.5 20)"/>
  <rect x="48" y="16" width="3" height="8" rx="1.5" fill="#FFFFFF" transform="rotate(-45 49.5 20)"/>
</svg>
"""),
}

# 12 Curated Preset Extensions with valid CRX IDs and embedded vector icons
PRESET_CATALOG = [
    {
        "id": "metamask",
        "name": "MetaMask",
        "version": "12.9.3",
        "icon_url": PRESET_ICONS["metamask"],
        "description": "全球最流行的以太坊及 EVM Web3 加密钱包",
        "category": "crypto",
        "crx_id": "nkbihfbeogaeaoehlefnkodbefgpgknn",
        "is_preset": 1,
    },
    {
        "id": "okx-wallet",
        "name": "OKX Wallet",
        "version": "3.18.0",
        "icon_url": PRESET_ICONS["okx-wallet"],
        "description": "OKX Web3 多链钱包，支持 80+ 公链与 DApp 交互",
        "category": "crypto",
        "crx_id": "mcohilncbfahbmgdjkbpemcciiolgcge",
        "is_preset": 1,
    },
    {
        "id": "phantom",
        "name": "Phantom",
        "version": "24.26.0",
        "icon_url": PRESET_ICONS["phantom"],
        "description": "Solana、Bitcoin 与以太坊生态友好的多链钱包",
        "category": "crypto",
        "crx_id": "bfnaelmomeimhlpmgjnjophhpkkoljpa",
        "is_preset": 1,
    },
    {
        "id": "rabby-wallet",
        "name": "Rabby Wallet",
        "version": "0.92.8",
        "icon_url": PRESET_ICONS["rabby-wallet"],
        "description": "DeBank 打造的 EVM 多链游戏与交易安全钱包，内置安全防钓鱼检测",
        "category": "crypto",
        "crx_id": "acmacodkjbdgmoleebolmdjonilkdbch",
        "is_preset": 1,
    },
    {
        "id": "tronlink",
        "name": "TronLink 波场钱包",
        "version": "4.1.5",
        "icon_url": PRESET_ICONS["tronlink"],
        "description": "波场 TRON 官方推荐插件钱包，支持 TRX 与 TRC20 转账与合约交互",
        "category": "crypto",
        "crx_id": "ibnejdfjmmkpcnlpebklmnkoeoihofec",
        "is_preset": 1,
    },
    {
        "id": "tampermonkey",
        "name": "Tampermonkey 篡改猴",
        "version": "5.3.3",
        "icon_url": PRESET_ICONS["tampermonkey"],
        "description": "强大的浏览器用户脚本管理器，自定义网页功能与自动化神器",
        "category": "tool",
        "crx_id": "dhdgffkkebhmkfjojejmpbldmpobfkfo",
        "is_preset": 1,
    },
    {
        "id": "google-translate",
        "name": "Google 翻译",
        "version": "2.0.17",
        "icon_url": PRESET_ICONS["google-translate"],
        "description": "浏览网页时一键划词翻译或整页翻译",
        "category": "tool",
        "crx_id": "aapbdbdomjkkjkaonfhkkikfgjllcleb",
        "is_preset": 1,
    },
    {
        "id": "authenticator",
        "name": "2FA Authenticator",
        "version": "7.0.2",
        "icon_url": PRESET_ICONS["authenticator"],
        "description": "双重身份验证 (2FA / OTP) 浏览器生成器，跨境出海多账号必备",
        "category": "tool",
        "crx_id": "bhghoamapcdpbohphigoooaddinpkbai",
        "is_preset": 1,
    },
    {
        "id": "switchyomega",
        "name": "Proxy SwitchyOmega 3",
        "version": "3.5.2",
        "icon_url": PRESET_ICONS["switchyomega"],
        "description": "轻松快捷地管理和切换多个代理服务器设置 (ZeroOmega MV3)",
        "category": "proxy",
        "crx_id": "pfnededegaaopdmhkdmcofjmoldfiped",
        "is_preset": 1,
    },
    {
        "id": "cookie-editor",
        "name": "Cookie-Editor",
        "version": "1.13.0",
        "icon_url": PRESET_ICONS["cookie-editor"],
        "description": "快速查看、编辑、导入与导出当前标签页的 Cookies",
        "category": "tool",
        "crx_id": "hlkenndednhfkekhgcdicdfddnkalmdm",
        "is_preset": 1,
    },
    {
        "id": "ublock-origin",
        "name": "uBlock Origin Lite",
        "version": "2026.10.12",
        "icon_url": PRESET_ICONS["ublock-origin"],
        "description": "高效轻量的网页广告、跟踪器与恶意弹窗拦截神器 (MV3 官方适配)",
        "category": "tool",
        "crx_id": "ddkjiahejlhfcafbddmgiahcphecmpfh",
        "is_preset": 1,
    },
    {
        "id": "lastpass",
        "name": "LastPass 密码管理",
        "version": "4.156.0",
        "icon_url": PRESET_ICONS["lastpass"],
        "description": "安全的密码管理工具，多平台同步与多账号一键自动填充",
        "category": "tool",
        "crx_id": "hdokiejnpimakedhajhdlcegeplioahd",
        "is_preset": 1,
    },
]
