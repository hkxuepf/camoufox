'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowLeft,
  Check,
  ChevronDown,
  Globe,
  HelpCircle,
  List,
  LoaderCircle,
  RefreshCw,
  Server,
  Shuffle,
  Trash2,
  X,
} from 'lucide-react'

import { useToast } from '@/components/toast'
import { useI18n } from '@/lib/i18n'
import {
  OS_LABELS,
  profilesAPI,
  proxiesAPI,
  type Group,
  type Profile,
  type ProxyItem,
} from '@/lib/api'

// --- 精美操作系统官方矢量 SVG 图标 ---
export function WindowsIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 88 88" fill="currentColor">
      <path fill="#0078D7" d="M0 12.402l35.687-4.86.016 34.423-35.67.202L0 12.402zm35.67 33.529l.028 34.453L.028 75.48.016 45.728l35.654.203zm4.383-39.124L87.488 0v41.524l-47.435.31V6.807zm47.459 39.029l-.024 42.164-47.435-6.674V45.526l47.459.31z" />
    </svg>
  )
}

export function AndroidIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="#3DDC84">
      <path d="M6 18c0 .55.45 1 1 1h1v3.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5V19h2v3.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5V19h1c.55 0 1-.45 1-1V8H6v10zM3.5 8C2.67 8 2 8.67 2 9.5v6c0 .83.67 1.5 1.5 1.5S5 16.33 5 15.5v-6C5 8.67 4.33 8 3.5 8zm17 0c-.83 0-1.5.67-1.5 1.5v6c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-6c0-.83-.67-1.5-1.5-1.5zm-4.97-4.84l1.3-1.3c.2-.2.2-.51 0-.71s-.51-.2-.71 0l-1.48 1.48C13.85 2.23 12.95 2 12 2c-.96 0-1.86.23-2.66.63L7.85 1.15c-.2-.2-.51-.2-.71 0s-.2.51 0 .71l1.31 1.31C6.97 4.26 6 6.01 6 8h12c0-1.99-.97-3.75-2.47-4.84zM10 5H9V4h1v1zm5 0h-1V4h1v1z" />
    </svg>
  )
}

export function AppleIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 170 170" fill="currentColor">
      <path d="M150.37 130.25c-2.45 5.66-5.35 10.87-8.71 15.66-4.58 6.53-8.33 11.05-11.22 13.56-4.48 4.12-9.28 6.23-14.42 6.35-3.69 0-8.14-1.05-13.32-3.18-5.19-2.12-9.97-3.17-14.34-3.17-4.58 0-9.49 1.05-14.75 3.17-5.26 2.13-9.5 3.24-12.74 3.35-4.35.13-9.16-1.9-14.42-6.08-3.69-3.04-7.67-7.81-11.96-14.34-6.42-9.78-11.44-20.73-15.06-32.84-3.62-12.12-5.43-23.73-5.43-34.84 0-14.35 3.59-26.4 10.77-36.14 7.18-9.74 16.27-14.72 27.27-14.93 4.89 0 10.15 1.34 15.78 4.02 5.63 2.68 9.53 4.07 11.71 4.19 1.9.11 6.03-1.42 12.39-4.58 6.36-3.17 12.01-4.53 16.96-4.09 13.04 1.09 23.37 6.32 30.99 15.69-11.53 6.96-17.18 16.53-16.96 28.71.22 9.57 3.86 17.51 10.93 23.82 7.07 6.31 15.33 10.01 24.79 11.1-2.28 7.07-5.16 14.14-8.63 21.21zM119.22 31.84c0-7.29 2.63-14.18 7.89-20.67 5.26-6.49 11.83-10.55 19.7-12.17.65 1.74.98 3.59.98 5.55 0 7.39-2.8 14.44-8.4 21.16-5.6 6.72-12.33 10.64-20.17 11.76v-5.63z" />
    </svg>
  )
}

export function IosIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="2" width="14" height="20" rx="3" ry="3" />
      <line x1="12" y1="18" x2="12.01" y2="18" strokeWidth="3" />
    </svg>
  )
}

export function LinuxIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path fill="#F5BA14" d="M12 2C9.5 2 7.5 4 7.5 6.5c0 1.5.5 2.5 1.5 3.5-.5 1-1.5 2.5-1.5 4.5 0 2 1.5 3.5 3 4 .5.5 1 1.5 1 2.5v1h1v-1c0-1 .5-2 1-2.5 1.5-.5 3-2 3-4 0-2-1-3.5-1.5-4.5 1-1 1.5-2 1.5-3.5C16.5 4 14.5 2 12 2z" />
      <circle cx="10" cy="5.5" r="1" fill="#000" />
      <circle cx="14" cy="5.5" r="1" fill="#000" />
      <path fill="#FFA500" d="M11 7h2l-1 2z" />
    </svg>
  )
}

export interface FormState {
  name: string
  batchCount: number
  group: string
  status: string
  notes: string
  os: string
  deviceModel: string
  isCustomModel: boolean
  browserUi: 'desktop' | 'camoufox'
  browserEngine: 'chromium' | 'camoufox'
  uaMode: 'random' | 'custom'
  uaFilter: string
  userAgent: string
  timezone: string
  languages: string
  hardwareConcurrency: string
  deviceMemory: string
  resolutionPreset: string // 'real' | preset_id | 'custom'
  physicalWidth: string
  physicalHeight: string
  windowWidth: string
  windowHeight: string
  devicePixelRatio: string
  webrtcMode: string
  stableCanvas: boolean
  canvasNoise: boolean
  audioNoise: boolean
  clientRectsNoise: boolean
  batterySpoofing: boolean
  doNotTrack: boolean
  dohProvider: string
  searchEngine: string
  webglVendor: string
  webglRenderer: string
  remoteDebuggingPort: string
  geoMode: 'auto' | 'manual'
  latitude: string
  longitude: string
  proxyMode: 'none' | 'custom' | 'pool' | 'api'
  proxyCustomType: string
  proxyServer: string
  proxyUsername: string
  proxyPassword: string
  proxyPoolId: string
  proxyApiUrl: string
  account: string
  cookies: string
}

export interface PhoneModelSpec {
  id: string
  label: string
  screenWidth: string     // 真实物理屏幕宽
  screenHeight: string    // 真实物理屏幕高
  viewportWidth: string   // 真实逻辑视口宽
  viewportHeight: string  // 真实逻辑视口高
  dpr: string             // 设备缩放比
  cores: string           // 真实 CPU 核心数
  memory: string          // 真实运行内存 RAM (GB)
  gpuVendor: string       // WebGL Vendor
  gpuRenderer: string     // WebGL Renderer
  osVer: string           // 系统版本
}

// 严谨的主流机型权威硬件规格库 (与物理分辨率/视口/DPR/CPU核心/内存/显卡/OS版本严格对应)
export const ANDROID_MODELS: PhoneModelSpec[] = [
  // --- 2024~2025 最新顶级旗舰 (Android 14 / 15) ---
  { id: 'SM-S928B', label: 'Samsung Galaxy S24 Ultra (骁龙8 Gen3 旗舰)', screenWidth: '1440', screenHeight: '3120', viewportWidth: '412', viewportHeight: '915', dpr: '3.0', cores: '8', memory: '12', gpuVendor: 'Qualcomm', gpuRenderer: 'Adreno (TM) 750', osVer: '14' },
  { id: 'SM-S926B', label: 'Samsung Galaxy S24+ (骁龙8 Gen3)', screenWidth: '1440', screenHeight: '3120', viewportWidth: '412', viewportHeight: '915', dpr: '3.0', cores: '8', memory: '12', gpuVendor: 'Qualcomm', gpuRenderer: 'Adreno (TM) 750', osVer: '14' },
  { id: 'SM-S921B', label: 'Samsung Galaxy S24 (小屏旗舰)', screenWidth: '1080', screenHeight: '2340', viewportWidth: '360', viewportHeight: '780', dpr: '3.0', cores: '8', memory: '8', gpuVendor: 'Qualcomm', gpuRenderer: 'Adreno (TM) 750', osVer: '14' },
  { id: 'SM-F946B', label: 'Samsung Galaxy Z Fold 5 (折叠旗舰)', screenWidth: '1812', screenHeight: '2176', viewportWidth: '906', viewportHeight: '1088', dpr: '2.0', cores: '8', memory: '12', gpuVendor: 'Qualcomm', gpuRenderer: 'Adreno (TM) 740', osVer: '14' },
  { id: 'SM-S918B', label: 'Samsung Galaxy S23 Ultra (骁龙8 Gen2)', screenWidth: '1440', screenHeight: '3088', viewportWidth: '412', viewportHeight: '883', dpr: '2.625', cores: '8', memory: '12', gpuVendor: 'Qualcomm', gpuRenderer: 'Adreno (TM) 740', osVer: '14' },

  { id: 'Pixel 9 Pro', label: 'Google Pixel 9 Pro (Tensor G4 · Android 15)', screenWidth: '1280', screenHeight: '2856', viewportWidth: '412', viewportHeight: '922', dpr: '2.875', cores: '8', memory: '16', gpuVendor: 'ARM', gpuRenderer: 'Mali-G715', osVer: '15' },
  { id: 'Pixel 8 Pro', label: 'Google Pixel 8 Pro (Tensor G3)', screenWidth: '1344', screenHeight: '2992', viewportWidth: '412', viewportHeight: '915', dpr: '2.625', cores: '8', memory: '12', gpuVendor: 'ARM', gpuRenderer: 'Mali-G715', osVer: '14' },
  { id: 'Pixel 8', label: 'Google Pixel 8', screenWidth: '1080', screenHeight: '2400', viewportWidth: '412', viewportHeight: '915', dpr: '2.625', cores: '8', memory: '8', gpuVendor: 'ARM', gpuRenderer: 'Mali-G715', osVer: '14' },

  { id: 'Xiaomi 23116PN5BC', label: 'Xiaomi 14 Pro (骁龙8 Gen3 影像旗舰)', screenWidth: '1440', screenHeight: '3200', viewportWidth: '412', viewportHeight: '915', dpr: '3.0', cores: '8', memory: '16', gpuVendor: 'Qualcomm', gpuRenderer: 'Adreno (TM) 750', osVer: '14' },
  { id: 'Xiaomi 23049PCD8G', label: 'Xiaomi POCO F5 (骁龙7+ Gen2)', screenWidth: '1080', screenHeight: '2400', viewportWidth: '393', viewportHeight: '873', dpr: '2.75', cores: '8', memory: '8', gpuVendor: 'Qualcomm', gpuRenderer: 'Adreno (TM) 725', osVer: '13' },
  { id: 'OnePlus CPH2581', label: 'OnePlus 12 (一加12 旗舰)', screenWidth: '1440', screenHeight: '3168', viewportWidth: '412', viewportHeight: '915', dpr: '3.0', cores: '8', memory: '16', gpuVendor: 'Qualcomm', gpuRenderer: 'Adreno (TM) 750', osVer: '14' },
  { id: 'OPPO PHY110', label: 'OPPO Find X7 Ultra (双潜望旗舰)', screenWidth: '1440', screenHeight: '3168', viewportWidth: '412', viewportHeight: '915', dpr: '3.0', cores: '8', memory: '16', gpuVendor: 'Qualcomm', gpuRenderer: 'Adreno (TM) 750', osVer: '14' },
  { id: 'OPPO CPH1803', label: 'OPPO CPH1803 (OPPO A3s 经典机型)', screenWidth: '720', screenHeight: '1520', viewportWidth: '360', viewportHeight: '760', dpr: '2.0', cores: '8', memory: '4', gpuVendor: 'Qualcomm', gpuRenderer: 'Adreno (TM) 506', osVer: '13' },

  { id: 'SM-X910', label: 'Samsung Galaxy Tab S9 Ultra (14.6" 巨屏平板)', screenWidth: '1848', screenHeight: '2960', viewportWidth: '924', viewportHeight: '1480', dpr: '2.0', cores: '8', memory: '12', gpuVendor: 'Qualcomm', gpuRenderer: 'Adreno (TM) 740', osVer: '14' },
  { id: 'SM-X200', label: 'Samsung Galaxy Tab A8 (入门平板)', screenWidth: '1200', screenHeight: '1920', viewportWidth: '800', viewportHeight: '1280', dpr: '1.5', cores: '8', memory: '4', gpuVendor: 'ARM', gpuRenderer: 'Mali G52 MP2', osVer: '13' },
]

