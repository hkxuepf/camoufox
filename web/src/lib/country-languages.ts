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
  CN: { name: '中国', flag: '🇨🇳', timezone: 'Asia/Shanghai', languages: ['zh-CN', 'zh'] },
  HK: { name: '中国香港', flag: '🇭🇰', timezone: 'Asia/Hong_Kong', languages: ['zh-HK', 'zh-TW', 'zh'] },
  TW: { name: '中国台湾', flag: '🇹🇼', timezone: 'Asia/Taipei', languages: ['zh-TW', 'zh-HK', 'zh'] },
  MO: { name: '中国澳门', flag: '🇲🇴', timezone: 'Asia/Macau', languages: ['zh-MO', 'zh-HK', 'zh'] },
  JP: { name: '日本', flag: '🇯🇵', timezone: 'Asia/Tokyo', languages: ['ja', 'ja-JP'] },
  KR: { name: '韩国', flag: '🇰🇷', timezone: 'Asia/Seoul', languages: ['ko-KR', 'ko'] },

  // 东南亚
  SG: { name: '新加坡', flag: '🇸🇬', timezone: 'Asia/Singapore', languages: ['en-SG', 'zh-SG', 'en'] },
  MY: { name: '马来西亚', flag: '🇲🇾', timezone: 'Asia/Kuala_Lumpur', languages: ['ms-MY', 'en-MY', 'ms'] },
  TH: { name: '泰国', flag: '🇹🇭', timezone: 'Asia/Bangkok', languages: ['th-TH', 'th'] },
  VN: { name: '越南', flag: '🇻🇳', timezone: 'Asia/Ho_Chi_Minh', languages: ['vi-VN', 'vi'] },
  ID: { name: '印度尼西亚', flag: '🇮🇩', timezone: 'Asia/Jakarta', languages: ['id-ID', 'id'] },
  PH: { name: '菲律宾', flag: '🇵🇭', timezone: 'Asia/Manila', languages: ['en-PH', 'fil-PH', 'en'] },

  // 北美与主要英语国家
  US: { name: '美国', flag: '🇺🇸', timezone: 'America/New_York', languages: ['en-US', 'en'] },
  GB: { name: '英国', flag: '🇬🇧', timezone: 'Europe/London', languages: ['en-GB', 'en-US', 'en'] },
  UK: { name: '英国', flag: '🇬🇧', timezone: 'Europe/London', languages: ['en-GB', 'en-US', 'en'] },
  CA: { name: '加拿大', flag: '🇨🇦', timezone: 'America/Toronto', languages: ['en-CA', 'en-US', 'fr-CA', 'en'] },
  AU: { name: '澳大利亚', flag: '🇦🇺', timezone: 'Australia/Sydney', languages: ['en-AU', 'en-GB', 'en'] },
  NZ: { name: '新西兰', flag: '🇳🇿', timezone: 'Pacific/Auckland', languages: ['en-NZ', 'en-GB', 'en'] },
  IE: { name: '爱尔兰', flag: '🇮🇪', timezone: 'Europe/Dublin', languages: ['en-IE', 'en-GB', 'en'] },

  // 欧洲
  DE: { name: '德国', flag: '🇩🇪', timezone: 'Europe/Berlin', languages: ['de-DE', 'de'] },
  FR: { name: '法国', flag: '🇫🇷', timezone: 'Europe/Paris', languages: ['fr-FR', 'fr'] },
  RU: { name: '俄罗斯', flag: '🇷🇺', timezone: 'Europe/Moscow', languages: ['ru-RU', 'ru'] },
  UA: { name: '乌克兰', flag: '🇺🇦', timezone: 'Europe/Kyiv', languages: ['uk-UA', 'uk'] },
  BY: { name: '白俄罗斯', flag: '🇧🇾', timezone: 'Europe/Minsk', languages: ['be-BY', 'ru-BY', 'ru'] },
  KZ: { name: '哈萨克斯坦', flag: '🇰🇿', timezone: 'Asia/Almaty', languages: ['kk-KZ', 'ru-KZ', 'ru'] },
  ES: { name: '西班牙', flag: '🇪🇸', timezone: 'Europe/Madrid', languages: ['es-ES', 'es'] },
  IT: { name: '意大利', flag: '🇮🇹', timezone: 'Europe/Rome', languages: ['it-IT', 'it'] },
  NL: { name: '荷兰', flag: '🇳🇱', timezone: 'Europe/Amsterdam', languages: ['nl-NL', 'nl'] },
  PL: { name: '波兰', flag: '🇵🇱', timezone: 'Europe/Warsaw', languages: ['pl-PL', 'pl'] },
  PT: { name: '葡萄牙', flag: '🇵🇹', timezone: 'Europe/Lisbon', languages: ['pt-PT', 'pt'] },
  SE: { name: '瑞典', flag: '🇸🇪', timezone: 'Europe/Stockholm', languages: ['sv-SE', 'sv'] },
  NO: { name: '挪威', flag: '🇳🇴', timezone: 'Europe/Oslo', languages: ['nb-NO', 'nn-NO', 'no'] },
  DK: { name: '丹麦', flag: '🇩🇰', timezone: 'Europe/Copenhagen', languages: ['da-DK', 'da'] },
  FI: { name: '芬兰', flag: '🇫🇮', timezone: 'Europe/Helsinki', languages: ['fi-FI', 'fi'] },
  CH: { name: '瑞士', flag: '🇨🇭', timezone: 'Europe/Zurich', languages: ['de-CH', 'fr-CH', 'it-CH'] },
  AT: { name: '奥地利', flag: '🇦🇹', timezone: 'Europe/Vienna', languages: ['de-AT', 'de'] },
  CZ: { name: '捷克', flag: '🇨🇿', timezone: 'Europe/Prague', languages: ['cs-CZ', 'cs'] },
  GR: { name: '希腊', flag: '🇬🇷', timezone: 'Europe/Athens', languages: ['el-GR', 'el'] },
  RO: { name: '罗马尼亚', flag: '🇷🇴', timezone: 'Europe/Bucharest', languages: ['ro-RO', 'ro'] },
  HU: { name: '匈牙利', flag: '🇭🇺', timezone: 'Europe/Budapest', languages: ['hu-HU', 'hu'] },
  BE: { name: '比利时', flag: '🇧🇪', timezone: 'Europe/Brussels', languages: ['nl-BE', 'fr-BE'] },

  // 拉美
  BR: { name: '巴西', flag: '🇧🇷', timezone: 'America/Sao_Paulo', languages: ['pt-BR', 'pt'] },
  MX: { name: '墨西哥', flag: '🇲🇽', timezone: 'America/Mexico_City', languages: ['es-MX', 'es'] },
  AR: { name: '阿根廷', flag: '🇦🇷', timezone: 'America/Argentina/Buenos_Aires', languages: ['es-AR', 'es'] },
  CO: { name: '哥伦比亚', flag: '🇨🇴', timezone: 'America/Bogota', languages: ['es-CO', 'es'] },
  CL: { name: '智利', flag: '🇨🇱', timezone: 'America/Santiago', languages: ['es-CL', 'es'] },
  PE: { name: '秘鲁', flag: '🇵🇪', timezone: 'America/Lima', languages: ['es-PE', 'es'] },

  // 中东与南亚、非洲
  TR: { name: '土耳其', flag: '🇹🇷', timezone: 'Europe/Istanbul', languages: ['tr-TR', 'tr'] },
  IN: { name: '印度', flag: '🇮🇳', timezone: 'Asia/Kolkata', languages: ['en-IN', 'hi-IN', 'en-GB', 'en'] },
  PK: { name: '巴基斯坦', flag: '🇵🇰', timezone: 'Asia/Karachi', languages: ['ur-PK', 'en-PK', 'en'] },
  BD: { name: '孟加拉国', flag: '🇧🇩', timezone: 'Asia/Dhaka', languages: ['bn-BD', 'bn'] },
  AE: { name: '阿联酋', flag: '🇦🇪', timezone: 'Asia/Dubai', languages: ['ar-AE', 'ar'] },
  SA: { name: '沙特阿拉伯', flag: '🇸🇦', timezone: 'Asia/Riyadh', languages: ['ar-SA', 'ar'] },
  EG: { name: '埃及', flag: '🇪🇬', timezone: 'Africa/Cairo', languages: ['ar-EG', 'ar'] },
  IL: { name: '以色列', flag: '🇮🇱', timezone: 'Asia/Jerusalem', languages: ['he-IL', 'he'] },
  ZA: { name: '南非', flag: '🇿🇦', timezone: 'Africa/Johannesburg', languages: ['en-ZA', 'en-GB', 'en'] },
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
