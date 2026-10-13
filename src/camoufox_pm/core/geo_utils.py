"""Geolocation, country, timezone, and language mapping utilities.

Provides authentic language chains and timezone mappings for country codes
to ensure browser fingerprints naturally match outbound IP locations.
"""

from __future__ import annotations

from typing import Any

# Comprehensive map of ISO 3166-1 alpha-2 country codes to regional details.
COUNTRY_DATA: dict[str, dict[str, Any]] = {
    # 东亚
    "CN": {"name": "中国", "flag": "🇨🇳", "timezone": "Asia/Shanghai", "languages": ["zh-CN", "zh", "en-US", "en"], "locale": "zh_CN"},
    "HK": {"name": "中国香港", "flag": "🇭🇰", "timezone": "Asia/Hong_Kong", "languages": ["zh-HK", "zh-TW", "zh", "en-US", "en"], "locale": "zh_HK"},
    "TW": {"name": "中国台湾", "flag": "🇹🇼", "timezone": "Asia/Taipei", "languages": ["zh-TW", "zh-HK", "zh", "en-US", "en"], "locale": "zh_TW"},
    "MO": {"name": "中国澳门", "flag": "🇲🇴", "timezone": "Asia/Macau", "languages": ["zh-MO", "zh-HK", "zh", "en-US", "en"], "locale": "zh_MO"},
    "JP": {"name": "日本", "flag": "🇯🇵", "timezone": "Asia/Tokyo", "languages": ["ja-JP", "ja", "en-US", "en"], "locale": "ja_JP"},
    "KR": {"name": "韩国", "flag": "🇰🇷", "timezone": "Asia/Seoul", "languages": ["ko-KR", "ko", "en-US", "en"], "locale": "ko_KR"},

    # 东南亚
    "SG": {"name": "新加坡", "flag": "🇸🇬", "timezone": "Asia/Singapore", "languages": ["en-SG", "zh-SG", "zh-CN", "en"], "locale": "en_SG"},
    "MY": {"name": "马来西亚", "flag": "🇲🇾", "timezone": "Asia/Kuala_Lumpur", "languages": ["ms-MY", "en-MY", "zh-MY", "en"], "locale": "ms_MY"},
    "TH": {"name": "泰国", "flag": "🇹🇭", "timezone": "Asia/Bangkok", "languages": ["th-TH", "th", "en-US", "en"], "locale": "th_TH"},
    "VN": {"name": "越南", "flag": "🇻🇳", "timezone": "Asia/Ho_Chi_Minh", "languages": ["vi-VN", "vi", "en-US", "en"], "locale": "vi_VN"},
    "ID": {"name": "印度尼西亚", "flag": "🇮🇩", "timezone": "Asia/Jakarta", "languages": ["id-ID", "id", "en-US", "en"], "locale": "id_ID"},
    "PH": {"name": "菲律宾", "flag": "🇵🇭", "timezone": "Asia/Manila", "languages": ["en-PH", "fil-PH", "en-US", "en"], "locale": "en_PH"},

    # 北美与主要英语国家
    "US": {"name": "美国", "flag": "🇺🇸", "timezone": "America/New_York", "languages": ["en-US", "en"], "locale": "en_US"},
    "GB": {"name": "英国", "flag": "🇬🇧", "timezone": "Europe/London", "languages": ["en-GB", "en-US", "en"], "locale": "en_GB"},
    "UK": {"name": "英国", "flag": "🇬🇧", "timezone": "Europe/London", "languages": ["en-GB", "en-US", "en"], "locale": "en_GB"},
    "CA": {"name": "加拿大", "flag": "🇨🇦", "timezone": "America/Toronto", "languages": ["en-CA", "en-US", "fr-CA", "en"], "locale": "en_CA"},
    "AU": {"name": "澳大利亚", "flag": "🇦🇺", "timezone": "Australia/Sydney", "languages": ["en-AU", "en-GB", "en-US", "en"], "locale": "en_AU"},
    "NZ": {"name": "新西兰", "flag": "🇳🇿", "timezone": "Pacific/Auckland", "languages": ["en-NZ", "en-GB", "en-US", "en"], "locale": "en_NZ"},
    "IE": {"name": "爱尔兰", "flag": "🇮🇪", "timezone": "Europe/Dublin", "languages": ["en-IE", "en-GB", "en-US", "en"], "locale": "en_IE"},

    # 欧洲
    "DE": {"name": "德国", "flag": "🇩🇪", "timezone": "Europe/Berlin", "languages": ["de-DE", "de", "en-US", "en"], "locale": "de_DE"},
    "FR": {"name": "法国", "flag": "🇫🇷", "timezone": "Europe/Paris", "languages": ["fr-FR", "fr", "en-US", "en"], "locale": "fr_FR"},
    "RU": {"name": "俄罗斯", "flag": "🇷🇺", "timezone": "Europe/Moscow", "languages": ["ru-RU", "ru", "en-US", "en"], "locale": "ru_RU"},
    "UA": {"name": "乌克兰", "flag": "🇺🇦", "timezone": "Europe/Kyiv", "languages": ["uk-UA", "uk", "ru-RU", "en-US", "en"], "locale": "uk_UA"},
    "BY": {"name": "白俄罗斯", "flag": "🇧🇾", "timezone": "Europe/Minsk", "languages": ["be-BY", "ru-BY", "ru", "en-US", "en"], "locale": "be_BY"},
    "KZ": {"name": "哈萨克斯坦", "flag": "🇰🇿", "timezone": "Asia/Almaty", "languages": ["kk-KZ", "ru-KZ", "ru", "en-US", "en"], "locale": "kk_KZ"},
    "ES": {"name": "西班牙", "flag": "🇪🇸", "timezone": "Europe/Madrid", "languages": ["es-ES", "es", "en-US", "en"], "locale": "es_ES"},
    "IT": {"name": "意大利", "flag": "🇮🇹", "timezone": "Europe/Rome", "languages": ["it-IT", "it", "en-US", "en"], "locale": "it_IT"},
    "NL": {"name": "荷兰", "flag": "🇳🇱", "timezone": "Europe/Amsterdam", "languages": ["nl-NL", "nl", "en-US", "en"], "locale": "nl_NL"},
    "PL": {"name": "波兰", "flag": "🇵🇱", "timezone": "Europe/Warsaw", "languages": ["pl-PL", "pl", "en-US", "en"], "locale": "pl_PL"},
    "PT": {"name": "葡萄牙", "flag": "🇵🇹", "timezone": "Europe/Lisbon", "languages": ["pt-PT", "pt", "en-US", "en"], "locale": "pt_PT"},
    "SE": {"name": "瑞典", "flag": "🇸🇪", "timezone": "Europe/Stockholm", "languages": ["sv-SE", "sv", "en-US", "en"], "locale": "sv_SE"},
    "NO": {"name": "挪威", "flag": "🇳🇴", "timezone": "Europe/Oslo", "languages": ["nb-NO", "nn-NO", "en-US", "en"], "locale": "nb_NO"},
    "DK": {"name": "丹麦", "flag": "🇩🇰", "timezone": "Europe/Copenhagen", "languages": ["da-DK", "da", "en-US", "en"], "locale": "da_DK"},
    "FI": {"name": "芬兰", "flag": "🇫🇮", "timezone": "Europe/Helsinki", "languages": ["fi-FI", "fi", "en-US", "en"], "locale": "fi_FI"},
    "CH": {"name": "瑞士", "flag": "🇨🇭", "timezone": "Europe/Zurich", "languages": ["de-CH", "fr-CH", "it-CH", "en"], "locale": "de_CH"},
    "AT": {"name": "奥地利", "flag": "🇦🇹", "timezone": "Europe/Vienna", "languages": ["de-AT", "de", "en-US", "en"], "locale": "de_AT"},
    "CZ": {"name": "捷克", "flag": "🇨🇿", "timezone": "Europe/Prague", "languages": ["cs-CZ", "cs", "en-US", "en"], "locale": "cs_CZ"},
    "GR": {"name": "希腊", "flag": "🇬🇷", "timezone": "Europe/Athens", "languages": ["el-GR", "el", "en-US", "en"], "locale": "el_GR"},
    "RO": {"name": "罗马尼亚", "flag": "🇷🇴", "timezone": "Europe/Bucharest", "languages": ["ro-RO", "ro", "en-US", "en"], "locale": "ro_RO"},
    "HU": {"name": "匈牙利", "flag": "🇭🇺", "timezone": "Europe/Budapest", "languages": ["hu-HU", "hu", "en-US", "en"], "locale": "hu_HU"},
    "BE": {"name": "比利时", "flag": "🇧🇪", "timezone": "Europe/Brussels", "languages": ["nl-BE", "fr-BE", "en-US", "en"], "locale": "nl_BE"},

    # 拉美
    "BR": {"name": "巴西", "flag": "🇧🇷", "timezone": "America/Sao_Paulo", "languages": ["pt-BR", "pt", "en-US", "en"], "locale": "pt_BR"},
    "MX": {"name": "墨西哥", "flag": "🇲🇽", "timezone": "America/Mexico_City", "languages": ["es-MX", "es", "en-US", "en"], "locale": "es_MX"},
    "AR": {"name": "阿根廷", "flag": "🇦🇷", "timezone": "America/Argentina/Buenos_Aires", "languages": ["es-AR", "es", "en-US", "en"], "locale": "es_AR"},
    "CO": {"name": "哥伦比亚", "flag": "🇨🇴", "timezone": "America/Bogota", "languages": ["es-CO", "es", "en-US", "en"], "locale": "es_CO"},
    "CL": {"name": "智利", "flag": "🇨🇱", "timezone": "America/Santiago", "languages": ["es-CL", "es", "en-US", "en"], "locale": "es_CL"},
    "PE": {"name": "秘鲁", "flag": "🇵🇪", "timezone": "America/Lima", "languages": ["es-PE", "es", "en-US", "en"], "locale": "es_PE"},

    # 中东与南亚、非洲
    "TR": {"name": "土耳其", "flag": "🇹🇷", "timezone": "Europe/Istanbul", "languages": ["tr-TR", "tr", "en-US", "en"], "locale": "tr_TR"},
    "IN": {"name": "印度", "flag": "🇮🇳", "timezone": "Asia/Kolkata", "languages": ["en-IN", "hi-IN", "en-GB", "en"], "locale": "en_IN"},
    "PK": {"name": "巴基斯坦", "flag": "🇵🇰", "timezone": "Asia/Karachi", "languages": ["ur-PK", "en-PK", "en-US", "en"], "locale": "ur_PK"},
    "BD": {"name": "孟加拉国", "flag": "🇧🇩", "timezone": "Asia/Dhaka", "languages": ["bn-BD", "en-US", "en"], "locale": "bn_BD"},
    "AE": {"name": "阿联酋", "flag": "🇦🇪", "timezone": "Asia/Dubai", "languages": ["ar-AE", "ar", "en-US", "en"], "locale": "ar_AE"},
    "SA": {"name": "沙特阿拉伯", "flag": "🇸🇦", "timezone": "Asia/Riyadh", "languages": ["ar-SA", "ar", "en-US", "en"], "locale": "ar_SA"},
    "EG": {"name": "埃及", "flag": "🇪🇬", "timezone": "Africa/Cairo", "languages": ["ar-EG", "ar", "en-US", "en"], "locale": "ar_EG"},
    "IL": {"name": "以色列", "flag": "🇮🇱", "timezone": "Asia/Jerusalem", "languages": ["he-IL", "he", "en-US", "en"], "locale": "he_IL"},
    "ZA": {"name": "南非", "flag": "🇿🇦", "timezone": "Africa/Johannesburg", "languages": ["en-ZA", "en-GB", "en-US", "en"], "locale": "en_ZA"},
    "NG": {"name": "尼日利亚", "flag": "🇳🇬", "timezone": "Africa/Lagos", "languages": ["en-NG", "en-US", "en"], "locale": "en_NG"},
}