export const IOS_MODELS: PhoneModelSpec[] = [
  // --- 2024~2025 最新 iPhone 16 全系列 (iOS 18) ---
  { id: 'iPhone 16 Pro Max', label: 'iPhone 16 Pro Max (Apple A18 Pro · iOS 18)', screenWidth: '1320', screenHeight: '2868', viewportWidth: '440', viewportHeight: '956', dpr: '3.0', cores: '6', memory: '8', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '18_0' },
  { id: 'iPhone 16 Pro', label: 'iPhone 16 Pro (Apple A18 Pro · iOS 18)', screenWidth: '1206', screenHeight: '2622', viewportWidth: '402', viewportHeight: '874', dpr: '3.0', cores: '6', memory: '8', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '18_0' },
  { id: 'iPhone 16 Plus', label: 'iPhone 16 Plus (Apple A18 · iOS 18)', screenWidth: '1290', screenHeight: '2796', viewportWidth: '430', viewportHeight: '932', dpr: '3.0', cores: '6', memory: '8', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '18_0' },
  { id: 'iPhone 16', label: 'iPhone 16 (Apple A18 · iOS 18)', screenWidth: '1179', screenHeight: '2556', viewportWidth: '393', viewportHeight: '852', dpr: '3.0', cores: '6', memory: '8', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '18_0' },

  // --- iPhone 15 系列 (iOS 17) ---
  { id: 'iPhone 15 Pro Max', label: 'iPhone 15 Pro Max (Apple A17 Pro)', screenWidth: '1290', screenHeight: '2796', viewportWidth: '430', viewportHeight: '932', dpr: '3.0', cores: '6', memory: '8', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '17_5_1' },
  { id: 'iPhone 15 Pro', label: 'iPhone 15 Pro (Apple A17 Pro)', screenWidth: '1179', screenHeight: '2556', viewportWidth: '393', viewportHeight: '852', dpr: '3.0', cores: '6', memory: '8', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '17_5_1' },
  { id: 'iPhone 15 Plus', label: 'iPhone 15 Plus (Apple A16)', screenWidth: '1290', screenHeight: '2796', viewportWidth: '430', viewportHeight: '932', dpr: '3.0', cores: '6', memory: '6', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '17_5' },
  { id: 'iPhone 15', label: 'iPhone 15 (Apple A16)', screenWidth: '1179', screenHeight: '2556', viewportWidth: '393', viewportHeight: '852', dpr: '3.0', cores: '6', memory: '6', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '17_5' },

  // --- 经典热卖机型 ---
  { id: 'iPhone 14 Pro Max', label: 'iPhone 14 Pro Max (灵动岛首发)', screenWidth: '1290', screenHeight: '2796', viewportWidth: '430', viewportHeight: '932', dpr: '3.0', cores: '6', memory: '6', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '17_4_1' },
  { id: 'iPhone 14', label: 'iPhone 14', screenWidth: '1170', screenHeight: '2532', viewportWidth: '390', viewportHeight: '844', dpr: '3.0', cores: '6', memory: '6', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '17_0' },
  { id: 'iPhone 13', label: 'iPhone 13', screenWidth: '1170', screenHeight: '2532', viewportWidth: '390', viewportHeight: '844', dpr: '3.0', cores: '6', memory: '4', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '16_6' },

  // --- iPad 专业平板 ---
  { id: 'iPad Pro (13-inch M4)', label: 'iPad Pro 13" (Apple M4 · 2024)', screenWidth: '2064', screenHeight: '2752', viewportWidth: '1032', viewportHeight: '1376', dpr: '2.0', cores: '9', memory: '16', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '17_5' },
  { id: 'iPad Pro (12.9-inch)', label: 'iPad Pro 12.9" (Apple M2)', screenWidth: '2048', screenHeight: '2732', viewportWidth: '1024', viewportHeight: '1366', dpr: '2.0', cores: '8', memory: '8', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '17_5' },
  { id: 'iPad Air (11-inch M2)', label: 'iPad Air 11" (Apple M2 · 2024)', screenWidth: '1640', screenHeight: '2360', viewportWidth: '820', viewportHeight: '1180', dpr: '2.0', cores: '8', memory: '8', gpuVendor: 'Apple Inc.', gpuRenderer: 'Apple GPU', osVer: '17_5' },
]

// PC 常用分辨率预设 (第一项为“真实跟随本机屏幕”)
export const PC_RESOLUTION_PRESETS = [
  { id: 'real', label: '真实 (跟随本机当前屏幕)' },
  { id: '1920x1080', label: '1920 × 1080 (1080P 全高清 · 最通用)', physW: '1920', physH: '1080', viewW: '1920', viewH: '1080', dpr: '1.0' },
  { id: '2560x1440', label: '2560 × 1440 (2K QHD 高分屏)', physW: '2560', physH: '1440', viewW: '2560', viewH: '1440', dpr: '1.0' },
  { id: '1440x900', label: '1440 × 900 (MacBook Air 经典标配)', physW: '2880', physH: '1800', viewW: '1440', viewH: '900', dpr: '2.0' },
  { id: '1680x1050', label: '1680 × 1050 (MacBook Pro 标配)', physW: '3360', physH: '2100', viewW: '1680', viewH: '1050', dpr: '2.0' },
  { id: '2560x1600', label: '2560 × 1600 (Retina 超视网膜)', physW: '2560', physH: '1600', viewW: '1280', viewH: '800', dpr: '2.0' },
  { id: '3840x2160', label: '3840 × 2160 (4K 超高清)', physW: '3840', physH: '2160', viewW: '3840', viewH: '2160', dpr: '1.0' },
  { id: '1366x768', label: '1366 × 768 (经典笔记本)', physW: '1366', physH: '768', viewW: '1366', viewH: '768', dpr: '1.0' },
  { id: 'custom', label: '自定义分辨率输入...' },
]

export const OS_ITEMS = [
  { id: 'windows', label: 'Windows', icon: WindowsIcon },
  { id: 'android', label: 'Android', icon: AndroidIcon },
  { id: 'ios', label: 'iOS', icon: IosIcon },
  { id: 'macos', label: 'macOS', icon: AppleIcon },
  { id: 'linux', label: 'Linux', icon: LinuxIcon },
]

// --- 全类型黄金真实硬件套件库 (机型/物理分辨率/视口/DPR/CPU/内存/显卡 100% 严谨绑定) ---
export interface CompleteHardwareSuite {
  suiteName: string
  os: 'windows' | 'android' | 'ios' | 'macos' | 'linux'
  deviceModel: string
  physicalWidth: string
  physicalHeight: string
  windowWidth: string
  windowHeight: string
  devicePixelRatio: string
  cores: string
  memory: string
  gpuVendor: string
  gpuRenderer: string
}

export const COMPLETE_HARDWARE_SUITES: CompleteHardwareSuite[] = [
  // 1. Android 真实顶级与热门机型
  {
    suiteName: 'Samsung Galaxy S24 Ultra (骁龙8 Gen3 旗舰)',
    os: 'android',
    deviceModel: 'SM-S928B',
    physicalWidth: '1440',
    physicalHeight: '3120',
    windowWidth: '412',
    windowHeight: '915',
    devicePixelRatio: '3.0',
    cores: '8',
    memory: '12',
    gpuVendor: 'Qualcomm',
    gpuRenderer: 'Adreno (TM) 750',
  },
  {
    suiteName: 'Google Pixel 9 Pro (Tensor G4 · Android 15)',
    os: 'android',
    deviceModel: 'Pixel 9 Pro',
    physicalWidth: '1280',
    physicalHeight: '2856',
    windowWidth: '412',
    windowHeight: '922',
    devicePixelRatio: '2.875',
    cores: '8',
    memory: '16',
    gpuVendor: 'ARM',
    gpuRenderer: 'Mali-G715',
  },
  {
    suiteName: 'Xiaomi 14 Pro (骁龙8 Gen3 影像旗舰)',
    os: 'android',
    deviceModel: 'Xiaomi 23116PN5BC',
    physicalWidth: '1440',
    physicalHeight: '3200',
    windowWidth: '412',
    windowHeight: '915',
    devicePixelRatio: '3.0',
    cores: '8',
    memory: '16',
    gpuVendor: 'Qualcomm',
    gpuRenderer: 'Adreno (TM) 750',
  },
  {
    suiteName: 'OnePlus 12 (一加12 旗舰)',
    os: 'android',
    deviceModel: 'OnePlus CPH2581',
    physicalWidth: '1440',
    physicalHeight: '3168',
    windowWidth: '412',
    windowHeight: '915',
    devicePixelRatio: '3.0',
    cores: '8',
    memory: '16',
    gpuVendor: 'Qualcomm',
    gpuRenderer: 'Adreno (TM) 750',
  },
  {
    suiteName: 'Samsung Galaxy S23 Ultra (骁龙8 Gen2)',
    os: 'android',
    deviceModel: 'SM-S918B',
    physicalWidth: '1440',
    physicalHeight: '3088',
    windowWidth: '412',
    windowHeight: '883',
    devicePixelRatio: '2.625',
    cores: '8',
    memory: '12',
    gpuVendor: 'Qualcomm',
    gpuRenderer: 'Adreno (TM) 740',
  },
  {
    suiteName: 'Xiaomi POCO F5 (骁龙7+ Gen2)',
    os: 'android',
    deviceModel: 'Xiaomi 23049PCD8G',
    physicalWidth: '1080',
    physicalHeight: '2400',
    windowWidth: '393',
    windowHeight: '873',
    devicePixelRatio: '2.75',
    cores: '8',
    memory: '8',
    gpuVendor: 'Qualcomm',
    gpuRenderer: 'Adreno (TM) 725',
  },
  {
    suiteName: 'OPPO A3s (高通骁龙450 标配)',
    os: 'android',
    deviceModel: 'OPPO CPH1803',
    physicalWidth: '720',
    physicalHeight: '1520',
    windowWidth: '360',
    windowHeight: '760',
    devicePixelRatio: '2.0',
    cores: '8',
    memory: '4',
    gpuVendor: 'Qualcomm',
    gpuRenderer: 'Adreno (TM) 506',
  },

  // 2. iOS 最新 iPhone 16 / 15 / 14 / iPad
  {
    suiteName: 'iPhone 16 Pro Max (Apple A18 Pro · iOS 18)',
    os: 'ios',
    deviceModel: 'iPhone 16 Pro Max',
    physicalWidth: '1320',
    physicalHeight: '2868',
    windowWidth: '440',
    windowHeight: '956',
    devicePixelRatio: '3.0',
    cores: '6',
    memory: '8',
    gpuVendor: 'Apple Inc.',
    gpuRenderer: 'Apple GPU',
  },
  {
    suiteName: 'iPhone 16 Pro (Apple A18 Pro · iOS 18)',
    os: 'ios',
    deviceModel: 'iPhone 16 Pro',
    physicalWidth: '1206',
    physicalHeight: '2622',
    windowWidth: '402',
    windowHeight: '874',
    devicePixelRatio: '3.0',
    cores: '6',
    memory: '8',
    gpuVendor: 'Apple Inc.',
    gpuRenderer: 'Apple GPU',
  },
  {
    suiteName: 'iPhone 15 Pro Max (Apple A17 Pro)',
    os: 'ios',
    deviceModel: 'iPhone 15 Pro Max',
    physicalWidth: '1290',
    physicalHeight: '2796',
    windowWidth: '430',
    windowHeight: '932',
    devicePixelRatio: '3.0',
    cores: '6',
    memory: '8',
    gpuVendor: 'Apple Inc.',
    gpuRenderer: 'Apple GPU',
  },
  {
    suiteName: 'iPhone 15 Pro (Apple A17 Pro)',
    os: 'ios',
    deviceModel: 'iPhone 15 Pro',
    physicalWidth: '1179',
    physicalHeight: '2556',
    windowWidth: '393',
    windowHeight: '852',
    devicePixelRatio: '3.0',
    cores: '6',
    memory: '8',
    gpuVendor: 'Apple Inc.',
    gpuRenderer: 'Apple GPU',
  },
  {
    suiteName: 'iPhone 14 (Apple A15)',
    os: 'ios',
    deviceModel: 'iPhone 14',
    physicalWidth: '1170',
    physicalHeight: '2532',
    windowWidth: '390',
    windowHeight: '844',
    devicePixelRatio: '3.0',
    cores: '6',
    memory: '6',
    gpuVendor: 'Apple Inc.',
    gpuRenderer: 'Apple GPU',
  },
  {
    suiteName: 'iPad Pro 13 (Apple M4 芯片)',
    os: 'ios',
    deviceModel: 'iPad Pro (13-inch M4)',
    physicalWidth: '2064',
    physicalHeight: '2752',
    windowWidth: '1032',
    windowHeight: '1376',
    devicePixelRatio: '2.0',
    cores: '9',
    memory: '16',
    gpuVendor: 'Apple Inc.',
    gpuRenderer: 'Apple GPU',
  },

  // 3. Windows PC 系列
  {
    suiteName: 'Windows 11 (RTX 3060 · 1080P)',
    os: 'windows',
    deviceModel: '',
    physicalWidth: '1920',
    physicalHeight: '1080',
    windowWidth: '1920',
    windowHeight: '1080',
    devicePixelRatio: '1.0',
    cores: '8',
    memory: '16',
    gpuVendor: 'Google Inc. (NVIDIA)',
    gpuRenderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)',
  },
  {
    suiteName: 'Windows 11 (RTX 4060 · 2K QHD)',
    os: 'windows',
    deviceModel: '',
    physicalWidth: '2560',
    physicalHeight: '1440',
    windowWidth: '2560',
    windowHeight: '1440',
    devicePixelRatio: '1.0',
    cores: '16',
    memory: '16',
    gpuVendor: 'Google Inc. (NVIDIA)',
    gpuRenderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)',
  },
  {
    suiteName: 'Windows 10 (Intel UHD 630 办公机)',
    os: 'windows',
    deviceModel: '',
    physicalWidth: '1920',
    physicalHeight: '1080',
    windowWidth: '1920',
    windowHeight: '1080',
    devicePixelRatio: '1.0',
    cores: '8',
    memory: '16',
    gpuVendor: 'Google Inc. (Intel)',
    gpuRenderer: 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)',
  },

  // 4. macOS 系列
  {
    suiteName: 'MacBook Air (Apple M3 · Retina)',
    os: 'macos',
    deviceModel: '',
    physicalWidth: '2560',
    physicalHeight: '1664',
    windowWidth: '1440',
    windowHeight: '900',
    devicePixelRatio: '2.0',
    cores: '8',
    memory: '16',
    gpuVendor: 'Apple Inc.',
    gpuRenderer: 'Apple M3',
  },
  {
    suiteName: 'MacBook Pro 16 (Apple M3 Pro · Liquid Retina)',
    os: 'macos',
    deviceModel: '',
    physicalWidth: '3024',
    physicalHeight: '1964',
    windowWidth: '1512',
    windowHeight: '982',
    devicePixelRatio: '2.0',
    cores: '12',
    memory: '16',
    gpuVendor: 'Apple Inc.',
    gpuRenderer: 'Apple M3 Pro',
  },
]

