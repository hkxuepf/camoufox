/**
 * Country code to authentic Accept-Language chains and timezone mappings.
 * Helps fingerprint browser profiles adapt naturally to outbound IP locations.
 */

export interface CountryGeoProfile {
  name: string
  flag: string
  timezone: string
  languages: string[]
}

export const COUNTRY_PROFILES: Record<string, CountryGeoProfile> = {
  // 东亚
  CN: { name: '中国', flag: '🇨🇳', timezone: 'Asia/Shanghai', languages: ['zh-CN', 'zh', 'en-US', 'en'] },
  HK: { name: '中国香港', flag: '🇭🇰', timezone: 'Asia/Hong_Kong', languages: ['zh-HK', 'zh-TW', 'zh', 'en-US', 'en'] },
  TW: { name: '中国台湾', flag: '🇹🇼', timezone: 'Asia/Taipei', languages: ['zh-TW', 'zh-HK', 'zh', 'en-US', 'en'] },
  MO: { name: '中国澳门', flag: '🇲🇴', timezone: 'Asia/Macau', languages: ['zh-MO', 'zh-HK', 'zh', 'en-US', 'en'] },
  JP: { name: '日本', flag: '🇯🇵', timezone: 'Asia/Tokyo', languages: ['ja-JP', 'ja', 'en-US', 'en'] },
  KR: { name: '韩国', flag: '🇰🇷', timezone: 'Asia/Seoul', languages: ['ko-KR', 'ko', 'en-US', 'en'] },

  // 东南亚
  SG: { name: '新加坡', flag: '🇸🇬', timezone: 'Asia/Singapore', languages: ['en-SG', 'zh-SG', 'zh-CN', 'en'] },
  MY: { name: '马来西亚', flag: '🇲🇾', timezone: 'Asia/Kuala_Lumpur', languages: ['ms-MY', 'en-MY', 'zh-MY', 'en'] },
  TH: { name: '泰国', flag: '🇹🇭', timezone: 'Asia/Bangkok', languages: ['th-TH', 'th', 'en-US', 'en'] },
  VN: { name: '越南', flag: '🇻🇳', timezone: 'Asia/Ho_Chi_Minh', languages: ['vi-VN', 'vi', 'en-US', 'en'] },
  ID: { name: '印度尼西亚', flag: '🇮🇩', timezone: 'Asia/Jakarta', languages: ['id-ID', 'id', 'en-US', 'en'] },
  PH: { name: '菲律宾', flag: '🇵🇭', timezone: 'Asia/Manila', languages: ['en-PH', 'fil-PH', 'en-US', 'en'] },

  // 北美与主要英语国家
  US: { name: '美国', flag: '🇺🇸', timezone: 'America/New_York', languages: ['en-US', 'en'] },
  GB: { name: '英国', flag: '🇬🇧', timezone: 'Europe/London', languages: ['en-GB', 'en-US', 'en'] },
  UK: { name: '英国', flag: '🇬🇧', timezone: 'Europe/London', languages: ['en-GB', 'en-US', 'en'] },
  CA: { name: '加拿大', flag: '🇨🇦', timezone: 'America/Toronto', languages: ['en-CA', 'en-US', 'fr-CA', 'en'] },
  AU: { name: '澳大利亚', flag: '🇦🇺', timezone: 'Australia/Sydney', languages: ['en-AU', 'en-GB', 'en-US', 'en'] },
  NZ: { name: '新西兰', flag: '🇳🇿', timezone: 'Pacific/Auckland', languages: ['en-NZ', 'en-GB', 'en-US', 'en'] },
  IE: { name: '爱尔兰', flag: '🇮🇪', timezone: 'Europe/Dublin', languages: ['en-IE', 'en-GB', 'en-US', 'en'] },

  // 欧洲
  DE: { name: '德国', flag: '🇩🇪', timezone: 'Europe/Berlin', languages: ['de-DE', 'de', 'en-US', 'en'] },
  FR: { name: '法国', flag: '🇫🇷', timezone: 'Europe/Paris', languages: ['fr-FR', 'fr', 'en-US', 'en'] },
  RU: { name: '俄罗斯', flag: '🇷🇺', timezone: 'Europe/Moscow', languages: ['ru-RU', 'ru', 'en-US', 'en'] },
  UA: { name: '乌克兰', flag: '🇺🇦', timezone: 'Europe/Kyiv', languages: ['uk-UA', 'uk', 'ru-RU', 'en-US', 'en'] },
  BY: { name: '白俄罗斯', flag: '🇧🇾', timezone: 'Europe/Minsk', languages: ['be-BY', 'ru-BY', 'ru', 'en-US', 'en'] },
  KZ: { name: '哈萨克斯坦', flag: '🇰🇿', timezone: 'Asia/Almaty', languages: ['kk-KZ', 'ru-KZ', 'ru', 'en-US', 'en'] },
  ES: { name: '西班牙', flag: '🇪🇸', timezone: 'Europe/Madrid', languages: ['es-ES', 'es', 'en-US', 'en'] },
  IT: { name: '意大利', flag: '🇮🇹', timezone: 'Europe/Rome', languages: ['it-IT', 'it', 'en-US', 'en'] },
  NL: { name: '荷兰', flag: '🇳🇱', timezone: 'Europe/Amsterdam', languages: ['nl-NL', 'nl', 'en-US', 'en'] },
  PL: { name: '波兰', flag: '🇵🇱', timezone: 'Europe/Warsaw', languages: ['pl-PL', 'pl', 'en-US', 'en'] },
  PT: { name: '葡萄牙', flag: '🇵🇹', timezone: 'Europe/Lisbon', languages: ['pt-PT', 'pt', 'en-US', 'en'] },
  SE: { name: '瑞典', flag: '🇸🇪', timezone: 'Europe/Stockholm', languages: ['sv-SE', 'sv', 'en-US', 'en'] },
  NO: { name: '挪威', flag: '🇳🇴', timezone: 'Europe/Oslo', languages: ['nb-NO', 'nn-NO', 'en-US', 'en'] },
  DK: { name: '丹麦', flag: '🇩🇰', timezone: 'Europe/Copenhagen', languages: ['da-DK', 'da', 'en-US', 'en'] },
  FI: { name: '芬兰', flag: '🇫🇮', timezone: 'Europe/Helsinki', languages: ['fi-FI', 'fi', 'en-US', 'en'] },
  CH: { name: '瑞士', flag: '🇨🇭', timezone: 'Europe/Zurich', languages: ['de-CH', 'fr-CH', 'it-CH', 'en'] },
  AT: { name: '奥地利', flag: '🇦🇹', timezone: 'Europe/Vienna', languages: ['de-AT', 'de', 'en-US', 'en'] },
  CZ: { name: '捷克', flag: '🇨🇿', timezone: 'Europe/Prague', languages: ['cs-CZ', 'cs', 'en-US', 'en'] },
  GR: { name: '希腊', flag: '🇬🇷', timezone: 'Europe/Athens', languages: ['el-GR', 'el', 'en-US', 'en'] },
  RO: { name: '罗马尼亚', flag: '🇷🇴', timezone: 'Europe/Bucharest', languages: ['ro-RO', 'ro', 'en-US', 'en'] },
  HU: { name: '匈牙利', flag: '🇭🇺', timezone: 'Europe/Budapest', languages: ['hu-HU', 'hu', 'en-US', 'en'] },
  BE: { name: '比利时', flag: '🇧🇪', timezone: 'Europe/Brussels', languages: ['nl-BE', 'fr-BE', 'en-US', 'en'] },

  // 拉美
  BR: { name: '巴西', flag: '🇧🇷', timezone: 'America/Sao_Paulo', languages: ['pt-BR', 'pt', 'en-US', 'en'] },
  MX: { name: '墨西哥', flag: '🇲🇽', timezone: 'America/Mexico_City', languages: ['es-MX', 'es', 'en-US', 'en'] },
  AR: { name: '阿根廷', flag: '🇦🇷', timezone: 'America/Argentina/Buenos_Aires', languages: ['es-AR', 'es', 'en-US', 'en'] },
  CO: { name: '哥伦比亚', flag: '🇨🇴', timezone: 'America/Bogota', languages: ['es-CO', 'es', 'en-US', 'en'] },
  CL: { name: '智利', flag: '🇨🇱', timezone: 'America/Santiago', languages: ['es-CL', 'es', 'en-US', 'en'] },
  PE: { name: '秘鲁', flag: '🇵🇪', timezone: 'America/Lima', languages: ['es-PE', 'es', 'en-US', 'en'] },

  // 中东与南亚、非洲
  TR: { name: '土耳其', flag: '🇹🇷', timezone: 'Europe/Istanbul', languages: ['tr-TR', 'tr', 'en-US', 'en'] },
  IN: { name: '印度', flag: '🇮🇳', timezone: 'Asia/Kolkata', languages: ['en-IN', 'hi-IN', 'en-GB', 'en'] },
  PK: { name: '巴基斯坦', flag: '🇵🇰', timezone: 'Asia/Karachi', languages: ['ur-PK', 'en-PK', 'en-US', 'en'] },
  BD: { name: '孟加拉国', flag: '🇧🇩', timezone: 'Asia/Dhaka', languages: ['bn-BD', 'en-US', 'en'] },
  AE: { name: '阿联酋', flag: '🇦🇪', timezone: 'Asia/Dubai', languages: ['ar-AE', 'ar', 'en-US', 'en'] },
  SA: { name: '沙特阿拉伯', flag: '🇸🇦', timezone: 'Asia/Riyadh', languages: ['ar-SA', 'ar', 'en-US', 'en'] },
  EG: { name: '埃及', flag: '🇪🇬', timezone: 'Africa/Cairo', languages: ['ar-EG', 'ar', 'en-US', 'en'] },
  IL: { name: '以色列', flag: '🇮🇱', timezone: 'Asia/Jerusalem', languages: ['he-IL', 'he', 'en-US', 'en'] },
  ZA: { name: '南非', flag: '🇿🇦', timezone: 'Africa/Johannesburg', languages: ['en-ZA', 'en-GB', 'en-US', 'en'] },
  NG: { name: '尼日利亚', flag: '🇳🇬', timezone: 'Africa/Lagos', languages: ['en-NG', 'en-US', 'en'] },
}

export function getLanguagesForCountry(countryCode?: string | null): string[] {
  if (!countryCode) return ['en-US', 'en']
  const upper = countryCode.trim().toUpperCase()
  if (COUNTRY_PROFILES[upper]) {
    return COUNTRY_PROFILES[upper].languages
  }
  if (upper.length === 2) {
    const lower = upper.toLowerCase()
    return [`${lower}-${upper}`, lower, 'en-US', 'en']
  }
  return ['en-US', 'en']
}

export function getTimezoneForCountry(countryCode?: string | null): string {
  if (!countryCode) return 'UTC'
  const upper = countryCode.trim().toUpperCase()
  return COUNTRY_PROFILES[upper]?.timezone || 'UTC'
}

export function getCountryProfile(countryCode?: string | null): CountryGeoProfile | null {
  if (!countryCode) return null
  const upper = countryCode.trim().toUpperCase()
  return COUNTRY_PROFILES[upper] || null
}