# Alias by common names or lowercase codes
_ALIASES: dict[str, str] = {
    "china": "CN",
    "japan": "JP",
    "united states": "US",
    "usa": "US",
    "united kingdom": "GB",
    "great britain": "GB",
    "germany": "DE",
    "france": "FR",
    "russia": "RU",
    "korea": "KR",
    "south korea": "KR",
    "taiwan": "TW",
    "hong kong": "HK",
    "singapore": "SG",
    "australia": "AU",
    "canada": "CA",
    "spain": "ES",
    "italy": "IT",
}


def normalize_country_code(code_or_name: str | None) -> str:
    """Normalize input country code or name to standard 2-letter uppercase ISO code."""
    if not code_or_name:
        return ""
    cleaned = code_or_name.strip()
    upper = cleaned.upper()
    if upper in COUNTRY_DATA:
        return upper
    lower = cleaned.lower()
    if lower in _ALIASES:
        return _ALIASES[lower]
    if len(cleaned) == 2 and cleaned.isalpha():
        return upper
    return ""


def get_languages_for_country(country_code: str | None) -> list[str]:
    """Return authentic Accept-Language chain for a given country code."""
    normalized = normalize_country_code(country_code)
    if normalized and normalized in COUNTRY_DATA:
        return list(COUNTRY_DATA[normalized]["languages"])
    if normalized and len(normalized) == 2:
        return [f"{normalized.lower()}-{normalized}", normalized.lower(), "en-US", "en"]
    return ["en-US", "en"]


def get_timezone_for_country(country_code: str | None) -> str:
    """Return default timezone name for a given country code."""
    normalized = normalize_country_code(country_code)
    if normalized and normalized in COUNTRY_DATA:
        return COUNTRY_DATA[normalized]["timezone"]
    return "UTC"


def get_locale_for_country(country_code: str | None) -> str:
    """Return standard locale for a given country code."""
    normalized = normalize_country_code(country_code)
    if normalized and normalized in COUNTRY_DATA:
        return COUNTRY_DATA[normalized]["locale"]
    return "en_US"


def get_country_info(country_code: str | None) -> dict[str, Any] | None:
    """Return full country info dictionary or None."""
    normalized = normalize_country_code(country_code)
    if normalized and normalized in COUNTRY_DATA:
        return dict(COUNTRY_DATA[normalized])
    return None