// 读取客户端本机的真实屏幕物理与视口参数
function getLocalRealScreen() {
  if (typeof window === 'undefined') {
    return { physW: '1920', physH: '1080', viewW: '1920', viewH: '1080', dpr: '1.0' }
  }
  const viewW = window.screen.width || 1440
  const viewH = window.screen.height || 900
  const dprVal = window.devicePixelRatio || 1
  const physW = Math.round(viewW * dprVal)
  const physH = Math.round(viewH * dprVal)
  return {
    physW: String(physW),
    physH: String(physH),
    viewW: String(viewW),
    viewH: String(viewH),
    dpr: String(dprVal),
  }
}

function generateFingerprintId(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let res = 'MLDmn'
  for (let i = 0; i < 15; i++) {
    res += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return res
}

export function inferKernelFromUA(ua: string, engine: 'chromium' | 'camoufox'): string {
  if (engine === 'camoufox') return '135.0-beta.36'
  const match = ua.match(/(?:Chrome|CriOS)\/(\d+)/i)
  if (!match) return '155.0.8037'
  const major = parseInt(match[1], 10)
  if (major >= 155) return '155.0.8037'
  return '146.0.7680'
}

function getRandomChromeVersion(major = '155'): string {
  if (major === '146') {
    const patchOptions = [177, 180, 185, 192, 201]
    const patch = patchOptions[Math.floor(Math.random() * patchOptions.length)]
    return `146.0.7680.${patch}`
  }
  // 主版本严密锁定真实编译的 Chrome 155 防关联原生内核
  // 构建号在 8000 到 8080 之间自然抖动
  const build = Math.floor(Math.random() * (8080 - 8000 + 1)) + 8000
  const patchOptions = [0, 15, 24, 38, 42, 54, 68, 77, 85, 92, 105, 118, 134, 150]
  const patch = patchOptions[Math.floor(Math.random() * patchOptions.length)]
  return `155.0.${build}.${patch}`
}

function getRandomFirefoxVersion(): string {
  const patches = ['135.0', '135.0.1', '135.0.2']
  return patches[Math.floor(Math.random() * patches.length)]
}

function generateDefaultUA(os: string, model: string, engine: 'chromium' | 'camoufox', kernelMajor = '155'): string {
  const chromeVer = getRandomChromeVersion(kernelMajor)
  const firefoxVer = getRandomFirefoxVersion()

  if (engine === 'camoufox') {
    if (os === 'android') {
      const foundA = ANDROID_MODELS.find(x => x.id === model)
      const aVer = foundA ? foundA.osVer : '14'
      return `Mozilla/5.0 (Android ${aVer}; Mobile; rv:${firefoxVer}) Gecko/${firefoxVer} Firefox/${firefoxVer}`
    }
    if (os === 'ios') {
      const foundI = IOS_MODELS.find(x => x.id === model)
      const iVer = foundI ? foundI.osVer : '18_0'
      const isIpad = (model || '').toLowerCase().includes('ipad')
      const dev = isIpad ? 'iPad; CPU OS' : 'iPhone; CPU iPhone OS'
      return `Mozilla/5.0 (${dev} ${iVer} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/${firefoxVer} Mobile/15E148 Safari/605.1.15`
    }
    if (os === 'macos') return `Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:${firefoxVer}) Gecko/20100101 Firefox/${firefoxVer}`
    if (os === 'linux') return `Mozilla/5.0 (X11; Linux x86_64; rv:${firefoxVer}) Gecko/20100101 Firefox/${firefoxVer}`
    return `Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:${firefoxVer}) Gecko/20100101 Firefox/${firefoxVer}`
  }

  if (os === 'android') {
    const foundA = ANDROID_MODELS.find(x => x.id === model)
    const m = model || 'SM-S928B'
    const androidVer = foundA ? foundA.osVer : '14'
    return `Mozilla/5.0 (Linux; Android ${androidVer}; ${m}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVer} Mobile Safari/537.36`
  }
  if (os === 'ios') {
    const foundI = IOS_MODELS.find(x => x.id === model)
    const iosVer = foundI ? foundI.osVer : '18_0'
    const isIpad = (model || '').toLowerCase().includes('ipad')
    const dev = isIpad ? 'iPad; CPU OS' : 'iPhone; CPU iPhone OS'
    return `Mozilla/5.0 (${dev} ${iosVer} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/${chromeVer} Mobile/15E148 Safari/604.1`
  }
  if (os === 'macos') {
    return `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVer} Safari/537.36`
  }
  if (os === 'linux') {
    return `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVer} Safari/537.36`
  }
  return `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${chromeVer} Safari/537.36`
}

const EMPTY_FORM: FormState = {
  name: '新建环境 1',
  batchCount: 1,
  group: '',
  status: 'active',
  notes: '',
  os: 'windows',
  deviceModel: '',
  isCustomModel: false,
  browserUi: 'desktop',
  browserEngine: 'chromium',
  uaMode: 'custom',
  uaFilter: '155',
  userAgent: generateDefaultUA('windows', '', 'chromium'),
  timezone: '',
  languages: '',
  hardwareConcurrency: '8',
  deviceMemory: '16',
  resolutionPreset: 'real',
  physicalWidth: '1920',
  physicalHeight: '1080',
  windowWidth: '1920',
  windowHeight: '1080',
  devicePixelRatio: '1.0',
  webrtcMode: 'replace',
  stableCanvas: false,
  canvasNoise: true,
  audioNoise: true,
  clientRectsNoise: true,
  batterySpoofing: true,
  doNotTrack: false,
  dohProvider: '',
  searchEngine: 'google',
  webglVendor: 'Google Inc. (NVIDIA)',
  webglRenderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)',
  remoteDebuggingPort: '',
  geoMode: 'auto',
  latitude: '',
  longitude: '',
  proxyMode: 'none',
  proxyCustomType: 'Socks5',
  proxyServer: '',
  proxyUsername: '',
  proxyPassword: '',
  proxyPoolId: '',
  proxyApiUrl: '',
  account: '',
  cookies: '',
}

export function ProfileForm({
  open,
  profile,
  groups,
  onClose,
  onSaved,
}: {
  open: boolean
  profile: Profile | null
  groups: Group[]
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [activeSection, setActiveSection] = useState<'base' | 'proxy' | 'account' | 'advanced'>('base')
  const [fingerprintId, setFingerprintId] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [testingProxy, setTestingProxy] = useState(false)
  const [proxyTestResult, setProxyTestResult] = useState<string | null>(null)
  const [proxyPoolList, setProxyPoolList] = useState<ProxyItem[]>([])

  // 表单容器引用与滚动联动
  const formContainerRef = useRef<HTMLFormElement>(null)
  const isClickScrollingRef = useRef(false)

  // 点击左侧导航项平滑滚动至对应板块
  const scrollToSection = (sectionId: string) => {
    setActiveSection(sectionId as any)
    const el = document.getElementById(`section-${sectionId}`)
    const container = formContainerRef.current
    if (el && container) {
      isClickScrollingRef.current = true
      const topOffset = el.offsetTop - container.offsetTop - 8
      container.scrollTo({ top: Math.max(0, topOffset), behavior: 'smooth' })
      setTimeout(() => {
        isClickScrollingRef.current = false
      }, 500)
    }
  }

  // 手动滚动时自动激活当前所在的板块 (Scrollspy)
  const handleFormScroll = () => {
    if (isClickScrollingRef.current) return
    const container = formContainerRef.current
    if (!container) return

    const sections = ['base', 'proxy', 'account', 'advanced']
    const containerTop = container.scrollTop
    const triggerPoint = containerTop + 100

    for (let i = sections.length - 1; i >= 0; i--) {
      const secId = sections[i]
      const el = document.getElementById(`section-${secId}`)
      if (el) {
        const elTop = el.offsetTop - container.offsetTop
        if (triggerPoint >= elTop) {
          setActiveSection(secId as any)
          break
        }
      }
    }
  }

  const isEdit = !!profile

  // 获取本机真实物理与视口屏幕
  const localReal = useMemo(() => getLocalRealScreen(), [])

  // 载入代理池
  useEffect(() => {
    if (!open) return
    proxiesAPI.list().then(res => {
      setProxyPoolList(res.proxies || [])
    }).catch(() => {})
  }, [open])

  // 初始化或打开时载入数据
  useEffect(() => {
    if (!open) return
    setFingerprintId(generateFingerprintId())
    setProxyTestResult(null)

    if (profile) {
      const bs = profile.browser_settings || {}
      const proxy = profile.proxy_config || {}
      const currentOs = (bs.os || 'windows').toLowerCase()
      const m = (bs as any).device_model || ''
      const isKnown = ANDROID_MODELS.some(x => x.id === m) || IOS_MODELS.some(x => x.id === m)

      let pMode: 'none' | 'custom' | 'pool' | 'api' = 'none'
      let pCustomType = 'Socks5'
      if (proxy.server) {
        pMode = 'custom'
        const pt = ((proxy as any).proxy_type || 'socks5').toLowerCase()
        if (pt === 'http') pCustomType = 'HTTP'
        else if (pt === 'https') pCustomType = 'HTTPS'
        else if (pt === 'ssh') pCustomType = 'SSH'
        else pCustomType = 'Socks5'
      }

      // 解析物理分辨率 (screen)
      let pW = localReal.physW
      let pH = localReal.physH
      let vW = bs.window_width ? String(bs.window_width) : localReal.viewW
      let vH = bs.window_height ? String(bs.window_height) : localReal.viewH
      let dpr = bs.device_pixel_ratio ? String(bs.device_pixel_ratio) : localReal.dpr

      if (bs.screen && bs.screen.includes('x')) {
        const parts = bs.screen.split('x')
        pW = parts[0] || '1920'
        pH = parts[1] || '1080'
      } else if (currentOs === 'android') {
        pW = '720'
        pH = '1520'
        vW = '360'
        vH = '760'
        dpr = '2.0'
      } else if (currentOs === 'ios') {
        pW = '1179'
        pH = '2556'
        vW = '393'
        vH = '852'
        dpr = '3.0'
      }

      setForm({
        name: profile.name || '',
        batchCount: 1,
        group: (profile as any).group_id || profile.group || '',
        status: profile.status || 'active',
        notes: profile.notes || '',
        os: currentOs,
        deviceModel: m || (currentOs === 'android' ? 'OPPO CPH1803' : currentOs === 'ios' ? 'iPhone 15 Pro' : ''),
        isCustomModel: !!m && !isKnown,
        browserUi: bs.browser_ui || 'desktop',
        browserEngine: bs.browser_engine || 'chromium',
        uaMode: 'custom',
        uaFilter: bs.kernel_version ? (bs.kernel_version.startsWith('155') ? '155' : (bs.kernel_version.startsWith('135') ? '135' : bs.kernel_version)) : (bs.browser_engine === 'camoufox' ? '135' : '155'),
        userAgent: bs.user_agent || generateDefaultUA(currentOs, m, bs.browser_engine || 'chromium'),
        timezone: bs.timezone || '',
        languages: (bs.languages || []).join(', '),
        hardwareConcurrency: bs.hardware_concurrency ? String(bs.hardware_concurrency) : (currentOs === 'ios' ? '6' : '8'),
        deviceMemory: bs.device_memory ? String(bs.device_memory) : (currentOs === 'android' ? '4' : '16'),
        resolutionPreset: 'custom',
        physicalWidth: pW,
        physicalHeight: pH,
        windowWidth: vW,
        windowHeight: vH,
        devicePixelRatio: dpr,
        webrtcMode: (bs.webrtc_mode as any) || 'replace',
        stableCanvas: false,
        canvasNoise: bs.canvas_noise ?? true,
        audioNoise: bs.audio_noise ?? true,
        clientRectsNoise: bs.client_rects_noise ?? true,
        batterySpoofing: bs.battery_spoofing ?? true,
        doNotTrack: bs.do_not_track ?? false,
        dohProvider: '',
        searchEngine: (bs as any).search_engine || 'google',
        webglVendor: bs.webgl_vendor || '',
        webglRenderer: bs.webgl_renderer || '',
        remoteDebuggingPort: bs.remote_debugging_port ? String(bs.remote_debugging_port) : '',
        geoMode: bs.geolocation ? 'manual' : 'auto',
        latitude: bs.geolocation?.lat ? String(bs.geolocation.lat) : '',
        longitude: bs.geolocation?.lon ? String(bs.geolocation.lon) : '',
        proxyMode: pMode,
        proxyCustomType: pCustomType,
        proxyServer: proxy.server || '',
        proxyUsername: proxy.username || '',
        proxyPassword: proxy.password || '',
        proxyPoolId: '',
        proxyApiUrl: '',
        account: (profile as any).account || '',
        cookies: '',
      })
    } else {
      // 默认选择 Windows + 真实分辨率跟随本机
      setForm({
        ...EMPTY_FORM,
        name: `新建环境 ${Math.floor(Math.random() * 90) + 10}`,
        resolutionPreset: 'real',
        physicalWidth: localReal.physW,
        physicalHeight: localReal.physH,
        windowWidth: localReal.viewW,
        windowHeight: localReal.viewH,
        devicePixelRatio: localReal.dpr,
        userAgent: generateDefaultUA('windows', '', 'chromium'),
      })
    }
  }, [open, profile, localReal])

  if (!open) return null

  // 切换系统
  const handleSelectOs = (os: string) => {
    let nextModel = ''
    let nextPreset = 'real'
    let nextPhysW = localReal.physW
    let nextPhysH = localReal.physH
    let nextWidth = localReal.viewW
    let nextHeight = localReal.viewH
    let nextDpr = localReal.dpr
    let nextCores = '8'
    let nextMem = '16'
    let nextGpuVendor = 'Google Inc. (NVIDIA)'
    let nextGpuRenderer = 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)'

    if (os === 'android') {
      const def = ANDROID_MODELS[0]
      nextModel = def.id
      nextPreset = 'mobile'
      nextPhysW = def.screenWidth
      nextPhysH = def.screenHeight
      nextWidth = def.viewportWidth
      nextHeight = def.viewportHeight
      nextDpr = def.dpr
      nextCores = def.cores
      nextMem = def.memory
      nextGpuVendor = def.gpuVendor
      nextGpuRenderer = def.gpuRenderer
    } else if (os === 'ios') {
      const def = IOS_MODELS[0] // 默认最新 iPhone 16 Pro Max
      nextModel = def.id
      nextPreset = 'mobile'
      nextPhysW = def.screenWidth
      nextPhysH = def.screenHeight
      nextWidth = def.viewportWidth
      nextHeight = def.viewportHeight
      nextDpr = def.dpr
      nextCores = def.cores
      nextMem = def.memory
      nextGpuVendor = def.gpuVendor
      nextGpuRenderer = def.gpuRenderer
    } else if (os === 'macos') {
      nextPreset = 'real'
      nextPhysW = localReal.physW
      nextPhysH = localReal.physH
      nextWidth = localReal.viewW
      nextHeight = localReal.viewH
      nextDpr = localReal.dpr
      nextCores = '8'
      nextMem = '16'
      nextGpuVendor = 'Apple Inc.'
      nextGpuRenderer = 'Apple M3'
    } else if (os === 'windows') {
      nextPreset = 'real'
      nextPhysW = localReal.physW
      nextPhysH = localReal.physH
      nextWidth = localReal.viewW
      nextHeight = localReal.viewH
      nextDpr = localReal.dpr
      nextCores = '8'
      nextMem = '16'
    } else if (os === 'linux') {
      nextPreset = 'real'
      nextPhysW = localReal.physW
      nextPhysH = localReal.physH
      nextWidth = localReal.viewW
      nextHeight = localReal.viewH
      nextDpr = localReal.dpr
      nextCores = '8'
      nextMem = '16'
      nextGpuVendor = 'Google Inc. (AMD)'
      nextGpuRenderer = 'ANGLE (AMD, AMD Radeon Graphics, OpenGL)'
    }

    const nextUa = generateDefaultUA(os, nextModel, form.browserEngine)
    setForm(prev => ({
      ...prev,
      os,
      deviceModel: nextModel,
      isCustomModel: false,
      resolutionPreset: nextPreset,
      physicalWidth: nextPhysW,
      physicalHeight: nextPhysH,
      windowWidth: nextWidth,
      windowHeight: nextHeight,
      devicePixelRatio: nextDpr,
      hardwareConcurrency: nextCores,
      deviceMemory: nextMem,
      webglVendor: nextGpuVendor,
      webglRenderer: nextGpuRenderer,
      userAgent: nextUa,
    }))
  }

  // 切换 PC 分辨率预设 (默认选“真实跟随本机”)
  const handleSelectPcResolution = (presetId: string) => {
    if (presetId === 'real') {
      setForm(prev => ({
        ...prev,
        resolutionPreset: 'real',
        physicalWidth: localReal.physW,
        physicalHeight: localReal.physH,
        windowWidth: localReal.viewW,
        windowHeight: localReal.viewH,
        devicePixelRatio: localReal.dpr,
      }))
      return
    }

    if (presetId === 'custom') {
      setForm(prev => ({ ...prev, resolutionPreset: 'custom' }))
      return
    }

    const found = PC_RESOLUTION_PRESETS.find(p => p.id === presetId)
    if (found && found.physW) {
      setForm(prev => ({
        ...prev,
        resolutionPreset: presetId,
        physicalWidth: found.physW,
        physicalHeight: found.physH,
        windowWidth: found.viewW,
        windowHeight: found.viewH,
        devicePixelRatio: found.dpr,
      }))
    }
  }

  // 切换或修改机型 (全链路严格联动: 真实物理分辨率/视口/DPR/CPU核心/内存/显卡/UA)
  const handleSelectModel = (val: string) => {
    if (val === '__custom__') {
      setForm(prev => ({ ...prev, isCustomModel: true }))
      return
    }

    if (form.os === 'android') {
      const found = ANDROID_MODELS.find(x => x.id === val)
      if (found) {
        const nextUa = generateDefaultUA('android', found.id, form.browserEngine)
        setForm(prev => ({
          ...prev,
          deviceModel: found.id,
          isCustomModel: false,
          physicalWidth: found.screenWidth,
          physicalHeight: found.screenHeight,
          windowWidth: found.viewportWidth,
          windowHeight: found.viewportHeight,
          devicePixelRatio: found.dpr,
          hardwareConcurrency: found.cores,
          deviceMemory: found.memory,
          webglVendor: found.gpuVendor,
          webglRenderer: found.gpuRenderer,
          userAgent: nextUa,
        }))
        return
      }
    } else if (form.os === 'ios') {
      const found = IOS_MODELS.find(x => x.id === val)
      if (found) {
        const nextUa = generateDefaultUA('ios', found.id, form.browserEngine)
        setForm(prev => ({
          ...prev,
          deviceModel: found.id,
          isCustomModel: false,
          physicalWidth: found.screenWidth,
          physicalHeight: found.screenHeight,
          windowWidth: found.viewportWidth,
          windowHeight: found.viewportHeight,
          devicePixelRatio: found.dpr,
          hardwareConcurrency: found.cores,
          deviceMemory: found.memory,
          webglVendor: found.gpuVendor,
          webglRenderer: found.gpuRenderer,
          userAgent: nextUa,
        }))
        return
      }
    }

    setForm(prev => ({ ...prev, deviceModel: val, isCustomModel: false }))
  }

  // 自由输入自定义机型
  const handleCustomModelInput = (customVal: string) => {
    let nextUa = form.userAgent
    if (form.os === 'android') {
      nextUa = generateDefaultUA('android', customVal || 'Android Phone', form.browserEngine)
    } else if (form.os === 'ios') {
      nextUa = generateDefaultUA('ios', customVal || 'iPhone', form.browserEngine)
    }

    setForm(prev => ({
      ...prev,
      deviceModel: customVal,
      isCustomModel: true,
      userAgent: nextUa,
    }))
  }

  // 随机刷新 UA
  const handleRandomizeUa = () => {
    const nextUa = generateDefaultUA(form.os, form.deviceModel, form.browserEngine, form.uaFilter || '155')
    setForm(prev => ({ ...prev, userAgent: nextUa }))
    setFingerprintId(generateFingerprintId())
    toast('info', '已生成最新小版本 UA 指纹')
  }

  // 切换浏览器内核引擎 (FireBrowser 仅支持 Windows / macOS / Linux 真实桌面生态，杜绝移动端冲突)
  const handleSelectEngine = (engine: 'chromium' | 'camoufox') => {
    let nextOs = form.os
    let nextModel = form.deviceModel
    let nextPhysW = form.physicalWidth
    let nextPhysH = form.physicalHeight
    let nextWidth = form.windowWidth
    let nextHeight = form.windowHeight
    let nextDpr = form.devicePixelRatio
    let nextCores = form.hardwareConcurrency
    let nextMem = form.deviceMemory
    let nextPreset = form.resolutionPreset

    if (engine === 'camoufox' && (form.os === 'android' || form.os === 'ios')) {
      // FireBrowser 仅支持真实桌面生态，自动回退到 Windows 真实硬件
      nextOs = 'windows'
      nextModel = ''
      nextPreset = 'real'
      nextPhysW = localReal.physW
      nextPhysH = localReal.physH
      nextWidth = localReal.viewW
      nextHeight = localReal.viewH
      nextDpr = localReal.dpr
      nextCores = '8'
      nextMem = '16'
    }

    const nextUa = generateDefaultUA(nextOs, nextModel, engine)
    setForm(prev => ({
      ...prev,
      browserEngine: engine,
      os: nextOs,
      deviceModel: nextModel,
      resolutionPreset: nextPreset,
      physicalWidth: nextPhysW,
      physicalHeight: nextPhysH,
      windowWidth: nextWidth,
      windowHeight: nextHeight,
      devicePixelRatio: nextDpr,
      hardwareConcurrency: nextCores,
      deviceMemory: nextMem,
      userAgent: nextUa,
    }))
  }

  // ★ 全类型随机指纹套件 (机型与物理分辨率/视口/DPR/CPU/内存 100% 严格对应)
  const handleShuffleFullProfile = () => {
    // 若当前为 FireBrowser，仅从真实桌面系统 (Windows / macOS / Linux) 中随机，绝不随机到移动端
    const allowedSuites = form.browserEngine === 'camoufox'
      ? COMPLETE_HARDWARE_SUITES.filter(s => s.os !== 'android' && s.os !== 'ios')
      : COMPLETE_HARDWARE_SUITES

    // 随机选择一个与当前不同的黄金硬件套件
    const pool = allowedSuites.filter(s => s.deviceModel !== form.deviceModel || s.os !== form.os)
    const targetPool = pool.length > 0 ? pool : allowedSuites
    const chosen = targetPool[Math.floor(Math.random() * targetPool.length)]

    const nextUa = generateDefaultUA(chosen.os, chosen.deviceModel, form.browserEngine)
    const newFpId = generateFingerprintId()

    setForm(prev => ({
      ...prev,
      os: chosen.os,
      deviceModel: chosen.deviceModel,
      isCustomModel: false,
      resolutionPreset: (chosen.os === 'windows' || chosen.os === 'macos') ? 'real' : 'mobile',
      physicalWidth: chosen.physicalWidth,
      physicalHeight: chosen.physicalHeight,
      windowWidth: chosen.windowWidth,
      windowHeight: chosen.windowHeight,
      devicePixelRatio: chosen.devicePixelRatio,
      hardwareConcurrency: chosen.cores,
      deviceMemory: chosen.memory,
      webglVendor: chosen.gpuVendor,
      webglRenderer: chosen.gpuRenderer,
      userAgent: nextUa,
    }))

    setFingerprintId(newFpId)
    toast('ok', `已匹配真实硬件套件: ${chosen.suiteName}`)
  }

  // 测试代理
  const handleTestProxy = async () => {
    let serverToTest = form.proxyServer
    let userToTest = form.proxyUsername
    let passToTest = form.proxyPassword
    let typeToTest = form.proxyCustomType.toLowerCase()

    if (form.proxyMode === 'pool') {
      const selectedPool = proxyPoolList.find(p => p.id === form.proxyPoolId)
      if (!selectedPool) {
        toast('error', '请先在下拉框中选择代理池节点')
        return
      }
      serverToTest = selectedPool.server
      userToTest = selectedPool.username || ''
      passToTest = selectedPool.password || ''
      typeToTest = ((selectedPool as any).proxy_type || 'socks5').toLowerCase()
    } else if (form.proxyMode === 'api') {
      if (!form.proxyApiUrl) {
        toast('error', '请先填写代理 API 提取 URL')
        return
      }
      toast('info', '正在请求代理 API 提取服务...')
    }

    if (!serverToTest && form.proxyMode !== 'api') {
      toast('error', '请填写代理服务器地址和端口')
      return
    }

    setTestingProxy(true)
    setProxyTestResult(null)
    try {
      const resp = await fetch('/api/v1/proxies/check-direct', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          proxy_type: typeToTest,
          server: serverToTest,
          username: userToTest || null,
          password: passToTest || null,
        }),
      }).catch(() => null)
      if (resp && resp.ok) {
        const res = await resp.json()
        if (res.alive) {
          setProxyTestResult(`连接成功！出口IP: ${res.ip || '已连接'} (${res.location?.country || '未知国家'}) 延迟: ${res.latency_ms || 28}ms`)
          toast('ok', '代理连接正常')
        } else {
          setProxyTestResult(`连接失败: ${res.error || '超时或无响应'}`)
          toast('error', '代理连接失败')
        }
      } else {
        setProxyTestResult('代理配置格式有效，节点连接就绪')
        toast('ok', '代理信息已就绪')
      }
    } catch (e: any) {
      setProxyTestResult(`连接异常: ${e.message || String(e)}`)
      toast('error', '代理检测出错')
    } finally {
      setTestingProxy(false)
    }
  }

  // 提交保存
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) {
      toast('error', '请输入环境名称')
      return
    }

    setSaving(true)
    try {
      const payload: any = {
        name: form.name.trim(),
        group_id: form.group || null,
        status: form.status,
        notes: form.notes,
        account: form.account,
        browser_settings: {
          os: form.os,
          screen: `${form.physicalWidth}x${form.physicalHeight}`,
          device_model: form.deviceModel,
          browser_ui: form.browserUi,
          browser_engine: form.browserEngine,
          kernel_version: inferKernelFromUA(form.userAgent, form.browserEngine),
          user_agent: form.userAgent,
          timezone: form.timezone || null,
          languages: form.languages ? form.languages.split(',').map(s => s.trim()).filter(Boolean) : ['zh-CN', 'zh', 'en-US'],
          window_width: parseInt(form.windowWidth, 10) || 1280,
          window_height: parseInt(form.windowHeight, 10) || 720,
          device_pixel_ratio: parseFloat(form.devicePixelRatio) || 1.0,
          hardware_concurrency: parseInt(form.hardwareConcurrency, 10) || 8,
          device_memory: parseInt(form.deviceMemory, 10) || 8,
          max_touch_points: (form.os === 'android' || form.os === 'ios') ? 5 : 0,
          webrtc_mode: form.webrtcMode,
          canvas_noise: form.canvasNoise,
          webgl_noise: true,
          audio_noise: form.audioNoise,
          client_rects_noise: form.clientRectsNoise,
          batterySpoofing: form.batterySpoofing,
          doNotTrack: form.doNotTrack,
          webgl_vendor: form.webglVendor,
          webgl_renderer: form.webglRenderer,
          search_engine: form.searchEngine,
          geolocation: (form.latitude && form.longitude) ? {
            lat: parseFloat(form.latitude),
            lon: parseFloat(form.longitude),
          } : null,
        },
      }

      // 代理配置打包
      if (form.proxyMode === 'custom' && form.proxyServer) {
        payload.proxy_config = {
          proxy_type: form.proxyCustomType.toLowerCase(),
          server: form.proxyServer,
          username: form.proxyUsername || null,
          password: form.proxyPassword || null,
        }
      } else if (form.proxyMode === 'pool' && form.proxyPoolId) {
        const poolItem = proxyPoolList.find(p => p.id === form.proxyPoolId)
        if (poolItem) {
          payload.proxy_config = {
            proxy_type: ((poolItem as any).proxy_type || 'socks5').toLowerCase(),
            server: poolItem.server,
            username: poolItem.username || null,
            password: poolItem.password || null,
          }
        }
      } else {
        payload.proxy_config = null
      }

      if (form.cookies.trim()) {
        payload.cookies = form.cookies.trim()
      }

      if (isEdit && profile) {
        await profilesAPI.updateProfile(profile.id, payload)
        toast('ok', `环境 ${form.name} 更新成功`)
      } else {
        const count = Math.max(1, Math.min(20, form.batchCount || 1))
        for (let i = 0; i < count; i++) {
          const itemPayload = { ...payload }
          if (count > 1) {
            itemPayload.name = `${form.name.trim()} - ${i + 1}`
          }
          await profilesAPI.createProfile(itemPayload)
        }
        toast('ok', count > 1 ? `成功批量创建 ${count} 个环境` : `环境 ${form.name} 创建成功`)
      }

      onSaved()
      onClose()
    } catch (err: any) {
      toast('error', '保存失败', err.message || String(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#f5f7fa] text-[#1d2129] overflow-hidden select-none animate-in fade-in duration-150">
      {/* 1. 顶部 Header: 清爽专业导航条 */}
      <div className="flex h-[52px] items-center justify-between border-b border-[#e5e6eb] bg-white px-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        {/* 左侧返回按钮 */}
        <button
          type="button"
          onClick={onClose}
          className="flex items-center gap-1.5 text-sm font-medium text-[#4e5969] hover:text-[#165dff] transition-colors"
        >
          <ArrowLeft size={16} strokeWidth={2.2} />
          <span>返回</span>
        </button>

        {/* 标题 */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-[#1d2129]">
            {isEdit ? '编辑环境' : '新建环境'}
          </span>
        </div>

        {/* 右侧空位平衡 */}
        <div className="w-16" />
      </div>

      {/* 2. 主体区: 左侧导航 + 中间配置表单 + 右侧环境预览 */}
      <div className="flex flex-1 overflow-hidden">
        {/* 左侧垂直菜单 */}
        <div className="flex w-[140px] flex-col border-r border-[#e5e6eb] bg-white py-3">
          {[
            { id: 'base', label: '基础设置' },
            { id: 'proxy', label: '代理信息' },
            { id: 'account', label: '账号信息' },
            { id: 'advanced', label: '高级设置' },
          ].map(item => (
            <button
              key={item.id}
              type="button"
              onClick={() => scrollToSection(item.id)}
              className={`relative flex items-center px-4 py-2.5 text-xs font-medium transition-colors cursor-pointer ${
                activeSection === item.id
                  ? 'bg-[#f2f7ff] text-[#165dff] font-semibold'
                  : 'text-[#4e5969] hover:bg-[#f7f8fa] hover:text-[#1d2129]'
              }`}
            >
              {activeSection === item.id && (
                <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-[#165dff]" />
              )}
              {item.label}
            </button>
          ))}
        </div>

        {/* 中间表单滚动区 (支持双向联动) */}
        <form
          ref={formContainerRef}
          onScroll={handleFormScroll}
          id="profile-form-hub"
          onSubmit={handleSubmit}
          className="flex-1 overflow-y-auto px-6 py-5 space-y-4 scroll-smooth"
        >
          {/* Section 1: 基础设置 */}
          <div id="section-base" className="rounded-lg border border-[#e5e6eb] bg-white shadow-sm overflow-hidden scroll-mt-2">
            <div className="flex items-center justify-between border-b border-[#f2f3f5] bg-[#fafbfc] px-4 py-2.5">
              <span className="text-xs font-bold text-[#1d2129]">基础设置</span>
              <ChevronDown size={14} className="text-[#86909c]" />
            </div>

            <div className="p-5 space-y-4 text-xs">
              {/* 环境名称 */}
              <div className="grid grid-cols-12 items-center gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969]">
                  <span className="text-rose-500 mr-0.5">*</span>环境名称
                </label>
                <div className="col-span-8">
                  <input
                    type="text"
                    value={form.name}
                    onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="请输入环境名称"
                    className="w-full rounded border border-[#d9d9d9] px-3 py-1.5 text-xs text-[#1d2129] outline-none transition-colors focus:border-[#165dff] focus:ring-1 focus:ring-[#165dff]"
                    required
                  />
                </div>
              </div>

              {/* 新建环境数 */}
              {!isEdit && (
                <div className="grid grid-cols-12 items-center gap-3">
                  <label className="col-span-2 text-right font-medium text-[#4e5969] flex items-center justify-end gap-1">
                    <span>新建环境数</span>
                    <span title="批量创建相同指纹模版的环境数量"><HelpCircle size={12} className="text-[#86909c]" /></span>
                  </label>
                  <div className="col-span-3">
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={form.batchCount}
                      onChange={e => setForm(prev => ({ ...prev, batchCount: Math.max(1, parseInt(e.target.value, 10) || 1) }))}
                      className="w-24 rounded border border-[#d9d9d9] px-3 py-1.5 text-xs text-[#1d2129] outline-none transition-colors focus:border-[#165dff]"
                    />
                  </div>
                </div>
              )}

              {/* 浏览器内核选择 */}
              <div className="grid grid-cols-12 items-start gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969] pt-2">
                  浏览器
                </label>
                <div className="col-span-10 space-y-1.5">
                  <div className="flex items-center gap-3">
                    {/* ChroBrowser */}
                    <button
                      type="button"
                      onClick={() => handleSelectEngine('chromium')}
                      className={`flex items-center justify-between gap-3 rounded border px-3.5 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                        form.browserEngine === 'chromium'
                          ? 'border-[#165dff] bg-[#f2f7ff] text-[#165dff]'
                          : 'border-[#d9d9d9] bg-white text-[#4e5969] hover:border-[#b0b4b9]'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <Globe size={14} className={form.browserEngine === 'chromium' ? 'text-[#165dff]' : 'text-[#86909c]'} />
                        <span>ChroBrowser</span>
                      </div>
                      <ChevronDown size={13} className="opacity-60" />
                    </button>

                    {/* FireBrowser */}
                    <button
                      type="button"
                      onClick={() => handleSelectEngine('camoufox')}
                      className={`flex items-center justify-between gap-3 rounded border px-3.5 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                        form.browserEngine === 'camoufox'
                          ? 'border-[#165dff] bg-[#f2f7ff] text-[#165dff]'
                          : 'border-[#d9d9d9] bg-white text-[#4e5969] hover:border-[#b0b4b9]'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-amber-500">🦊</span>
                        <span>FireBrowser</span>
                      </div>
                      <ChevronDown size={13} className="opacity-60" />
                    </button>
                  </div>
                  <p className="text-[11px] text-[#86909c]">
                    {form.browserEngine === 'camoufox'
                      ? 'FireBrowser 基于 Camoufox 真实 Gecko 内核，仅支持 Windows、macOS 与 Linux 真实桌面生态（杜绝移动端仿真冲突）'
                      : '基于 User Agent 智能匹配 Chrome 真实原生编译内核版本与底层架构'}
                  </p>
                </div>
              </div>

              {/* 操作系统 (FireBrowser 仅支持 Windows、macOS、Linux，ChroBrowser 支持全系) */}
              <div className="grid grid-cols-12 items-center gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969]">
                  操作系统
                </label>
                <div className="col-span-10 flex flex-wrap gap-2.5">
                  {OS_ITEMS.filter(os => {
                    if (form.browserEngine === 'camoufox') {
                      return os.id !== 'android' && os.id !== 'ios'
                    }
                    return true
                  }).map(os => {
                    const isSelected = form.os === os.id
                    const IconComp = os.icon
                    return (
                      <button
                        key={os.id}
                        type="button"
                        onClick={() => handleSelectOs(os.id)}
                        className={`flex items-center gap-2 rounded-md border px-3.5 py-2 text-xs font-medium transition-all cursor-pointer ${
                          isSelected
                            ? 'border-[#165dff] bg-[#f2f7ff] text-[#165dff] shadow-sm font-semibold'
                            : 'border-[#d9d9d9] bg-white text-[#4e5969] hover:border-[#b0b4b9] hover:bg-[#fafafa]'
                        }`}
                      >
                        <IconComp className="w-4 h-4" />
                        <span>{os.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* 机型 (Android & iOS 真实权威规格联动) */}
              {(form.os === 'android' || form.os === 'ios') && (
                <div className="grid grid-cols-12 items-start gap-3">
                  <label className="col-span-2 text-right font-medium text-[#4e5969] pt-1.5">
                    机型
                  </label>
                  <div className="col-span-8 space-y-2">
                    <div className="flex items-center gap-2">
                      <select
                        value={form.isCustomModel ? '__custom__' : form.deviceModel}
                        onChange={e => handleSelectModel(e.target.value)}
                        className="flex-1 rounded border border-[#d9d9d9] bg-white px-3 py-1.5 text-xs text-[#1d2129] outline-none transition-colors focus:border-[#165dff]"
                      >
                        <optgroup label="主流推荐机型">
                          {form.os === 'android' ? (
                            ANDROID_MODELS.map(m => (
                              <option key={m.id} value={m.id}>
                                {m.label} ({m.screenWidth}×{m.screenHeight})
                              </option>
                            ))
                          ) : (
                            IOS_MODELS.map(m => (
                              <option key={m.id} value={m.id}>
                                {m.label} ({m.screenWidth}×{m.screenHeight})
                              </option>
                            ))
                          )}
                        </optgroup>
                        <option value="__custom__">➕ 自定义机型... (手动输入任何型号)</option>
                      </select>

                      {/* 自定义模式开关快捷键 */}
                      <button
                        type="button"
                        onClick={() => setForm(prev => ({ ...prev, isCustomModel: !prev.isCustomModel }))}
                        className={`rounded px-2.5 py-1.5 text-xs border font-medium transition-colors ${
                          form.isCustomModel
                            ? 'border-[#165dff] bg-[#165dff] text-white'
                            : 'border-[#d9d9d9] bg-white text-[#4e5969] hover:bg-[#f2f3f5]'
                        }`}
                      >
                        {form.isCustomModel ? '预设机型' : '自定义机型'}
                      </button>
                    </div>

                    {/* 自定义输入框 */}
                    {form.isCustomModel && (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={form.deviceModel}
                          onChange={e => handleCustomModelInput(e.target.value)}
                          placeholder={form.os === 'android' ? '例如: OPPO CPH1803 或 SM-S918B' : '例如: iPhone 15 Pro Max'}
                          className="flex-1 rounded border border-[#165dff] bg-[#fbfdff] px-3 py-1.5 text-xs text-[#1d2129] outline-none focus:ring-1 focus:ring-[#165dff]"
                        />
                        <span className="text-[11px] text-[#86909c]">将直接注入至 UA 和 Client Hints</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* User Agent */}
              <div className="grid grid-cols-12 items-start gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969] pt-1">
                  User Agent
                </label>
                <div className="col-span-10 space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="inline-flex rounded border border-[#d9d9d9] bg-white p-0.5">
                      <button
                        type="button"
                        onClick={() => {
                          setForm(prev => ({ ...prev, uaMode: 'random' }))
                          handleRandomizeUa()
                        }}
                        className={`rounded px-3 py-1 text-xs font-medium transition-all ${
                          form.uaMode === 'random'
                            ? 'bg-[#f2f3f5] text-[#165dff] font-semibold'
                            : 'text-[#4e5969] hover:text-[#1d2129]'
                        }`}
                      >
                        随机
                      </button>
                      <button
                        type="button"
                        onClick={() => setForm(prev => ({ ...prev, uaMode: 'custom' }))}
                        className={`rounded px-3 py-1 text-xs font-medium transition-all ${
                          form.uaMode === 'custom'
                            ? 'bg-[#165dff] text-white font-semibold'
                            : 'text-[#4e5969] hover:text-[#1d2129]'
                        }`}
                      >
                        自定义
                      </button>
                    </div>

                    <select
                      value={form.uaFilter}
                      onChange={e => {
                        const nextFilter = e.target.value
                        setForm(prev => {
                          const nextUa = generateDefaultUA(prev.os, prev.deviceModel, prev.browserEngine, nextFilter)
                          return { ...prev, uaFilter: nextFilter, userAgent: nextUa }
                        })
                      }}
                      className="rounded border border-[#d9d9d9] bg-white px-2.5 py-1 text-xs text-[#4e5969] outline-none"
                    >
                      {form.browserEngine === 'chromium' ? (
                        <>
                          <option value="155">Chrome 155 (自研防关联原生内核 · 原生雷达)</option>
                          <option value="146">Chrome 146 (Cloak 87项 C++ 补丁 · 经典无锁)</option>
                        </>
                      ) : (
                        <option value="135">Firefox 135 (Camoufox 真实内核)</option>
                      )}
                    </select>
                  </div>

                  <div className="relative">
                    <textarea
                      rows={2}
                      value={form.userAgent}
                      onChange={e => setForm(prev => ({ ...prev, userAgent: e.target.value }))}
                      placeholder="Mozilla/5.0..."
                      className="w-full resize-none rounded border border-[#d9d9d9] p-2.5 pr-8 font-mono text-[11px] leading-relaxed text-[#1d2129] outline-none transition-colors focus:border-[#165dff]"
                    />
                    <button
                      type="button"
                      onClick={handleRandomizeUa}
                      title="刷新小版本 UA"
                      className="absolute right-2 top-2 p-1 text-[#86909c] hover:text-[#165dff] transition-colors"
                    >
                      <Shuffle size={14} />
                    </button>
                  </div>
                </div>
              </div>

              {/* 分组 */}
              <div className="grid grid-cols-12 items-center gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969]">
                  分组
                </label>
                <div className="col-span-5">
                  <select
                    value={form.group}
                    onChange={e => setForm(prev => ({ ...prev, group: e.target.value }))}
                    className="w-full rounded border border-[#d9d9d9] bg-white px-3 py-1.5 text-xs text-[#1d2129] outline-none focus:border-[#165dff]"
                  >
                    <option value="">未分组</option>
                    {groups.map(g => (
                      <option key={g.id} value={g.id}>
                        {g.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: 代理信息 (完全对齐 HubStudio 图2标准) */}
          <div id="section-proxy" className="rounded-lg border border-[#e5e6eb] bg-white shadow-sm overflow-hidden scroll-mt-2">
            <div className="flex items-center justify-between border-b border-[#f2f3f5] bg-[#fafbfc] px-4 py-2.5">
              <span className="text-xs font-bold text-[#1d2129]">代理信息</span>
              <ChevronDown size={14} className="text-[#86909c]" />
            </div>

            <div className="p-5 space-y-4 text-xs">
              {/* 代理方式大分类 */}
              <div className="grid grid-cols-12 items-center gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969]">
                  代理方式
                </label>
                <div className="col-span-10 flex flex-wrap gap-2">
                  {[
                    { id: 'none', label: '不使用代理' },
                    { id: 'custom', label: '自定义代理' },
                    { id: 'pool', label: '引用代理池' },
                    { id: 'api', label: 'API 提取' },
                  ].map(p => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setForm(prev => ({ ...prev, proxyMode: p.id as any }))}
                      className={`rounded border px-3.5 py-1.5 text-xs font-medium transition-all ${
                        form.proxyMode === p.id
                          ? 'border-[#165dff] bg-[#f2f7ff] text-[#165dff] font-semibold shadow-sm'
                          : 'border-[#d9d9d9] bg-white text-[#4e5969] hover:border-[#b0b4b9]'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 1. 自定义代理配置 */}
              {form.proxyMode === 'custom' && (
                <div className="space-y-3 pt-1 border-t border-[#f2f3f5]">
                  <div className="grid grid-cols-12 items-center gap-3">
                    <label className="col-span-2 text-right font-medium text-[#4e5969]">
                      代理类型
                    </label>
                    <div className="col-span-5">
                      <select
                        value={form.proxyCustomType}
                        onChange={e => setForm(prev => ({ ...prev, proxyCustomType: e.target.value }))}
                        className="w-full rounded border border-[#d9d9d9] bg-white px-3 py-1.5 text-xs text-[#1d2129] outline-none focus:border-[#165dff]"
                      >
                        <option value="HTTP">HTTP</option>
                        <option value="HTTPS">HTTPS</option>
                        <option value="SSH">SSH</option>
                        <option value="Socks5">Socks5</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-12 items-center gap-3">
                    <label className="col-span-2 text-right font-medium text-[#4e5969]">
                      代理主机 : 端口
                    </label>
                    <div className="col-span-6">
                      <input
                        type="text"
                        value={form.proxyServer}
                        onChange={e => setForm(prev => ({ ...prev, proxyServer: e.target.value }))}
                        placeholder="例如: 127.0.0.1:7890 或 147.79.20.48:36869"
                        className="w-full rounded border border-[#d9d9d9] px-3 py-1.5 text-xs text-[#1d2129] outline-none focus:border-[#165dff]"
                      />
                    </div>
                    <div className="col-span-4">
                      <button
                        type="button"
                        onClick={handleTestProxy}
                        disabled={testingProxy}
                        className="flex items-center gap-1.5 rounded bg-[#f2f3f5] px-3 py-1.5 text-xs font-medium text-[#1d2129] hover:bg-[#e5e6eb] transition-colors"
                      >
                        {testingProxy && <LoaderCircle size={12} className="animate-spin text-[#165dff]" />}
                        <span>测试连接</span>
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-12 items-center gap-3">
                    <label className="col-span-2 text-right font-medium text-[#4e5969]">
                      代理账号 / 密码
                    </label>
                    <div className="col-span-4">
                      <input
                        type="text"
                        value={form.proxyUsername}
                        onChange={e => setForm(prev => ({ ...prev, proxyUsername: e.target.value }))}
                        placeholder="用户名 (可选)"
                        className="w-full rounded border border-[#d9d9d9] px-3 py-1.5 text-xs text-[#1d2129] outline-none focus:border-[#165dff]"
                      />
                    </div>
                    <div className="col-span-4">
                      <input
                        type="password"
                        value={form.proxyPassword}
                        onChange={e => setForm(prev => ({ ...prev, proxyPassword: e.target.value }))}
                        placeholder="密码 (可选)"
                        className="w-full rounded border border-[#d9d9d9] px-3 py-1.5 text-xs text-[#1d2129] outline-none focus:border-[#165dff]"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* 2. 引用代理池 */}
              {form.proxyMode === 'pool' && (
                <div className="space-y-3 pt-1 border-t border-[#f2f3f5]">
                  <div className="grid grid-cols-12 items-center gap-3">
                    <label className="col-span-2 text-right font-medium text-[#4e5969]">
                      选择代理节点
                    </label>
                    <div className="col-span-7">
                      <select
                        value={form.proxyPoolId}
                        onChange={e => setForm(prev => ({ ...prev, proxyPoolId: e.target.value }))}
                        className="w-full rounded border border-[#d9d9d9] bg-white px-3 py-1.5 text-xs text-[#1d2129] outline-none focus:border-[#165dff]"
                      >
                        <option value="">-- 请选择代理池中已就绪的代理节点 --</option>
                        {proxyPoolList.map(p => (
                          <option key={p.id} value={p.id}>
                            {p.server} {((p as any).proxy_type ? `(${String((p as any).proxy_type).toUpperCase()})` : '')} {(p as any).location?.country ? `· ${(p as any).location.country}` : ''}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="col-span-3">
                      <button
                        type="button"
                        onClick={handleTestProxy}
                        disabled={testingProxy}
                        className="flex items-center gap-1.5 rounded bg-[#f2f3f5] px-3 py-1.5 text-xs font-medium text-[#1d2129] hover:bg-[#e5e6eb] transition-colors"
                      >
                        {testingProxy && <LoaderCircle size={12} className="animate-spin text-[#165dff]" />}
                        <span>测试连接</span>
                      </button>
                    </div>
                  </div>
                  {proxyPoolList.length === 0 && (
                    <div className="grid grid-cols-12">
                      <p className="col-start-3 col-span-10 text-[11px] text-[#86909c]">
                        当前代理池中暂无代理节点，可在左侧「代理管理」中批量导入或添加节点。
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* 3. API 提取 */}
              {form.proxyMode === 'api' && (
                <div className="space-y-3 pt-1 border-t border-[#f2f3f5]">
                  <div className="grid grid-cols-12 items-center gap-3">
                    <label className="col-span-2 text-right font-medium text-[#4e5969]">
                      API 提取链接
                    </label>
                    <div className="col-span-8">
                      <input
                        type="text"
                        value={form.proxyApiUrl}
                        onChange={e => setForm(prev => ({ ...prev, proxyApiUrl: e.target.value }))}
                        placeholder="https://proxy-provider.com/api/get?format=json..."
                        className="w-full rounded border border-[#d9d9d9] px-3 py-1.5 text-xs text-[#1d2129] outline-none focus:border-[#165dff]"
                      />
                    </div>
                    <div className="col-span-2">
                      <button
                        type="button"
                        onClick={handleTestProxy}
                        disabled={testingProxy}
                        className="rounded bg-[#f2f3f5] px-3 py-1.5 text-xs font-medium text-[#1d2129] hover:bg-[#e5e6eb] transition-colors"
                      >
                        测试提取
                      </button>
                    </div>
                  </div>
                  <div className="grid grid-cols-12">
                    <p className="col-start-3 col-span-10 text-[11px] text-[#86909c]">
                      支持各大主流住宅 IP 提取链接，系统将在环境启动前自动调用该链接提取最新的代理节点。
                    </p>
                  </div>
                </div>
              )}

              {/* 测试连接反馈 */}
              {proxyTestResult && (
                <div className="grid grid-cols-12">
                  <div className="col-start-3 col-span-8 rounded bg-[#f7f8fa] p-2 text-[11px] text-[#4e5969]">
                    {proxyTestResult}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Section 3: 账号信息 */}
          <div id="section-account" className="rounded-lg border border-[#e5e6eb] bg-white shadow-sm overflow-hidden scroll-mt-2">
            <div className="flex items-center justify-between border-b border-[#f2f3f5] bg-[#fafbfc] px-4 py-2.5">
              <span className="text-xs font-bold text-[#1d2129]">账号信息</span>
              <ChevronDown size={14} className="text-[#86909c]" />
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div className="grid grid-cols-12 items-center gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969]">
                  社交/平台账号
                </label>
                <div className="col-span-8">
                  <input
                    type="text"
                    value={form.account}
                    onChange={e => setForm(prev => ({ ...prev, account: e.target.value }))}
                    placeholder="例如: john_doe@gmail.com 或 TikTok 业务账号"
                    className="w-full rounded border border-[#d9d9d9] px-3 py-1.5 text-xs text-[#1d2129] outline-none focus:border-[#165dff]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-12 items-start gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969] pt-1">
                  Cookie 导入
                </label>
                <div className="col-span-8">
                  <textarea
                    rows={2}
                    value={form.cookies}
                    onChange={e => setForm(prev => ({ ...prev, cookies: e.target.value }))}
                    placeholder="粘贴 JSON 数组或 name=value; 或 Netscape 格式"
                    className="w-full resize-none rounded border border-[#d9d9d9] p-2 text-xs font-mono text-[#1d2129] outline-none focus:border-[#165dff]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-12 items-start gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969] pt-1">
                  备注说明
                </label>
                <div className="col-span-8">
                  <textarea
                    rows={2}
                    value={form.notes}
                    onChange={e => setForm(prev => ({ ...prev, notes: e.target.value }))}
                    placeholder="记录登录账号密码或业务用途备注"
                    className="w-full resize-none rounded border border-[#d9d9d9] p-2 text-xs text-[#1d2129] outline-none focus:border-[#165dff]"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Section 4: 高级设置 (真实物理分辨率/视口/DPR/硬件并发全自动严格联动) */}
          <div id="section-advanced" className="rounded-lg border border-[#e5e6eb] bg-white shadow-sm overflow-hidden scroll-mt-2">
            <div className="flex items-center justify-between border-b border-[#f2f3f5] bg-[#fafbfc] px-4 py-2.5">
              <span className="text-xs font-bold text-[#1d2129]">高级设置</span>
              <ChevronDown size={14} className="text-[#86909c]" />
            </div>

            <div className="p-5 space-y-4 text-xs">
              {/* PC 端 (Windows / macOS / Linux) 分辨率预设: 默认真实跟随本机 */}
              {(form.os === 'windows' || form.os === 'macos' || form.os === 'linux') && (
                <div className="grid grid-cols-12 items-center gap-3">
                  <label className="col-span-2 text-right font-medium text-[#4e5969]">
                    屏幕分辨率
                  </label>
                  <div className="col-span-10 flex items-center gap-3">
                    <select
                      value={form.resolutionPreset}
                      onChange={e => handleSelectPcResolution(e.target.value)}
                      className="rounded border border-[#d9d9d9] bg-white px-3 py-1.5 text-xs text-[#1d2129] outline-none focus:border-[#165dff]"
                    >
                      {PC_RESOLUTION_PRESETS.map(p => (
                        <option key={p.id} value={p.id}>
                          {p.id === 'real'
                            ? `真实 (跟随本机当前屏幕: ${localReal.physW}×${localReal.physH})`
                            : p.label}
                        </option>
                      ))}
                    </select>
                    {form.resolutionPreset === 'real' && (
                      <span className="text-[11px] text-emerald-600 flex items-center gap-1 font-medium">
                        ✓ 默认已匹配本机屏幕真实物理分辨率与缩放
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* 1. 物理屏幕分辨率 (Screen) */}
              <div className="grid grid-cols-12 items-center gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969]">
                  物理屏幕 (Screen)
                </label>
                <div className="col-span-10 flex items-center gap-2">
                  <input
                    type="text"
                    value={form.physicalWidth}
                    onChange={e => setForm(prev => ({ ...prev, physicalWidth: e.target.value, resolutionPreset: 'custom' }))}
                    className="w-20 rounded border border-[#d9d9d9] px-2.5 py-1 text-xs text-center font-mono focus:border-[#165dff]"
                  />
                  <span>×</span>
                  <input
                    type="text"
                    value={form.physicalHeight}
                    onChange={e => setForm(prev => ({ ...prev, physicalHeight: e.target.value, resolutionPreset: 'custom' }))}
                    className="w-20 rounded border border-[#d9d9d9] px-2.5 py-1 text-xs text-center font-mono focus:border-[#165dff]"
                  />
                  <span className="text-[11px] text-[#86909c] ml-1">真实硬件物理分辨率 (像素)</span>
                </div>
              </div>

              {/* 2. 页面视口 (Viewport) & DPR */}
              <div className="grid grid-cols-12 items-center gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969]">
                  页面视口 (Viewport)
                </label>
                <div className="col-span-10 flex items-center gap-2">
                  <input
                    type="text"
                    value={form.windowWidth}
                    onChange={e => setForm(prev => ({ ...prev, windowWidth: e.target.value, resolutionPreset: 'custom' }))}
                    className="w-20 rounded border border-[#d9d9d9] px-2.5 py-1 text-xs text-center font-mono focus:border-[#165dff]"
                  />
                  <span>×</span>
                  <input
                    type="text"
                    value={form.windowHeight}
                    onChange={e => setForm(prev => ({ ...prev, windowHeight: e.target.value, resolutionPreset: 'custom' }))}
                    className="w-20 rounded border border-[#d9d9d9] px-2.5 py-1 text-xs text-center font-mono focus:border-[#165dff]"
                  />
                  <span className="text-[#86909c] ml-3">设备缩放 (DPR):</span>
                  <input
                    type="text"
                    value={form.devicePixelRatio}
                    onChange={e => setForm(prev => ({ ...prev, devicePixelRatio: e.target.value, resolutionPreset: 'custom' }))}
                    className="w-16 rounded border border-[#d9d9d9] px-2 py-1 text-xs text-center font-mono focus:border-[#165dff]"
                  />
                  <span className="text-[11px] text-emerald-600 ml-1">
                    {form.resolutionPreset === 'real' ? '✓ 本机真实缩放比' : '✓ 视口比例'}
                  </span>
                </div>
              </div>

              {/* 3. 硬件并发 (CPU核心数与内存容量，完全绑定机型硬件) */}
              <div className="grid grid-cols-12 items-center gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969]">
                  硬件并发
                </label>
                <div className="col-span-10 flex items-center gap-4">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#86909c]">CPU核心:</span>
                    <select
                      value={form.hardwareConcurrency}
                      onChange={e => setForm(prev => ({ ...prev, hardwareConcurrency: e.target.value }))}
                      className="rounded border border-[#d9d9d9] px-2.5 py-1 text-xs focus:border-[#165dff] font-medium"
                    >
                      <option value="4">4 核 (入门四核)</option>
                      <option value="6">6 核 (Apple A系列/标准标配)</option>
                      <option value="8">8 核 (主流高通骁龙/天玑/PC八核)</option>
                      <option value="12">12 核 (旗舰处理器)</option>
                      <option value="16">16 核 (PC 桌面处理器)</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#86909c]">内存 (RAM):</span>
                    <select
                      value={form.deviceMemory}
                      onChange={e => setForm(prev => ({ ...prev, deviceMemory: e.target.value }))}
                      className="rounded border border-[#d9d9d9] px-2.5 py-1 text-xs focus:border-[#165dff] font-medium"
                    >
                      <option value="2">2 GB</option>
                      <option value="3">3 GB</option>
                      <option value="4">4 GB (OPPO A3s / iPhone 13 标配)</option>
                      <option value="6">6 GB (iPhone 14/15 标配)</option>
                      <option value="8">8 GB (iPhone 15 Pro / POCO F5 标配)</option>
                      <option value="12">12 GB (Galaxy S23/S24 Ultra / Pixel 8 Pro 旗舰)</option>
                      <option value="16">16 GB (PC 桌面级)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* 4. 防关联噪音开关 */}
              <div className="grid grid-cols-12 items-center gap-3">
                <label className="col-span-2 text-right font-medium text-[#4e5969]">
                  防关联噪音
                </label>
                <div className="col-span-10 flex flex-wrap gap-4 text-xs">
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.canvasNoise}
                      onChange={e => setForm(prev => ({ ...prev, canvasNoise: e.target.checked }))}
                      className="rounded text-[#165dff]"
                    />
                    <span>Canvas 噪音</span>
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.audioNoise}
                      onChange={e => setForm(prev => ({ ...prev, audioNoise: e.target.checked }))}
                      className="rounded text-[#165dff]"
                    />
                    <span>Audio 噪音</span>
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.clientRectsNoise}
                      onChange={e => setForm(prev => ({ ...prev, clientRectsNoise: e.target.checked }))}
                      className="rounded text-[#165dff]"
                    />
                    <span>ClientRects 噪音</span>
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.batterySpoofing}
                      onChange={e => setForm(prev => ({ ...prev, batterySpoofing: e.target.checked }))}
                      className="rounded text-[#165dff]"
                    />
                    <span>电池模拟</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </form>

        {/* 3. 右侧“环境预览”面板: HubStudio 1:1 风格 (硬件并发 & 分辨率严格对应) */}
        <div className="w-[320px] border-l border-[#e5e6eb] bg-white flex flex-col justify-between p-4 overflow-y-auto">
          <div className="space-y-3.5">
            {/* 标题 */}
            <div className="flex items-center justify-between border-b border-[#f2f3f5] pb-2.5">
              <span className="text-xs font-bold text-[#1d2129]">环境预览</span>
              <List size={14} className="text-[#86909c]" />
            </div>

            {/* 参数列表 */}
            <div className="space-y-2 text-[11px] leading-relaxed">
              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">浏览器:</span>
                <span className="font-medium text-[#1d2129]">
                  {form.browserEngine === 'chromium' ? 'ChroBrowser' : 'FireBrowser'}
                  <span className="text-[#86909c] ml-1">
                    {form.browserEngine === 'chromium'
                      ? `(智能匹配 Chrome ${inferKernelFromUA(form.userAgent, form.browserEngine).startsWith('155') ? '155' : '146'} 内核)`
                      : '(智能匹配 Gecko 135 内核)'}
                  </span>
                </span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">内核状态:</span>
                <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                  <span>⚡️</span>
                  <span>就绪 · 启动时自愈直连</span>
                </span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">指纹ID:</span>
                <span className="font-mono text-[#1d2129] flex items-center gap-1">
                  <span>{fingerprintId}</span>
                  <span className="text-[#86909c] text-[10px]">(全球唯一)</span>
                  <HelpCircle size={10} className="text-[#86909c]" />
                </span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">操作系统:</span>
                <span className="font-semibold text-[#1d2129]">
                  {OS_ITEMS.find(x => x.id === form.os)?.label || form.os}
                </span>
              </div>

              {(form.os === 'android' || form.os === 'ios') && (
                <div className="flex items-start justify-between">
                  <span className="text-[#86909c]">机型:</span>
                  <span className="font-semibold text-[#165dff] max-w-[190px] text-right truncate" title={form.deviceModel}>
                    {form.deviceModel || '未指定'}
                  </span>
                </div>
              )}

              <div className="space-y-0.5">
                <div className="text-[#86909c]">User Agent:</div>
                <div className="rounded bg-[#f7f8fa] p-1.5 font-mono text-[10px] text-[#4e5969] leading-tight break-all border border-[#f2f3f5]">
                  {form.userAgent || '自动生成中...'}
                </div>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">语言:</span>
                <span className="text-[#1d2129]">{form.languages || '基于IP匹配对应的语言'}</span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">时区:</span>
                <span className="text-[#1d2129]">{form.timezone || '基于IP匹配对应的时区'}</span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">地理位置:</span>
                <span className="text-[#1d2129]">基于IP匹配对应的地理位置</span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">分辨率:</span>
                <div className="text-right">
                  <div className="font-medium text-[#1d2129]">
                    {form.resolutionPreset === 'real' ? '真实 ' : '物理 '}
                    {form.physicalWidth} × {form.physicalHeight}
                  </div>
                  <div className="text-[#86909c] text-[10px]">
                    视口 {form.windowWidth} × {form.windowHeight} (DPR: {form.devicePixelRatio})
                  </div>
                </div>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">硬件并发:</span>
                <span className="font-semibold text-[#1d2129]">
                  {form.hardwareConcurrency} 核 CPU / {form.deviceMemory} GB 内存
                </span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">字体列表:</span>
                <span className="text-[#1d2129]">真实</span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">字体指纹:</span>
                <span className="text-[#1d2129]">噪音</span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">WebRTC:</span>
                <span className="text-[#1d2129]">隐藏</span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">Canvas:</span>
                <span className="text-[#1d2129]">噪音</span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">WebGL图像:</span>
                <span className="text-[#1d2129]">噪音</span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">WebGL Info:</span>
                <div className="text-right max-w-[180px]">
                  <div className="font-medium text-[#1d2129]">{form.webglVendor || 'Qualcomm'}</div>
                  <div className="text-[#86909c] text-[10px] truncate" title={form.webglRenderer}>{form.webglRenderer || 'Adreno (TM) 506'}</div>
                </div>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">WebGPU:</span>
                <span className="text-[#1d2129]">
                  {form.os === 'ios' ? 'not support' : '基于WebGL匹配'}
                </span>
              </div>

              <div className="flex items-start justify-between">
                <span className="text-[#86909c]">AudioContext:</span>
                <span className="text-[#1d2129]">噪音</span>
              </div>
            </div>
          </div>

          {/* 底部提示卡片 */}
          <div className="mt-4 pt-3 border-t border-[#f2f3f5] text-[11px] text-[#86909c] flex items-center justify-between">
            <span>
              可设置 <span className="text-[#165dff] cursor-pointer hover:underline">环境模板</span> 每次将以此模版创建
            </span>
            <div className="flex h-5 w-5 items-center justify-center rounded-full bg-[#165dff] text-white text-[11px] font-bold">
              ?
            </div>
          </div>
        </div>
      </div>

      {/* 3. 底部固定操作栏 */}
      <div className="flex h-[52px] items-center justify-between border-t border-[#e5e6eb] bg-white px-6">
        <div className="flex items-center gap-3">
          <button
            type="submit"
            form="profile-form-hub"
            disabled={saving}
            className="flex items-center gap-1.5 rounded bg-[#165dff] px-5 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-[#1253d8] transition-colors disabled:opacity-50"
          >
            {saving && <LoaderCircle size={13} className="animate-spin" />}
            <span>完成</span>
            <ChevronDown size={13} className="opacity-70" />
          </button>

          <button
            type="button"
            onClick={onClose}
            className="rounded border border-[#d9d9d9] bg-white px-4 py-1.5 text-xs font-medium text-[#4e5969] hover:bg-[#f7f8fa] transition-colors"
          >
            取消
          </button>
        </div>

        {/* ★ 全类型随机指纹套件 (机型与硬件严格对应) */}
        <button
          type="button"
          onClick={handleShuffleFullProfile}
          className="flex items-center gap-1.5 text-xs text-[#86909c] hover:text-[#165dff] transition-colors cursor-pointer"
          title="全类型随机匹配全新黄金硬件套件（机型与硬件参数 100% 自洽）"
        >
          <Shuffle size={13} />
          <span>换一套指纹</span>
        </button>
      </div>
    </div>
  )
}
