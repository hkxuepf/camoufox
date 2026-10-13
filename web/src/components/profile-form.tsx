'use client'

import { useEffect, useMemo, useState } from 'react'
import { Check, Info, LoaderCircle, RefreshCw, TriangleAlert, X } from 'lucide-react'

import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { useI18n } from '@/lib/i18n'
import {
  getCountryProfile,
  getLanguagesForCountry,
  getTimezoneForCountry,
} from '@/lib/country-languages'
import {
  hasGeography,
  isStaleWrite,
  OS_LABELS,
  presetsAPI,
  profilesAPI,
  proxiesAPI,
  type DevicePreset,
  type FingerprintSummary,
  type Group,
  type Profile,
  type ProxyCheck,
  type ProxyItem,
  type ProxyLocation,
} from '@/lib/api'

interface FormState {
  name: string
  group: string
  status: string
  notes: string
  os: string
  browserUi: 'desktop' | 'camoufox'
  browserEngine: 'chromium' | 'camoufox'
  userAgent: string
  timezone: string
  languages: string
  hardwareConcurrency: string
  deviceMemory: string
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
  proxyType: string
  proxyServer: string
  proxyUsername: string
  proxyPassword: string
}

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPod|iPad/.test(navigator.platform || navigator.userAgent);

export const WEBGL_PRESETS = [
  { label: '自动默认 (跟随底层真实显卡)', vendor: '', renderer: '' },
  { label: 'Apple M4 (Apple Metal GPU)', vendor: 'Apple', renderer: 'Apple M4' },
  { label: 'Apple M3 Max (Apple Metal GPU)', vendor: 'Apple', renderer: 'Apple M3 Max' },
  { label: 'NVIDIA GeForce RTX 4090', vendor: 'Google Inc. (NVIDIA)', renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
  { label: 'NVIDIA GeForce RTX 4070', vendor: 'Google Inc. (NVIDIA)', renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
  { label: 'AMD Radeon RX 7800 XT', vendor: 'Google Inc. (AMD)', renderer: 'ANGLE (AMD, AMD Radeon RX 7800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)' },
  { label: 'Intel Iris Xe Graphics', vendor: 'Google Inc. (Intel)', renderer: 'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)' },
]

function WindowsIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 88 88" fill="currentColor">
      <path d="M0 12.402l35.687-4.86.016 34.423-35.67.202L0 12.402zm35.67 33.529l.028 34.453L.028 75.48.016 45.728l35.654.203zm4.383-39.124L87.488 0v41.524l-47.435.31V6.807zm47.459 39.029l-.024 42.164-47.435-6.674V45.526l47.459.31z" />
    </svg>
  )
}

function AppleIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 170 170" fill="currentColor">
      <path d="M150.37 130.25c-2.45 5.66-5.35 10.87-8.71 15.66-4.58 6.53-8.33 11.05-11.22 13.56-4.48 4.12-9.28 6.23-14.42 6.35-3.69 0-8.14-1.05-13.32-3.18-5.19-2.12-9.97-3.17-14.34-3.17-4.58 0-9.49 1.05-14.75 3.17-5.26 2.13-9.5 3.24-12.74 3.35-4.35.13-9.16-1.9-14.42-6.08-3.69-3.04-7.67-7.81-11.96-14.34-6.42-9.78-11.44-20.73-15.06-32.84-3.62-12.12-5.43-23.73-5.43-34.84 0-14.35 3.59-26.4 10.77-36.14 7.18-9.74 16.27-14.72 27.27-14.93 4.89 0 10.15 1.34 15.78 4.02 5.63 2.68 9.53 4.07 11.71 4.19 1.9.11 6.03-1.42 12.39-4.58 6.36-3.17 12.01-4.53 16.96-4.09 13.04 1.09 23.37 6.32 30.99 15.69-11.53 6.96-17.18 16.53-16.96 28.71.22 9.57 3.86 17.51 10.93 23.82 7.07 6.31 15.33 10.01 24.79 11.1-2.28 7.07-5.16 14.14-8.63 21.21zM119.22 31.84c0-7.29 2.63-14.18 7.89-20.67 5.26-6.49 11.83-10.55 19.7-12.17.65 1.74.98 3.59.98 5.55 0 7.39-2.8 14.44-8.4 21.16-5.6 6.72-12.33 10.64-20.17 11.76v-5.63z" />
    </svg>
  )
}

function LinuxIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C9.5 2 7.5 4 7.5 6.5c0 1.5.5 2.5 1.5 3.5-.5 1-1.5 2.5-1.5 4.5 0 2 1.5 3.5 3 4 .5.5 1 1.5 1 2.5v1h1v-1c0-1 .5-2 1-2.5 1.5-.5 3-2 3-4 0-2-1-3.5-1.5-4.5 1-1 1.5-2 1.5-3.5C16.5 4 14.5 2 12 2z"/>
    </svg>
  )
}

function AndroidIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 18c0 .55.45 1 1 1h1v3.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5V19h2v3.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5V19h1c.55 0 1-.45 1-1V8H6v10zM3.5 8C2.67 8 2 8.67 2 9.5v6c0 .83.67 1.5 1.5 1.5S5 16.33 5 15.5v-6C5 8.67 4.33 8 3.5 8zm17 0c-.83 0-1.5.67-1.5 1.5v6c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-6c0-.83-.67-1.5-1.5-1.5zm-4.97-4.84l1.3-1.3c.2-.2.2-.51 0-.71s-.51-.2-.71 0l-1.48 1.48C13.85 2.23 12.95 2 12 2c-.96 0-1.86.23-2.66.63L7.85 1.15c-.2-.2-.51-.2-.71 0s-.2.51 0 .71l1.31 1.31C6.97 4.26 6 6.01 6 8h12c0-1.99-.97-3.75-2.47-4.84zM10 5H9V4h1v1zm5 0h-1V4h1v1z"/>
    </svg>
  )
}

function IosIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14zm-5-3c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
    </svg>
  )
}

export const SCREEN_PRESETS = [
  { label: '1920 × 1080 (16:9 全高清标准)', w: '1920', h: '1080' },
  { label: '1512 × 982 (MacBook Pro 14" 原生视网膜)', w: '1512', h: '982' },
  { label: '2560 × 1440 (2K QHD 高清)', w: '2560', h: '1440' },
  { label: '1440 × 900 (MacBook Air/Pro)', w: '1440', h: '900' },
  { label: '1366 × 768 (常见笔记本)', w: '1366', h: '768' },
  { label: '1680 × 1050 (16:10 宽屏)', w: '1680', h: '1050' },
  { label: '3840 × 2160 (4K 超高清)', w: '3840', h: '2160' },
]

export const OS_ITEMS = [
  { id: 'windows', label: 'Windows', tag: 'Win 10/11', icon: WindowsIcon, iconColor: 'text-sky-400 group-hover:text-sky-300' },
  { id: 'macos', label: 'macOS', tag: 'Apple Silicon', icon: AppleIcon, iconColor: 'text-zinc-200 group-hover:text-white' },
  { id: 'linux', label: 'Linux', tag: 'Ubuntu / Debian', icon: LinuxIcon, iconColor: 'text-amber-500 group-hover:text-amber-400' },
  { id: 'android', label: 'Android', tag: 'Mobile 14+', icon: AndroidIcon, iconColor: 'text-emerald-400 group-hover:text-emerald-300' },
  { id: 'ios', label: 'iOS', tag: 'iPhone / iPad', icon: IosIcon, iconColor: 'text-indigo-400 group-hover:text-indigo-300' },
]

const EMPTY: FormState = {
  name: '',
  group: '',
  status: 'active',
  notes: '',
  os: isMac ? 'macos' : 'windows',
  browserUi: 'desktop',
  browserEngine: 'chromium',
  userAgent: '',
  timezone: '',
  languages: '',
  hardwareConcurrency: '',
  deviceMemory: '8',
  windowWidth: '1280',
  windowHeight: '720',
  devicePixelRatio: '1',
  webrtcMode: 'replace',
  stableCanvas: false,
  canvasNoise: true,
  audioNoise: true,
  clientRectsNoise: true,
  batterySpoofing: true,
  doNotTrack: false,
  dohProvider: '',
  searchEngine: 'google',
  webglVendor: '',
  webglRenderer: '',
  remoteDebuggingPort: '',
  geoMode: 'auto',
  latitude: '',
  longitude: '',
  proxyType: 'none',
  proxyServer: '',
  proxyUsername: '',
  proxyPassword: '',
}

function fromProfile(profile: Profile): FormState {
  const bs = profile.browser_settings ?? {}
  const proxy = profile.proxy_config ?? {}
  const geo = bs.geolocation
  const lat = geo?.lat ?? geo?.latitude
  const lon = geo?.lon ?? geo?.longitude
  return {
    name: profile.name,
    group: profile.group ?? '',
    status: profile.status,
    notes: profile.notes ?? '',
    os: bs.os ?? 'windows',
    browserUi: bs.browser_ui ?? 'desktop',
    browserEngine: bs.browser_engine ?? 'camoufox',
    userAgent: bs.user_agent ?? '',
    timezone: bs.timezone ?? '',
    languages: (bs.languages ?? []).join(', '),
    hardwareConcurrency: bs.hardware_concurrency ? String(bs.hardware_concurrency) : '',
    deviceMemory: bs.device_memory ? String(bs.device_memory) : '',
    windowWidth: String(bs.window_width ?? 1280),
    windowHeight: String(bs.window_height ?? 720),
    devicePixelRatio: String(bs.device_pixel_ratio ?? 1),
    webrtcMode: bs.webrtc_mode ?? 'replace',
    stableCanvas: bs.stable_canvas ?? false,
    canvasNoise: bs.canvas_noise ?? true,
    audioNoise: bs.audio_noise ?? true,
    clientRectsNoise: bs.client_rects_noise ?? true,
    batterySpoofing: bs.battery_spoofing ?? true,
    doNotTrack: bs.do_not_track ?? false,
    dohProvider: bs.doh_provider ?? '',
    searchEngine: bs.search_engine ?? 'google',
    webglVendor: bs.webgl_vendor ?? '',
    webglRenderer: bs.webgl_renderer ?? '',
    remoteDebuggingPort: bs.remote_debugging_port ? String(bs.remote_debugging_port) : '',
    geoMode: lat != null && lon != null ? 'manual' : 'auto',
    latitude: lat != null ? String(lat) : '',
    longitude: lon != null ? String(lon) : '',
    proxyType: proxy.server ? (proxy.type ?? 'http') : 'none',
    proxyServer: proxy.server ?? '',
    proxyUsername: proxy.username ?? '',
    proxyPassword: proxy.password ?? '',
  }
}

/**
 * Which fields differ between the profile this form was opened on and the one
 * now stored — the answer to "changed how?", which is the only part of a
 * conflict a user can act on.
 */
function describeChanges(before: Profile | null, after: Profile): string {
  if (!before) return ''
  const fields: string[] = []
  if (before.name !== after.name) fields.push(`name is now "${after.name}"`)
  if ((before.group ?? null) !== (after.group ?? null))
    fields.push(after.group ? `group is now "${after.group}"` : 'group was cleared')
  if (before.status !== after.status) fields.push(`status is now ${after.status}`)
  if ((before.notes ?? '') !== (after.notes ?? '')) fields.push('notes changed')
  if (JSON.stringify(before.proxy_config ?? null) !== JSON.stringify(after.proxy_config ?? null))
    fields.push('the proxy changed')
  if (JSON.stringify(before.browser_settings) !== JSON.stringify(after.browser_settings))
    fields.push('browser settings changed')
  if (!fields.length) return ''
  // Two is enough to recognise what happened; a full list would not fit a toast.
  const shown = fields.slice(0, 2).join(', ')
  return fields.length > 2 ? `${shown}, and ${fields.length - 2} more` : shown
}

interface Props {
  open: boolean
  /** null = create a new profile. */
  profile: Profile | null
  groups: Group[]
  onClose: () => void
  onSaved: () => void
}

export function ProfileForm({ open, profile, groups, onClose, onSaved }: Props) {
  const { isZh } = useI18n()
  const isEdit = profile !== null
  const [form, setForm] = useState<FormState>(EMPTY)
  const [saving, setSaving] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [refreshingBrowser, setRefreshingBrowser] = useState(false)
  const [checkingProxy, setCheckingProxy] = useState(false)
  const [proxyCheck, setProxyCheck] = useState<ProxyCheck | null>(null)
  const [autoMatchIp, setAutoMatchIp] = useState(true)
  const [detectedLocation, setDetectedLocation] = useState<ProxyLocation | null>(null)
  const [detectingIp, setDetectingIp] = useState(false)
  const [poolProxies, setPoolProxies] = useState<ProxyItem[]>([])
  const [proxySource, setProxySource] = useState<'custom' | 'pool'>('custom')
  const [selectedPoolId, setSelectedPoolId] = useState('')
  const [ipChannel, setIpChannel] = useState('ip2location')
  // The `profile` prop is a snapshot from the list; regenerating or updating the
  // browser returns a new machine, and the panel has to show it without waiting
  // for the dialog to be reopened.
  const [machine, setMachine] = useState<FingerprintSummary | null | undefined>(undefined)
  const [reconciling, setReconciling] = useState(false)
  // Whether the *saved* profile states where it is. The form fields alone cannot
  // answer that once the user has started typing in them.
  const [storedGeography, setStoredGeography] = useState(false)
  const [clearingGeography, setClearingGeography] = useState(false)
  const [presets, setPresets] = useState<DevicePreset[]>([])
  const [presetId, setPresetId] = useState('')
  // The version this form was filled from. Sent with the save so that an edit
  // somebody else made in the meantime is refused instead of being overwritten,
  // and moved on after a refused save so a deliberate second Save can proceed.
  const [baseVersion, setBaseVersion] = useState(0)
  const toast = useToast()

  useEffect(() => {
    if (open) {
      proxiesAPI.list().then((res) => setPoolProxies(res.proxies || [])).catch(() => {})
      // The dialog is kept mounted and refilled when it opens, so the form has
      // to be reset here. A key would avoid the effect, but it would also throw
      // away the loaded presets on every open and would not refill when the
      // same profile is reopened after a save changed it.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm(profile ? fromProfile(profile) : EMPTY)
      setBaseVersion(profile?.row_version ?? 0)
      setMachine(profile?.fingerprint)
      setStoredGeography(profile ? hasGeography(profile) : false)
      setPresetId('')
      setProxyCheck(null)
      setSelectedPoolId('')
      setProxySource('custom')
      if (!profile) {
        setAutoMatchIp(true)
        // Automatically query exit IP and adapt timezone & language for new profile
        detectIpAndAdapt(null, false)
      } else {
        setAutoMatchIp(true)
        if (profile.proxy_check?.ip) {
          setDetectedLocation({
            ip: profile.proxy_check.ip,
            country: profile.proxy_check.country ?? null,
            timezone: profile.proxy_check.timezone ?? null,
            latitude: null,
            longitude: null,
            languages: getLanguagesForCountry(profile.proxy_check.country),
          })
        } else if (profile.proxy_config?.server) {
          detectIpAndAdapt(null, false)
        }
      }
    }
  }, [open, profile])

  const uaPresets = useMemo(() => {
    if (form.browserEngine === 'camoufox') {
      return [
        { label: isZh ? '自动匹配系统与内核 (Firefox 135 原生)' : 'Auto match OS (Firefox 135)', ua: '' },
        { label: 'Firefox 135 (Windows 11 x64)', ua: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0' },
        { label: 'Firefox 135 (macOS ARM64)', ua: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0' },
        { label: 'Firefox 135 (Linux x86_64)', ua: 'Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0' },
        { label: 'Firefox 135 (Android Mobile)', ua: 'Mozilla/5.0 (Android 14; Mobile; rv:135.0) Gecko/135.0 Firefox/135.0' },
        { label: 'Firefox 135 (iOS Mobile)', ua: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/135.0 Mobile/15E148 Safari/605.1.15' },
      ]
    }
    return [
      { label: isZh ? '自动匹配系统与内核 (Chrome 154 智能微抖动)' : 'Auto match OS (Chrome 154)', ua: '' },
      { label: 'Chrome 154 (Windows 11 x64)', ua: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8035.120 Safari/537.36' },
      { label: 'Chrome 154 (macOS ARM64)', ua: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8035.120 Safari/537.36' },
      { label: 'Chrome 154 (Linux x86_64)', ua: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8035.120 Safari/537.36' },
      { label: 'Chrome 154 (Android 14 Mobile)', ua: 'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8035.120 Mobile Safari/537.36' },
      { label: 'Chrome 154 (iOS Mobile)', ua: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/154.0.8035.120 Mobile/15E148 Safari/604.1' },
    ]
  }, [form.browserEngine, isZh])

  // Presets only matter while creating: an existing profile is already pinned.
  useEffect(() => {
    if (!open || isEdit || presets.length) return
    presetsAPI
      .list()
      .then(setPresets)
      .catch(() => setPresets([]))
  }, [open, isEdit, presets.length])

  const presetsForOs = useMemo(
    () => presets.filter((preset) => preset.os === form.os),
    [presets, form.os],
  )

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((current) => ({ ...current, [key]: value }))

  /**
   * A key we send is authoritative and a null clears the value, so a blank
   * optional field has to mean different things in the two modes: on create it
   * means "let the backend generate this", so the key is omitted; on edit the
   * user is looking at the stored value and blanking it means "remove it", so
   * an explicit null goes out. Sending null on create produced profiles with a
   * missing timezone and geolocation — a fingerprint with holes in it.
   */
  function buildBrowserSettings() {
    let languages = form.languages
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)

    if (autoMatchIp && (!languages.length || (languages.length <= 2 && languages[0] === 'en-US'))) {
      if (detectedLocation?.languages?.length) {
        languages = detectedLocation.languages
      }
    }

    const settings: Record<string, unknown> = {
      os: form.os,
      browser_ui: form.browserUi,
      browser_engine: form.browserEngine,
      user_agent: form.userAgent.trim() || null,
      window_width: Number(form.windowWidth) || 1280,
      window_height: Number(form.windowHeight) || 720,
      device_pixel_ratio: Number(form.devicePixelRatio) || 1.0,
      webrtc_mode: form.webrtcMode,
      stable_canvas: form.stableCanvas,
      canvas_noise: form.canvasNoise,
      audio_noise: form.audioNoise,
      client_rects_noise: form.clientRectsNoise,
      battery_spoofing: form.batterySpoofing,
      do_not_track: form.doNotTrack,
      doh_provider: form.dohProvider || null,
      search_engine: form.searchEngine || 'google',
      // Always explicit: "from the proxy IP" must clear any stored coordinates,
      // otherwise geoip stays disabled and the old position keeps applying.
      geolocation:
        form.geoMode === 'manual' && form.latitude && form.longitude
          ? { lat: Number(form.latitude), lon: Number(form.longitude) }
          : null,
    }

    const optional: [string, unknown][] = [
      ['timezone', form.timezone.trim() || null],
      ['languages', languages.length ? languages : null],
      ['hardware_concurrency', form.hardwareConcurrency ? Number(form.hardwareConcurrency) : null],
      ['device_memory', form.deviceMemory ? Number(form.deviceMemory) : null],
      ['webgl_vendor', form.webglVendor.trim() || null],
      ['webgl_renderer', form.webglRenderer.trim() || null],
      ['remote_debugging_port', form.remoteDebuggingPort ? Number(form.remoteDebuggingPort) : null],
    ]
    for (const [key, value] of optional) {
      if (value !== null || isEdit) settings[key] = value
    }
    return settings
  }

  function handleRandomizeFingerprint() {
    const isCamoufox = form.browserEngine === 'camoufox'
    const targetOs = form.os || (isMac ? 'macos' : 'windows')
    const coresList = ['4', '6', '8', '12', '16']
    const ramList = ['4', '8', '16', '32']
    const resolutions = [
      { w: '1920', h: '1080' },
      { w: '2560', h: '1440' },
      { w: '1440', h: '900' },
      { w: '1366', h: '768' },
      { w: '1680', h: '1050' },
    ]
    const dprList = ['1', '1.25', '1.5', '2']
    const gpuPresets = targetOs === 'macos' ? WEBGL_PRESETS.slice(1, 3) : WEBGL_PRESETS.slice(3)
    const randomGpu = gpuPresets[Math.floor(Math.random() * gpuPresets.length)]
    const randomRes = resolutions[Math.floor(Math.random() * resolutions.length)]

    let randomUa = ''
    if (isCamoufox) {
      if (targetOs === 'macos') {
        randomUa = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0'
      } else if (targetOs === 'linux') {
        randomUa = 'Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0'
      } else {
        randomUa = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0'
      }
    } else {
      const buildJitter = 8035 + Math.floor(Math.random() * 8)
      const patchJitter = 40 + Math.floor(Math.random() * 150)
      const jitteredVersion = `154.0.${buildJitter}.${patchJitter}`
      randomUa = targetOs === 'macos'
        ? `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${jitteredVersion} Safari/537.36`
        : `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${jitteredVersion} Safari/537.36`
    }

    setForm((prev) => ({
      ...prev,
      userAgent: randomUa,
      hardwareConcurrency: coresList[Math.floor(Math.random() * coresList.length)],
      deviceMemory: ramList[Math.floor(Math.random() * ramList.length)],
      windowWidth: randomRes.w,
      windowHeight: randomRes.h,
      devicePixelRatio: dprList[Math.floor(Math.random() * dprList.length)],
      webglVendor: randomGpu.vendor,
      webglRenderer: randomGpu.renderer,
      clientRectsNoise: true,
      audioNoise: true,
      canvasNoise: true,
      batterySpoofing: true,
    }))
    toast('info', isZh ? `已随机生成新指纹特征 (${isCamoufox ? 'Firefox 135' : 'Chrome 154'})` : 'Fingerprint randomized')
  }

  function handleSelectEngine(engine: 'chromium' | 'camoufox') {
    set('browserEngine', engine)
    const isCamoufox = engine === 'camoufox'
    const buildJitter = 8035 + Math.floor(Math.random() * 8)
    const patchJitter = 40 + Math.floor(Math.random() * 150)
    const jitteredVer = `154.0.${buildJitter}.${patchJitter}`

    let ua = ''
    if (isCamoufox) {
      if (form.os === 'macos') {
        ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0'
      } else if (form.os === 'linux') {
        ua = 'Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0'
      } else if (form.os === 'android') {
        ua = 'Mozilla/5.0 (Android 14; Mobile; rv:135.0) Gecko/135.0 Firefox/135.0'
      } else if (form.os === 'ios') {
        ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/135.0 Mobile/15E148 Safari/605.1.15'
      } else {
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0'
      }
    } else {
      if (form.os === 'android') {
        ua = `Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${jitteredVer} Mobile Safari/537.36`
      } else if (form.os === 'ios') {
        ua = `Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/${jitteredVer} Mobile/15E148 Safari/604.1`
      } else if (form.os === 'macos') {
        ua = `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${jitteredVer} Safari/537.36`
      } else if (form.os === 'linux') {
        ua = `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${jitteredVer} Safari/537.36`
      } else {
        ua = `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${jitteredVer} Safari/537.36`
      }
    }
    set('userAgent', ua)
  }

  function handleSelectOs(targetOs: string) {
    const isCamoufox = form.browserEngine === 'camoufox'
    const buildJitter = 8035 + Math.floor(Math.random() * 8)
    const patchJitter = 40 + Math.floor(Math.random() * 150)
    const jitteredVer = `154.0.${buildJitter}.${patchJitter}`

    let ua = ''
    if (isCamoufox) {
      if (targetOs === 'macos') {
        ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0'
      } else if (targetOs === 'linux') {
        ua = 'Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0'
      } else if (targetOs === 'android') {
        ua = 'Mozilla/5.0 (Android 14; Mobile; rv:135.0) Gecko/135.0 Firefox/135.0'
      } else if (targetOs === 'ios') {
        ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/135.0 Mobile/15E148 Safari/605.1.15'
      } else {
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0'
      }
    } else {
      if (targetOs === 'android') {
        ua = `Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${jitteredVer} Mobile Safari/537.36`
      } else if (targetOs === 'ios') {
        ua = `Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/${jitteredVer} Mobile/15E148 Safari/604.1`
      } else if (targetOs === 'macos') {
        ua = `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${jitteredVer} Safari/537.36`
      } else if (targetOs === 'linux') {
        ua = `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${jitteredVer} Safari/537.36`
      } else {
        ua = `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${jitteredVer} Safari/537.36`
      }
    }

    if (targetOs === 'android') {
      setForm((prev) => ({
        ...prev,
        os: 'android',
        windowWidth: '412',
        windowHeight: '915',
        devicePixelRatio: '2.625',
        hardwareConcurrency: '8',
        deviceMemory: '8',
        webglVendor: 'Google Inc. (Qualcomm)',
        webglRenderer: 'ANGLE (Qualcomm, Adreno (TM) 730, OpenGL ES 3.2)',
        userAgent: ua,
      }))
    } else if (targetOs === 'ios') {
      setForm((prev) => ({
        ...prev,
        os: 'ios',
        windowWidth: '393',
        windowHeight: '852',
        devicePixelRatio: '3',
        hardwareConcurrency: '6',
        deviceMemory: '8',
        webglVendor: 'Apple Inc.',
        webglRenderer: 'Apple GPU',
        userAgent: ua,
      }))
    } else if (targetOs === 'macos') {
      setForm((prev) => ({
        ...prev,
        os: 'macos',
        windowWidth: '1440',
        windowHeight: '900',
        devicePixelRatio: '2',
        hardwareConcurrency: '8',
        deviceMemory: '16',
        webglVendor: 'Google Inc. (Apple)',
        webglRenderer: 'ANGLE (Apple, Apple M2, OpenGL 4.1)',
        userAgent: ua,
      }))
    } else if (targetOs === 'linux') {
      setForm((prev) => ({
        ...prev,
        os: 'linux',
        windowWidth: '1920',
        windowHeight: '1080',
        devicePixelRatio: '1',
        hardwareConcurrency: '8',
        deviceMemory: '16',
        webglVendor: 'Google Inc. (Intel)',
        webglRenderer: 'ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)',
        userAgent: ua,
      }))
    } else {
      // windows
      setForm((prev) => ({
        ...prev,
        os: 'windows',
        windowWidth: '1920',
        windowHeight: '1080',
        devicePixelRatio: '1',
        hardwareConcurrency: '8',
        deviceMemory: '16',
        webglVendor: 'Google Inc. (NVIDIA)',
        webglRenderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)',
        userAgent: ua,
      }))
    }
  }

  function handleQuickPasteProxy(raw: string) {
    const text = raw.trim()
    if (!text) return
    let type = form.proxyType === 'none' ? 'http' : form.proxyType
    let server = ''
    let user = ''
    let pass = ''

    if (text.includes('://')) {
      try {
        const url = new URL(text)
        type = url.protocol.replace(':', '')
        server = url.host
        user = decodeURIComponent(url.username || '')
        pass = decodeURIComponent(url.password || '')
      } catch {}
    } else if (text.includes('@')) {
      const [auth, hostPort] = text.split('@')
      const [u, p] = auth.split(':')
      user = u || ''
      pass = p || ''
      server = hostPort || ''
    } else if (text.includes(':')) {
      const parts = text.split(':')
      if (parts.length === 4) {
        server = `${parts[0]}:${parts[1]}`
        user = parts[2]
        pass = parts[3]
      } else if (parts.length === 2) {
        server = `${parts[0]}:${parts[1]}`
      } else {
        server = text
      }
    } else {
      server = text
    }

    setForm((prev) => ({
      ...prev,
      proxyType: type,
      proxyServer: server,
      proxyUsername: user,
      proxyPassword: pass,
    }))
    toast('ok', isZh ? `已快捷解析代理配置: ${server}` : `Parsed proxy: ${server}`)
  }

  function handleSelectPoolProxy(poolId: string) {
    setSelectedPoolId(poolId)
    if (!poolId) return
    const p = poolProxies.find((item) => item.id === poolId)
    if (p) {
      const pServer = p.port ? `${p.server}:${p.port}` : p.server
      setForm((prev) => ({
        ...prev,
        proxyType: p.type || 'http',
        proxyServer: pServer,
        proxyUsername: p.username || '',
        proxyPassword: p.password || '',
      }))
      toast('ok', isZh ? `已选用代理池节点: ${p.name || p.server}` : `Selected proxy: ${p.name || p.server}`)
    }
  }


  function buildProxy() {
    if (form.proxyType === 'none' || !form.proxyServer.trim()) return null
    return {
      type: form.proxyType,
      server: form.proxyServer.trim(),
      username: form.proxyUsername.trim() || undefined,
      password: form.proxyPassword.trim() || undefined,
    }
  }

  function applyLocationToForm(loc: ProxyLocation, notify = false) {
    setDetectedLocation(loc)
    const langs = (loc.languages && loc.languages.length)
      ? loc.languages
      : getLanguagesForCountry(loc.country)
    const tz = loc.timezone || getTimezoneForCountry(loc.country)
    setForm((prev) => ({
      ...prev,
      timezone: tz || prev.timezone,
      languages: langs.join(', '),
    }))
    if (notify) {
      const countryProfile = getCountryProfile(loc.country)
      const flagAndName = countryProfile ? `${countryProfile.flag} ${countryProfile.name}` : (loc.country || '')
      toast('ok', isZh
        ? `已根据 IP 自动适配: ${flagAndName} (时区 ${tz}, 语言 ${langs.slice(0, 2).join(', ')})`
        : `Adapted to IP: ${loc.country || ''} (${tz}, ${langs.slice(0, 2).join(', ')})`
      )
    }
  }

  async function detectIpAndAdapt(proxyOverride?: ReturnType<typeof buildProxy>, notify = false) {
    setDetectingIp(true)
    try {
      const pConf = proxyOverride !== undefined ? proxyOverride : buildProxy()
      const res = await profilesAPI.checkUnsavedProxy({
        proxy_config: pConf,
        browser_settings: buildBrowserSettings(),
      })
      if (res?.reachable && res.location) {
        applyLocationToForm(res.location, notify)
        return res.location
      }
    } catch {
      // Fallback: machine resolved timezone & navigator language
      if (!isEdit && !form.timezone) {
        try {
          const sysTz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai'
          const sysLangs = (navigator.languages && navigator.languages.length)
            ? Array.from(navigator.languages).join(', ')
            : (navigator.language || 'zh-CN, zh, en')
          setForm((prev) => ({
            ...prev,
            timezone: prev.timezone || sysTz,
            languages: prev.languages || sysLangs,
          }))
        } catch {}
      }
    } finally {
      setDetectingIp(false)
    }
    return null
  }

  /**
   * Checks what is on screen rather than what is stored, so the answer belongs to
   * the proxy the user is currently typing — the point is to find out before
   * saving whether it works and whether it agrees with the profile.
   */
  async function handleCheckProxy() {
    setCheckingProxy(true)
    setProxyCheck(null)
    try {
      const res = await profilesAPI.checkUnsavedProxy({
        proxy_config: buildProxy(),
        browser_settings: buildBrowserSettings(),
      })
      setProxyCheck(res)
      if (res?.reachable && res.location) {
        setDetectedLocation(res.location)
        setAutoMatchIp(true)
        applyLocationToForm(res.location, true)
      }
    } catch (error) {
      toast('error', isZh ? '测试代理失败' : 'Could not check the proxy', (error as Error).message)
    } finally {
      setCheckingProxy(false)
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!form.name.trim()) {
      toast('error', 'Name is required')
      return
    }
    if (form.geoMode === 'manual' && (!form.latitude || !form.longitude)) {
      toast('error', 'Manual geolocation needs both latitude and longitude')
      return
    }

    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        group: form.group || null,
        notes: form.notes.trim() || null,
        browser_settings: buildBrowserSettings(),
        proxy_config: buildProxy(),
      }

      if (isEdit) {
        payload.status = form.status
        payload.row_version = baseVersion
        await profilesAPI.updateProfile(profile.id, payload)
        toast('ok', 'Profile updated', form.name.trim())
      } else {
        // The backend generates a consistent fingerprint, then applies these.
        payload.generate_fingerprint = true
        if (presetId) payload.fingerprint_preset = presetId
        await profilesAPI.createProfile(payload)
        toast(
          'ok',
          'Profile created',
          presetId ? `${form.name.trim()} · pinned to a real device` : form.name.trim(),
        )
      }
      onSaved()
      onClose()
    } catch (err) {
      if (isStaleWrite(err) && profile) {
        await handleStaleWrite(profile.id)
        return
      }
      toast('error', isEdit ? 'Could not update profile' : 'Could not create profile', String(err))
    } finally {
      setSaving(false)
    }
  }

  /**
   * Somebody else saved this profile while this form was open.
   *
   * Nothing on screen is replaced: the user's typing is theirs, and a form that
   * rewrites itself under them loses work just as surely as the overwrite this
   * refusal prevented. Instead the stored values are fetched to name what
   * actually changed, and the form is moved onto the current version so that a
   * second Save is a deliberate, informed overwrite rather than a blind one.
   */
  async function handleStaleWrite(profileId: string) {
    try {
      const current = await profilesAPI.getProfile(profileId)
      setBaseVersion(current.row_version)
      setStoredGeography(hasGeography(current))
      setMachine(current.fingerprint)
      const changed = describeChanges(profile, current)
      toast(
        'error',
        'Someone else changed this profile',
        changed
          ? `${changed}. Nothing you typed was lost — press Save again to apply your version.`
          : 'Your edit was not saved. Press Save again to apply your version.',
      )
    } catch {
      // The reload is a courtesy; without it the user still needs to know the
      // save did not land, and that is the part that must never be swallowed.
      toast(
        'error',
        'Someone else changed this profile',
        'Your edit was not saved. Reopen the profile to see the current values.',
      )
    }
  }

  async function handleRefreshBrowser() {
    if (!profile) return
    setRefreshingBrowser(true)
    try {
      const updated = await profilesAPI.refreshBrowserVersion(profile.id)
      setMachine(updated.fingerprint)
      toast(
        'ok',
        `Browser updated to Firefox ${updated.fingerprint?.browser_major}`,
        'The machine is unchanged.',
      )
      onSaved()
    } catch (err) {
      toast('error', 'Could not update the browser version', String(err))
    } finally {
      setRefreshingBrowser(false)
    }
  }

  /**
   * Keeping the machine only moves the dropdown; keeping the setting replaces the
   * hardware, so the two are reported very differently even though one call does
   * both. The form's own OS field follows, or it would still show the value the
   * user has just resolved away from.
   */
  async function handleReconcileOs(keepMachine: boolean) {
    if (!profile) return
    setReconciling(true)
    try {
      const updated = await profilesAPI.reconcileOs(profile.id, keepMachine)
      setMachine(updated.fingerprint)
      set('os', updated.browser_settings.os)
      toast(
        'ok',
        keepMachine
          ? `Set back to ${OS_LABELS[updated.browser_settings.os] ?? updated.browser_settings.os}`
          : 'New machine pinned',
        keepMachine
          ? 'The machine is untouched.'
          : `${updated.fingerprint?.screen} · ${updated.fingerprint?.hardware_concurrency} cores. The old hardware is gone.`,
      )
      onSaved()
    } catch (err) {
      toast('error', 'Could not reconcile the operating system', String(err))
    } finally {
      setReconciling(false)
    }
  }

  async function handleClearGeography() {
    if (!profile) return
    setClearingGeography(true)
    try {
      await profilesAPI.clearGeography([profile.id])
      setForm((current) => ({ ...current, timezone: '', geoMode: 'auto', latitude: '', longitude: '' }))
      setStoredGeography(false)
      toast('ok', 'Timezone and coordinates cleared', 'Both now follow the proxy.')
      onSaved()
    } catch (err) {
      toast('error', 'Could not clear the geography', String(err))
    } finally {
      setClearingGeography(false)
    }
  }

  async function handleRegenerate() {
    if (!profile) return
    setRegenerating(true)
    try {
      const updated = await profilesAPI.resetFingerprint(profile.id)
      setForm(fromProfile(updated))
      setMachine(updated.fingerprint)
      toast('ok', 'Fingerprint regenerated')
      onSaved()
    } catch (err) {
      toast('error', 'Could not regenerate fingerprint', String(err))
    } finally {
      setRegenerating(false)
    }
  }

  return (
    <Modal
      open={open}
      title={isEdit ? (isZh ? '编辑环境' : 'Edit profile') : (isZh ? '新建环境' : 'New profile')}
      subtitle={
        isEdit
          ? (isZh
              ? `${profile.id} · 创建于 ${new Date(profile.created_at).toLocaleDateString()}`
              : `${profile.id} · created ${new Date(profile.created_at).toLocaleDateString()}`)
          : (isZh
              ? '指定环境名称与可选的代理网络。系统将自动为您生成一套真实且一致的防关联指纹。'
              : 'Choose a name and an optional proxy. A consistent fingerprint is generated for you.')
      }
      onClose={onClose}
      width={640}
      footer={
        <>
          <button
            type="button"
            className="btn btn-default mr-auto flex items-center gap-1.5"
            onClick={handleRandomizeFingerprint}
            title={isZh ? '随机生成一套全套硬件、显卡与指纹参数' : 'Randomize all hardware parameters'}
          >
            <span>🎲</span>
            {isZh ? '换一套指纹' : 'Randomize'}
          </button>
          {isEdit && (
            <button
              type="button"
              className="btn btn-default"
              onClick={handleRegenerate}
              disabled={regenerating}
            >
              <RefreshCw size={13} className={regenerating ? 'animate-spin' : ''} />
              {isZh ? '重置指纹' : 'Reset'}
            </button>
          )}
          <button type="button" className="btn btn-default" onClick={onClose}>
            {isZh ? '取消' : 'Cancel'}
          </button>
          <button type="submit" form="profile-form" className="btn btn-primary" disabled={saving}>
            {saving && <LoaderCircle size={13} className="animate-spin" />}
            {isEdit ? (isZh ? '保存更改' : 'Save changes') : (isZh ? '创建环境' : 'Create profile')}
          </button>
        </>
      }
    >
      <form id="profile-form" onSubmit={handleSubmit} className="flex flex-col gap-5">
        <Section title={isZh ? '基本信息' : 'Identity'}>
          <div className="col-span-2">
            <label className="field-label mb-2">
              {isZh ? '浏览器内核' : 'Browser Engine'}
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => handleSelectEngine('chromium')}
                className={`flex flex-col text-left p-3 rounded-lg border transition-all cursor-pointer ${
                  form.browserEngine === 'chromium'
                    ? 'border-accent bg-accent/10 ring-1 ring-accent'
                    : 'border-line hover:border-line-dim bg-raised/50'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1">
                  <span className="font-semibold text-xs flex items-center gap-1.5 text-ink">
                    <span>🚀</span>
                    {isZh ? 'ChroBrowser (智能匹配)' : 'ChroBrowser (Auto-match)'}
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400 border border-blue-500/20">
                    Chrome 154
                  </span>
                </div>
                <span className="text-[11px] text-ink-dim leading-snug">
                  {isZh
                    ? '基于 Chrome 154 真实内核与 UA 智能抖动，底层特性零撕裂'
                    : 'Real Chrome 154 kernel with build jitter & zero feature mismatch'}
                </span>
              </button>

              <button
                type="button"
                onClick={() => handleSelectEngine('camoufox')}
                className={`flex flex-col text-left p-3 rounded-lg border transition-all cursor-pointer ${
                  form.browserEngine === 'camoufox'
                    ? 'border-accent bg-accent/10 ring-1 ring-accent'
                    : 'border-line hover:border-line-dim bg-raised/50'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1">
                  <span className="font-semibold text-xs flex items-center gap-1.5 text-ink">
                    <span>🦊</span>
                    {isZh ? 'FireBrowser (Gecko 内核)' : 'FireBrowser (Gecko)'}
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20">
                    Firefox 135
                  </span>
                </div>
                <span className="text-[11px] text-ink-dim leading-snug">
                  {isZh
                    ? '开源高匿 Gecko 内核，支持高级拟真硬件特征'
                    : 'Anti-detect Firefox Gecko kernel'}
                </span>
              </button>
            </div>
          </div>

          <div className="col-span-2">
            <label className="field-label" htmlFor="pf-name">
              {isZh ? '环境名称' : 'Name'}
            </label>
            <input
              id="pf-name"
              className="field"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="account-1"
              autoFocus
              required
            />
          </div>

          <div>
            <label className="field-label" htmlFor="pf-group">
              {isZh ? '所属分组' : 'Group'}
            </label>
            <select
              id="pf-group"
              className="field"
              value={form.group}
              onChange={(e) => set('group', e.target.value)}
            >
              <option value="">{isZh ? '未分组' : 'No group'}</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </div>

          <div className="col-span-2">
            <div className="flex items-center justify-between mb-2">
              <label className="field-label mb-0" htmlFor="pf-os">
                {isZh ? '模拟操作系统' : 'Operating system'}
              </label>
              <span className="text-[11px] text-ink-faint">
                {isZh ? '选择后将联动重构底层硬件特征与设备分辨率' : 'Hardware & resolution adapt automatically'}
              </span>
            </div>
            <div className="grid grid-cols-5 gap-2.5">
              {OS_ITEMS.map((item) => {
                const isSelected = form.os === item.id
                const IconComp = item.icon
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleSelectOs(item.id)}
                    className={`relative flex flex-col items-center justify-center p-2.5 rounded-xl border text-center transition-all cursor-pointer group select-none ${
                      isSelected
                        ? 'border-accent bg-accent/10 ring-2 ring-accent/30 shadow-sm'
                        : 'border-line/70 hover:border-line-dim bg-raised/40 hover:bg-raised/80'
                    }`}
                  >
                    {isSelected && (
                      <span className="absolute top-1.5 right-1.5 w-3.5 h-3.5 rounded-full bg-accent text-white flex items-center justify-center shadow-xs">
                        <Check size={9} strokeWidth={3} />
                      </span>
                    )}
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center mb-1.5 transition-transform duration-200 group-hover:scale-110 ${
                        isSelected ? 'bg-accent/20' : 'bg-surface/80'
                      }`}
                    >
                      <IconComp className={`w-4 h-4 ${item.iconColor}`} />
                    </div>
                    <span className={`text-xs font-semibold leading-tight ${isSelected ? 'text-ink' : 'text-ink-dim group-hover:text-ink'}`}>
                      {item.label}
                    </span>
                    <span className="text-[10px] text-ink-faint mt-0.5 leading-tight scale-95">
                      {item.tag}
                    </span>
                  </button>
                )
              })}
            </div>
            {/* Once a machine is pinned this setting is not what a page sees, so
                the honest warning is stronger than "the rest stays as it was". */}
            {isEdit && form.os !== (profile.browser_settings?.os ?? 'windows') && (
              <p className="mt-1.5 text-ink-faint">
                {machine?.pinned_os
                  ? (isZh
                      ? `保存此选项不会改变网站端实际看到的特征：当前已固定的底层机器仍然报告为 ${
                          OS_LABELS[machine.pinned_os] ?? machine.pinned_os
                        }。您可在下方的硬件信息面板中进行一致性调和。`
                      : `Saving this changes nothing a page can see: the pinned machine reports ${
                          OS_LABELS[machine.pinned_os] ?? machine.pinned_os
                        } and keeps doing so. The Machine panel then offers both ways out.`)
                  : (isZh
                      ? '屏幕尺寸、地区和字体等保持原样。使用“重新生成指纹”以生成一套与新操作系统完全匹配的指纹组合。'
                      : 'Screen size, locale and fonts stay as they were. Use Regenerate fingerprint for a set that matches the new OS.')}
              </p>
            )}
          </div>

          <div className="col-span-2">
            <div className="flex items-center justify-between mb-1.5">
              <label className="field-label mb-0" htmlFor="pf-ua">
                {isZh ? 'User-Agent (用户代理特征)' : 'User-Agent'}
              </label>
              <select
                className="text-xs py-0.5 px-2 rounded-md border border-line bg-surface text-ink-dim hover:text-ink cursor-pointer focus:outline-none"
                value={form.userAgent}
                onChange={(e) => set('userAgent', e.target.value)}
              >
                {uaPresets.map((p, idx) => (
                  <option key={idx} value={p.ua}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <input
              id="pf-ua"
              className="field font-mono text-xs"
              placeholder={
                form.browserEngine === 'camoufox'
                  ? (isZh ? '留空则自动采用 Firefox 135 原生真实 UA' : 'Default Firefox 135 UA')
                  : (isZh ? '留空则自动采用 Chrome 154 智能微抖动 UA' : 'Default Chrome 154 UA')
              }
              value={form.userAgent}
              onChange={(e) => set('userAgent', e.target.value)}
            />
          </div>

          {isEdit && (
            <div>
              <label className="field-label" htmlFor="pf-status">
                {isZh ? '环境状态' : 'Status'}
              </label>
              <select
                id="pf-status"
                className="field"
                value={form.status}
                onChange={(e) => set('status', e.target.value)}
              >
                <option value="active">{isZh ? '活跃 (Active)' : 'Active'}</option>
                <option value="inactive">{isZh ? '停用 (Inactive)' : 'Inactive'}</option>
                <option value="blocked">{isZh ? '封禁 (Blocked)' : 'Blocked'}</option>
                <option value="maintenance">{isZh ? '维护中 (Maintenance)' : 'Maintenance'}</option>
              </select>
            </div>
          )}

          <div className="col-span-2">
            <label className="field-label" htmlFor="pf-notes">
              {isZh ? '备注说明' : 'Notes'}
            </label>
            <textarea
              id="pf-notes"
              className="field resize-y"
              rows={2}
              value={form.notes}
              onChange={(e) => set('notes', e.target.value)}
              placeholder={isZh ? '记录登录账号密码或业务用途备注' : undefined}
            />
          </div>
        </Section>

        <div className="rounded-xl border border-line bg-surface/50 p-4 space-y-3.5">
          {/* Header */}
          <div className="flex items-center justify-between pb-2 border-b border-line/60">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-xs text-ink">{isZh ? '代理信息' : 'Proxy Settings'}</span>
              <span
                className="text-ink-faint text-xs cursor-help"
                title={isZh ? '配置环境出网代理网络。系统支持本地直连、自定义代理或直接引用已有代理池。' : 'Configure outbound proxy'}
              >
                <Info size={13} />
              </span>
            </div>
            <button
              type="button"
              onClick={() => {
                const next = proxySource === 'custom' ? 'pool' : 'custom'
                setProxySource(next)
                if (next === 'pool' && poolProxies.length > 0 && !selectedPoolId) {
                  handleSelectPoolProxy(poolProxies[0].id)
                }
              }}
              className="text-xs text-accent hover:underline flex items-center gap-1 font-medium cursor-pointer"
            >
              {proxySource === 'custom'
                ? (isZh ? '引用已有代理' : 'Use Existing Proxy')
                : (isZh ? '切换自定义配置' : 'Custom Config')}
            </button>
          </div>

          {/* 代理方式 tabs */}
          <div>
            <label className="field-label mb-1.5">{isZh ? '代理方式' : 'Proxy Mode'}</label>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setProxySource('custom')}
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-all cursor-pointer ${
                  proxySource === 'custom'
                    ? 'border-accent bg-accent/10 text-accent ring-1 ring-accent/30 font-semibold'
                    : 'border-line hover:border-line-dim bg-raised/50 text-ink-dim hover:text-ink'
                }`}
              >
                {isZh ? '自定义' : 'Custom'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setProxySource('pool')
                  if (poolProxies.length > 0 && !selectedPoolId) {
                    handleSelectPoolProxy(poolProxies[0].id)
                  }
                }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-all cursor-pointer ${
                  proxySource === 'pool'
                    ? 'border-accent bg-accent/10 text-accent ring-1 ring-accent/30 font-semibold'
                    : 'border-line hover:border-line-dim bg-raised/50 text-ink-dim hover:text-ink'
                }`}
              >
                {isZh ? '从代理池选用' : 'Select from Pool'}
              </button>
            </div>
          </div>

          {/* 自定义模式 */}
          {proxySource === 'custom' && (
            <>
              <div>
                <label className="field-label" htmlFor="pf-proxy-type">
                  {isZh ? '代理类型*' : 'Proxy Type*'}
                </label>
                <select
                  id="pf-proxy-type"
                  className="field"
                  value={form.proxyType}
                  onChange={(e) => {
                    const newType = e.target.value
                    set('proxyType', newType)
                    if (newType === 'none') {
                      set('proxyServer', '')
                      set('proxyUsername', '')
                      set('proxyPassword', '')
                      setProxyCheck(null)
                    }
                  }}
                >
                  <option value="none">{isZh ? '不使用代理（使用本地网络直连）' : 'No proxy (Direct local connection)'}</option>
                  <option value="http">HTTP</option>
                  <option value="https">HTTPS</option>
                  <option value="socks5">SOCKS5</option>
                </select>
              </div>

              {form.proxyType === 'none' ? (
                <div className="p-2.5 rounded-lg border border-line/60 bg-raised/40 text-xs text-ink-dim">
                  {isZh
                    ? '将使用本机IP，更换上网地点或电脑时IP将变化'
                    : 'Direct connection: Uses your local machine IP. IP will change if your machine moves.'}
                </div>
              ) : (
                <div className="space-y-3 pt-1">
                  <div>
                    <label className="field-label flex items-center justify-between">
                      <span>{isZh ? '快速解析导入' : 'Quick Parse / Paste'}</span>
                      <span className="text-[11px] text-ink-faint font-normal">支持 host:port 或 host:port:user:pass</span>
                    </label>
                    <input
                      className="field font-mono text-xs"
                      placeholder={isZh ? '粘贴代理字符串，系统将自动拆分并填充至下方输入框' : 'Paste proxy text to auto-fill'}
                      onChange={(e) => {
                        handleQuickPasteProxy(e.target.value)
                        e.target.value = ''
                      }}
                    />
                  </div>

                  <div>
                    <label className="field-label" htmlFor="pf-proxy-server">
                      {isZh ? '代理主机及端口*' : 'Server & Port*'}
                    </label>
                    <input
                      id="pf-proxy-server"
                      className="field font-mono"
                      value={form.proxyServer}
                      onChange={(e) => set('proxyServer', e.target.value)}
                      placeholder="例如: 127.0.0.1:7890"
                      required={form.proxyType !== 'none'}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="field-label" htmlFor="pf-proxy-user">
                        {isZh ? '代理用户名' : 'Username'}
                      </label>
                      <input
                        id="pf-proxy-user"
                        className="field"
                        value={form.proxyUsername}
                        onChange={(e) => set('proxyUsername', e.target.value)}
                        placeholder={isZh ? '可选' : 'Optional'}
                        autoComplete="off"
                      />
                    </div>

                    <div>
                      <label className="field-label" htmlFor="pf-proxy-pass">
                        {isZh ? '代理密码' : 'Password'}
                      </label>
                      <input
                        id="pf-proxy-pass"
                        type="password"
                        className="field"
                        value={form.proxyPassword}
                        onChange={(e) => set('proxyPassword', e.target.value)}
                        placeholder={isZh ? '可选' : 'Optional'}
                        autoComplete="new-password"
                      />
                    </div>
                  </div>

                  {form.proxyType.startsWith('socks') &&
                    form.browserEngine === 'camoufox' &&
                    (form.proxyUsername.trim() || form.proxyPassword.trim()) && (
                      <p className="text-danger text-xs">
                        {isZh
                          ? 'Firefox 浏览器内核不支持带账号密码的 SOCKS 认证，这会导致浏览器无法启动。请使用 HTTP/HTTPS 协议，或使用无需密码的白名单 SOCKS 代理。'
                          : 'Firefox cannot authenticate to a SOCKS proxy with credentials. Use HTTP/HTTPS or whitelist-based SOCKS.'}
                      </p>
                    )}
                </div>
              )}
            </>
          )}

          {/* 代理池选用模式 */}
          {proxySource === 'pool' && (
            <div className="space-y-3">
              <div>
                <label className="field-label mb-1">
                  {isZh ? '选择已有代理节点*' : 'Select Proxy from Pool*'}
                </label>
                <select
                  className="field"
                  value={selectedPoolId}
                  onChange={(e) => handleSelectPoolProxy(e.target.value)}
                >
                  <option value="">
                    {poolProxies.length
                      ? (isZh ? '请选择代理池中的节点...' : 'Choose a proxy from pool...')
                      : (isZh ? '暂无可用代理节点，请先在代理池添加' : 'No proxies available in pool')}
                  </option>
                  {poolProxies.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name || p.server} [{p.type?.toUpperCase() || 'HTTP'}] {p.country ? `· ${p.country}` : ''}
                    </option>
                  ))}
                </select>
              </div>

              {selectedPoolId && (
                <div className="p-3 rounded-lg border border-line/60 bg-raised/40 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-ink">{form.proxyType.toUpperCase()} 代理</span>
                    <span className="font-mono text-ink">{form.proxyServer}</span>
                  </div>
                  <div className="text-ink-faint flex items-center justify-between">
                    <span>{form.proxyUsername ? (isZh ? '已配置用户名及密码' : 'Authenticated') : (isZh ? '免密节点' : 'No authentication')}</span>
                    <span className="text-ok font-medium">{isZh ? '已同步至环境' : 'Linked'}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* IP查询渠道 */}
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div>
              <label className="field-label flex items-center gap-1">
                <span>{isZh ? 'IP查询渠道*' : 'IP Database*'}</span>
                <span className="text-ink-faint text-xs cursor-help" title={isZh ? '选择用于检测网络出网IP与地理归属的数据库服务' : 'IP Geo query channel'}>
                  <Info size={12} />
                </span>
              </label>
              <select
                className="field"
                value={ipChannel}
                onChange={(e) => setIpChannel(e.target.value)}
              >
                <option value="ip2location">IP2Location</option>
                <option value="maxmind">MaxMind</option>
                <option value="iphey">Iphey</option>
                <option value="ipinfo">Ipinfo</option>
              </select>
            </div>
          </div>

          {/* 检查网络按钮 */}
          <div className="pt-2">
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="btn btn-default flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium cursor-pointer"
                onClick={handleCheckProxy}
                disabled={checkingProxy}
              >
                {checkingProxy ? (
                  <LoaderCircle size={13} className="animate-spin text-accent" />
                ) : (
                  <RefreshCw size={13} />
                )}
                <span>{checkingProxy ? (isZh ? '正在检查网络…' : 'Checking…') : (isZh ? '检查网络' : 'Check Network')}</span>
              </button>
              <span className="text-xs text-ink-faint">
                {form.proxyType === 'none'
                  ? (isZh ? '测试本机网络直连出网与地理位置' : 'Test direct local network exit')
                  : (isZh ? '测试代理服务器连通性与出网特征' : 'Test proxy connection & exit')}
              </span>
            </div>

            <ProxyCheckResult result={proxyCheck} isZh={isZh} />
          </div>
        </div>

        <details className="rounded-md border border-line p-3" open={isEdit || undefined}>
          <summary className="cursor-pointer font-medium">
            {isZh ? '高级浏览器与防关联指纹参数' : 'Advanced browser and fingerprint settings'}
          </summary>
          <p className="mb-4 mt-1 text-ink-dim">
            {isZh
              ? '默认参数经过严格防指纹关联测试，即开即用。仅当业务需要特殊软硬件特征时才进行修改。'
              : 'Defaults are ready to use. Change these only when a profile needs a specific setup.'}
          </p>
          <div className="flex flex-col gap-5">
          <div>
            <label className="field-label" htmlFor="pf-browser-ui">
              {isZh ? '浏览器界面模式' : 'Browser interface'}
            </label>
            <select id="pf-browser-ui" className="field" value={form.browserUi} onChange={(event) => set('browserUi', event.target.value as FormState['browserUi'])}>
              <option value="desktop">{isZh ? '桌面标准模式 (完整标签页与工具栏)' : 'Desktop (standard tabs and controls)'}</option>
              <option value="camoufox">{isZh ? 'Camoufox 极简模式 (Minimal)' : 'Camoufox (minimal)'}</option>
            </select>
            <p className="mt-1.5 text-ink-dim">
              {isZh
                ? '控制启动后的浏览器窗口外壳样式。不会改变网站识别到的底层操作系统指纹。'
                : 'Controls the browser window interface. It does not change the operating system websites see in your fingerprint.'}
            </p>
          </div>
        {isEdit ? (
          <PinnedMachine
            fingerprint={machine}
            onRefreshBrowser={handleRefreshBrowser}
            refreshing={refreshingBrowser}
            onReconcileOs={handleReconcileOs}
            reconciling={reconciling}
            isZh={isZh}
          />
        ) : (
          <fieldset>
            <legend className="mb-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">
              {isZh ? '硬件特征组合' : 'Machine'}
            </legend>
            <p className="mb-2.5 text-ink-faint">
              {isZh
                ? '自动生成的指纹具备底层一致性；预设设备库则采用真实存在的硬件组合。创建后该环境将永久固定该硬件特征。'
                : 'A generated fingerprint is internally consistent; a preset is a combination that genuinely exists. Either way the profile keeps it for good.'}
            </p>
            <select
              className="field"
              value={presetId}
              onChange={(event) => setPresetId(event.target.value)}
              aria-label="Device preset"
            >
              <option value="">{isZh ? '自动随机生成一套特征' : 'Generate one automatically'}</option>
              {presetsForOs.map((preset) => (
                <option key={preset.id} value={preset.id}>
                  {[preset.screen, `${preset.hardware_concurrency} ${isZh ? '核' : 'cores'}`, shortGpu(preset.gpu)]
                    .filter(Boolean)
                    .join(' · ')}
                </option>
              ))}
            </select>
            {presetsForOs.length > 0 && (
              <p className="mt-1.5 text-ink-faint">
                {isZh ? `现有 ${presetsForOs.length} 个真实 ${form.os} 设备预设可供选用。` : `${presetsForOs.length} real ${form.os} devices available.`}
              </p>
            )}
          </fieldset>
        )}

        <Section
          title={isZh ? '指纹特征细节' : 'Fingerprint'}
          hint={isZh ? 'Camoufox 会确保所有底层指纹特征的自洽，如无必要建议保持默认。' : 'Camoufox keeps the fingerprint internally consistent; only override what you need.'}
        >
          {/* IP 智能自适应联动面板 */}
          <div className="col-span-2 rounded-lg border border-[#bfdbfe] bg-[#eff6ff]/70 p-3 text-xs dark:border-[#1e3a8a] dark:bg-[#0f172a]/70">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="flex cursor-pointer items-center gap-2 font-medium text-[#1e40af] dark:text-[#38bdf8]">
                <input
                  type="checkbox"
                  className="rounded border-line text-signal focus:ring-signal"
                  checked={autoMatchIp}
                  onChange={(e) => {
                    const checked = e.target.checked
                    setAutoMatchIp(checked)
                    if (checked && detectedLocation) {
                      applyLocationToForm(detectedLocation, true)
                    } else if (checked) {
                      detectIpAndAdapt(undefined, true)
                    }
                  }}
                />
                <span>{isZh ? '根据 IP 自动匹配语言与时区 (推荐开启)' : 'Auto-match Languages & Timezone by IP'}</span>
              </label>

              <button
                type="button"
                onClick={() => detectIpAndAdapt(undefined, true)}
                disabled={detectingIp || checkingProxy}
                className="btn btn-sm text-[11px] py-1 px-2.5 bg-white border border-[#93c5fd] text-[#1d4ed8] hover:bg-[#dbeafe] dark:bg-black/40 dark:border-white/10 dark:text-[#38bdf8]"
              >
                {detectingIp ? <LoaderCircle size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                {isZh ? '根据当前 IP 重新适配' : 'Re-sync from IP'}
              </button>
            </div>

            {detectedLocation ? (
              <div className="mt-2.5 flex flex-wrap items-center gap-2 text-[11px] text-ink-dim">
                <span className="inline-flex items-center gap-1 font-semibold text-ink">
                  📍 {detectedLocation.ip}
                  {getCountryProfile(detectedLocation.country) ? (
                    <span className="rounded bg-white/90 px-1.5 py-0.5 border border-line/60 dark:bg-white/10">
                      {getCountryProfile(detectedLocation.country)?.flag} {getCountryProfile(detectedLocation.country)?.name} ({detectedLocation.country})
                    </span>
                  ) : (
                    detectedLocation.country && <span className="rounded bg-white/90 px-1.5 py-0.5 border border-line/60 dark:bg-white/10">{detectedLocation.country}</span>
                  )}
                </span>
                <span className="text-ink-faint">·</span>
                <span>时区: <code className="font-mono font-medium text-[#0284c7] dark:text-[#38bdf8]">{form.timezone || detectedLocation.timezone || 'UTC'}</code></span>
                <span className="text-ink-faint">·</span>
                <span>语言: <code className="font-mono font-medium text-[#0284c7] dark:text-[#38bdf8]">{form.languages || (detectedLocation.languages || []).join(', ') || 'en-US, en'}</code></span>
              </div>
            ) : detectingIp ? (
              <div className="mt-2 flex items-center gap-1.5 text-[11px] text-ink-dim">
                <LoaderCircle size={12} className="animate-spin text-signal" />
                <span>{isZh ? '正在探测出网 IP 地理位置并适配语言地区…' : 'Detecting exit IP and adapting location…'}</span>
              </div>
            ) : null}
          </div>

          <div>
            <label className="field-label flex items-center justify-between" htmlFor="pf-tz">
              <span>{isZh ? '时区' : 'Timezone'}</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    if (detectedLocation) {
                      applyLocationToForm(detectedLocation, true)
                    } else {
                      detectIpAndAdapt(undefined, true)
                    }
                  }}
                  className="text-[10px] font-medium text-emerald-400 hover:text-emerald-300 flex items-center gap-1 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40 transition-colors cursor-pointer"
                  title={isZh ? '一键根据当前代理 IP 自动匹配时区与语言' : 'Auto-match timezone & languages from IP'}
                >
                  ⚡ {isZh ? '按 IP 匹配' : 'Match from IP'}
                </button>
                {autoMatchIp && (
                  <span className="text-[10px] font-normal text-signal">⚡ 自动跟随 IP</span>
                )}
              </div>
            </label>
            <input
              id="pf-tz"
              className="field font-mono"
              value={form.timezone}
              onChange={(e) => set('timezone', e.target.value)}
              placeholder={detectedLocation?.timezone || (isZh ? '自动跟随 IP (如 Asia/Tokyo)' : 'Auto follow IP')}
            />
          </div>

          <div>
            <label className="field-label flex items-center justify-between" htmlFor="pf-langs">
              <span>{isZh ? '系统语言与地区' : 'Languages'}</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    if (detectedLocation) {
                      applyLocationToForm(detectedLocation, true)
                    } else {
                      detectIpAndAdapt(undefined, true)
                    }
                  }}
                  className="text-[10px] font-medium text-emerald-400 hover:text-emerald-300 flex items-center gap-1 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40 transition-colors cursor-pointer"
                  title={isZh ? '一键根据当前代理 IP 自动匹配语言与时区' : 'Auto-match languages & timezone from IP'}
                >
                  ⚡ {isZh ? '按 IP 匹配' : 'Match from IP'}
                </button>
                {autoMatchIp && (
                  <span className="text-[10px] font-normal text-signal">⚡ 自动跟随 IP</span>
                )}
              </div>
            </label>
            <input
              id="pf-langs"
              className="field font-mono"
              value={form.languages}
              onChange={(e) => set('languages', e.target.value)}
              placeholder={
                (detectedLocation?.languages || []).join(', ') ||
                getLanguagesForCountry(detectedLocation?.country).join(', ') ||
                (isZh ? '自动跟随 IP (如 ja-JP, ja, en)' : 'Auto follow IP')
              }
            />
          </div>

          <div>
            <label className="field-label" htmlFor="pf-cores">
              {isZh ? 'CPU 逻辑核心数' : 'CPU cores'}
            </label>
            <input
              id="pf-cores"
              type="number"
              min={1}
              max={32}
              className="field"
              value={form.hardwareConcurrency}
              onChange={(e) => set('hardwareConcurrency', e.target.value)}
              placeholder={isZh ? '自动' : 'auto'}
            />
          </div>

          <div>
            <label className="field-label" htmlFor="pf-memory">
              {isZh ? '设备内存 (RAM)' : 'Device Memory'}
            </label>
            <select
              id="pf-memory"
              className="field"
              value={form.deviceMemory}
              onChange={(e) => set('deviceMemory', e.target.value)}
            >
              <option value="">{isZh ? '自动默认' : 'Auto'}</option>
              <option value="2">2 GB</option>
              <option value="4">4 GB</option>
              <option value="8">8 GB (推荐)</option>
              <option value="16">16 GB</option>
              <option value="32">32 GB</option>
            </select>
          </div>

          <div>
            <label className="field-label" htmlFor="pf-webrtc">
              WebRTC
            </label>
            <select
              id="pf-webrtc"
              className="field"
              value={form.webrtcMode}
              onChange={(e) => set('webrtcMode', e.target.value)}
            >
              <option value="replace">{isZh ? '替换为代理 IP 地址 (推荐)' : 'Replace with proxy IP'}</option>
              <option value="real">{isZh ? '暴露真实公网 IP' : 'Use the real IP'}</option>
              <option value="forward">{isZh ? '转发模式' : 'Forward'}</option>
              <option value="none">{isZh ? '完全禁用 WebRTC (最高隐私)' : 'Disable WebRTC'}</option>
            </select>
          </div>

          <div className="col-span-2">
            <label className="field-label" htmlFor="pf-canvas">
              {isZh ? 'Canvas 渲染保护' : 'Canvas'}
            </label>
            <select
              id="pf-canvas"
              className="field"
              value={form.stableCanvas ? 'stable' : 'randomised'}
              onChange={(e) => set('stableCanvas', e.target.value === 'stable')}
            >
              <option value="randomised">{isZh ? '每次会话随机注入噪点 (防追踪默认)' : 'Randomised each session (default)'}</option>
              <option value="stable">{isZh ? '每次启动保持相同指纹 (像真实电脑)' : 'Same canvas every launch'}</option>
            </select>
            <p className="mt-1.5 text-ink-faint">
              {form.stableCanvas
                ? (isZh
                    ? '跨会话保持相同的 Canvas 指纹，如同真实硬件设备。'
                    : 'Reads the same to a site across launches, like real hardware — but also the same on every site, so sites can link this profile between them.')
                : (isZh
                    ? '网站每次看到的 Canvas 图像均带有独特噪点，有效防止跨站追踪，适合养号与多账号防封。'
                    : "A site sees a different canvas each session, and a different one per site. Safer against tracking, but a long-lived account looks like new hardware every visit.")}
            </p>
          </div>

          <div className="col-span-2 rounded-lg border border-line bg-raised/40 p-3.5">
            <div className="flex items-center justify-between mb-2">
              <label className="field-label mb-0" htmlFor="pf-webgl-preset">
                {isZh ? 'WebGL 显卡渲染硬件特征 (GPU Spoofing)' : 'WebGL GPU Spoofing'}
              </label>
              <span className="text-[11px] text-ink-dim">
                {isZh ? '真实设备显卡预设' : 'Hardware Presets'}
              </span>
            </div>
            <select
              id="pf-webgl-preset"
              className="field mb-3"
              onChange={(e) => {
                const idx = Number(e.target.value)
                const preset = WEBGL_PRESETS[idx]
                if (preset) {
                  set('webglVendor', preset.vendor)
                  set('webglRenderer', preset.renderer)
                }
              }}
            >
              {WEBGL_PRESETS.map((p, idx) => (
                <option key={idx} value={idx}>
                  {p.label}
                </option>
              ))}
            </select>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-[11px] text-ink-dim block mb-1">WebGL Vendor</span>
                <input
                  className="field font-mono text-xs"
                  placeholder="Apple / Google Inc. (NVIDIA)"
                  value={form.webglVendor}
                  onChange={(e) => set('webglVendor', e.target.value)}
                />
              </div>
              <div>
                <span className="text-[11px] text-ink-dim block mb-1">WebGL Renderer</span>
                <input
                  className="field font-mono text-xs"
                  placeholder="Apple M4 / ANGLE (...)"
                  value={form.webglRenderer}
                  onChange={(e) => set('webglRenderer', e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="col-span-2">
            <label className="field-label" htmlFor="pf-cdp-port">
              {isZh ? '自动化远程调试端口 (CDP Remote Port)' : 'Remote Debugging Port (CDP)'}
            </label>
            <input
              id="pf-cdp-port"
              type="number"
              min={1024}
              max={65535}
              className="field font-mono"
              placeholder="9222 (可选)"
              value={form.remoteDebuggingPort}
              onChange={(e) => set('remoteDebuggingPort', e.target.value)}
            />
            <p className="mt-1 text-ink-faint">
              {isZh
                ? '配置固定端口后，可通过 Selenium / Puppeteer / Playwright 等自动化工具直接连接接管浏览器。'
                : 'Allow automation frameworks to connect via Chrome DevTools Protocol.'}
            </p>
          </div>

          <div className="col-span-2">
            <div className="flex items-center justify-between mb-1">
              <label className="field-label mb-0">
                {isZh ? '窗口分辨率' : 'Resolution'}
              </label>
              <select
                className="text-xs py-0.5 px-2 rounded border border-line bg-surface text-ink-dim"
                onChange={(e) => {
                  const idx = Number(e.target.value)
                  const p = SCREEN_PRESETS[idx]
                  if (p) {
                    set('windowWidth', p.w)
                    set('windowHeight', p.h)
                  }
                }}
              >
                <option value="">{isZh ? '快速预设分辨率…' : 'Screen presets…'}</option>
                {SCREEN_PRESETS.map((p, idx) => (
                  <option key={idx} value={idx}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-[11px] text-ink-dim block mb-1">{isZh ? '宽度 (px)' : 'Width'}</span>
                <input
                  id="pf-win-w"
                  type="number"
                  className="field"
                  value={form.windowWidth}
                  onChange={(e) => set('windowWidth', e.target.value)}
                />
              </div>
              <div>
                <span className="text-[11px] text-ink-dim block mb-1">{isZh ? '高度 (px)' : 'Height'}</span>
                <input
                  id="pf-win-h"
                  type="number"
                  className="field"
                  value={form.windowHeight}
                  onChange={(e) => set('windowHeight', e.target.value)}
                />
              </div>
            </div>
          </div>

          <div>
            <label className="field-label" htmlFor="pf-dpr">
              {isZh ? '设备像素比 (DPR / 缩放)' : 'Device Pixel Ratio'}
            </label>
            <select
              id="pf-dpr"
              className="field"
              value={form.devicePixelRatio}
              onChange={(e) => set('devicePixelRatio', e.target.value)}
            >
              <option value="1">1.0 (标准普通屏幕)</option>
              <option value="1.25">1.25 (常见 125% 缩放)</option>
              <option value="1.5">1.5 (高分屏 150% 缩放)</option>
              <option value="2">2.0 (Retina 视网膜双倍高清)</option>
            </select>
          </div>

          <div>
            <label className="field-label" htmlFor="pf-doh">
              {isZh ? '安全 DNS (DoH 加密)' : 'DNS over HTTPS'}
            </label>
            <select
              id="pf-doh"
              className="field"
              value={form.dohProvider}
              onChange={(e) => set('dohProvider', e.target.value)}
            >
              <option value="">{isZh ? '系统默认 (关闭 DoH)' : 'Default (Off)'}</option>
              <option value="cloudflare">Cloudflare (1.1.1.1 安全防泄漏)</option>
              <option value="google">Google DNS (8.8.8.8)</option>
              <option value="alidns">AliDNS (阿里云公共加密DNS)</option>
            </select>
          </div>

          <div className="col-span-2">
            <label className="field-label" htmlFor="pf-search">
              {isZh ? '默认搜索引擎 (激活地址栏搜索)' : 'Default Search Engine'}
            </label>
            <select
              id="pf-search"
              className="field"
              value={form.searchEngine}
              onChange={(e) => set('searchEngine', e.target.value)}
            >
              <option value="google">{isZh ? '🔍 Google 搜索 (默认 · 全球主流)' : 'Google Search'}</option>
              <option value="bing">{isZh ? '🔍 Microsoft Bing 搜索 (必应)' : 'Microsoft Bing'}</option>
              <option value="baidu">{isZh ? '🔍 百度搜索 (Baidu · 国内网络优化)' : 'Baidu Search'}</option>
              <option value="duckduckgo">{isZh ? '🔍 DuckDuckGo (高隐私无追踪)' : 'DuckDuckGo'}</option>
            </select>
            <p className="mt-1 text-ink-faint">
              {isZh
                ? '激活浏览器地址栏即时搜索，彻底解决关键词被误识别为错误 IP / 域名的问题。'
                : 'Activates address bar direct search. Prevents keywords from resolving as invalid hostnames.'}
            </p>
          </div>

          <div className="col-span-2 rounded-lg border border-line bg-surface/30 p-3.5 flex flex-col gap-2.5">
            <span className="text-xs font-semibold text-ink">
              {isZh ? '高级隐蔽性与防关联保护开关' : 'Advanced Stealth & Spoofing'}
            </span>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <label className="flex items-center gap-2 cursor-pointer text-ink-dim hover:text-ink">
                <input
                  type="checkbox"
                  checked={form.batterySpoofing}
                  onChange={(e) => set('batterySpoofing', e.target.checked)}
                  className="rounded border-line"
                />
                <span>{isZh ? '模拟固定 100% 充电中 (防电池API追踪)' : 'Battery API Spoofing'}</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-ink-dim hover:text-ink">
                <input
                  type="checkbox"
                  checked={form.clientRectsNoise}
                  onChange={(e) => set('clientRectsNoise', e.target.checked)}
                  className="rounded border-line"
                />
                <span>{isZh ? 'ClientRects DOM 元素尺寸微扰' : 'ClientRects Noise'}</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-ink-dim hover:text-ink">
                <input
                  type="checkbox"
                  checked={form.audioNoise}
                  onChange={(e) => set('audioNoise', e.target.checked)}
                  className="rounded border-line"
                />
                <span>{isZh ? 'AudioContext 音频指纹噪点保护' : 'AudioContext Noise'}</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-ink-dim hover:text-ink">
                <input
                  type="checkbox"
                  checked={form.doNotTrack}
                  onChange={(e) => set('doNotTrack', e.target.checked)}
                  className="rounded border-line"
                />
                <span>{isZh ? '启用 Do Not Track (DNT) 请求头' : 'Send Do Not Track'}</span>
              </label>
            </div>
          </div>

          <div>
            <label className="field-label" htmlFor="pf-geo">
              {isZh ? '地理位置定位 (GPS)' : 'Geolocation'}
            </label>
            <select
              id="pf-geo"
              className="field"
              value={form.geoMode}
              onChange={(e) => set('geoMode', e.target.value as 'auto' | 'manual')}
            >
              <option value="auto">{isZh ? '跟随代理 IP 归属地自动匹配' : 'From the proxy IP'}</option>
              <option value="manual">{isZh ? '手动指定经纬度' : 'Set coordinates'}</option>
            </select>
          </div>

          {form.geoMode === 'manual' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="field-label" htmlFor="pf-lat">
                  {isZh ? '纬度 (Latitude)' : 'Latitude'}
                </label>
                <input
                  id="pf-lat"
                  className="field font-mono"
                  value={form.latitude}
                  onChange={(e) => set('latitude', e.target.value)}
                  placeholder="52.52"
                />
              </div>
              <div>
                <label className="field-label" htmlFor="pf-lon">
                  {isZh ? '经度 (Longitude)' : 'Longitude'}
                </label>
                <input
                  id="pf-lon"
                  className="field font-mono"
                  value={form.longitude}
                  onChange={(e) => set('longitude', e.target.value)}
                  placeholder="13.405"
                />
              </div>
            </div>
          )}

          {/* Until recently every new profile was given the timezone and
              coordinates of a randomly chosen region, so an old one can claim
              Shanghai on a German proxy. Nothing recorded which values were
              chosen and which were rolled, so this is offered whenever both are
              set rather than guessed at. */}
          {isEdit && storedGeography && (
            <div className="col-span-2 rounded-md border border-line bg-raised p-2.5">
              <p className="text-ink">
                {isZh ? '此环境当前指定了自定义地理位置，而非跟随代理 IP。' : 'This profile states where it is instead of taking it from its proxy.'}
              </p>
              <p className="mt-0.5 text-ink-faint">
                {isZh
                  ? '若将其留空，Camoufox 将自动根据代理 IP 的出口节点推导匹配的时区、GPS 坐标和 WebRTC 地址。'
                  : 'A profile created today leaves both unset, so Camoufox derives the timezone, the coordinates and the WebRTC address from the exit address.'}
              </p>
              <div className="mt-2 flex justify-end">
                <button
                  type="button"
                  className="btn btn-default"
                  onClick={handleClearGeography}
                  disabled={clearingGeography}
                >
                  {clearingGeography && <LoaderCircle size={13} className="animate-spin" />}
                  {isZh ? '清除自定义，完全跟随代理' : 'Clear both, follow the proxy'}
                </button>
              </div>
            </div>
          )}
        </Section>
          </div>
        </details>
      </form>
    </Modal>
  )
}

/**
 * Reduce a renderer string to the card name.
 *
 *   "ANGLE (NVIDIA, NVIDIA GeForce GTX 980 Direct3D11 vs_5_0 ps_5_0)" -> "NVIDIA GeForce GTX 980"
 *   "Apple M1, or similar"                                           -> "Apple M1"
 *
 * Unwrapping ANGLE first matters: vendor names contain their own brackets
 * ("Intel(R) HD Graphics"), so cutting at the first one truncates the name.
 */
function shortGpu(gpu?: string | null): string {
  if (!gpu) return ''
  // Drop Camoufox's ", or similar" suffix before unwrapping, or the closing
  // bracket of the ANGLE wrapper is no longer at the end of the string.
  const base = gpu.replace(/,\s*or similar\s*$/i, '')
  const angle = base.match(/^ANGLE \([^,]+,\s*(.*)\)$/)
  const name = angle ? angle[1] : base
  return name.split(/\s+Direct3D|\s+vs_/)[0].trim()
}

/**
 * The machine a profile is pinned to. Without this the profile would look like
 * different hardware every session, so it is worth showing that it does not.
 */
function PinnedMachine({
  fingerprint,
  onRefreshBrowser,
  refreshing,
  onReconcileOs,
  reconciling,
  isZh = false,
}: {
  fingerprint?: FingerprintSummary | null
  onRefreshBrowser: () => void
  refreshing: boolean
  onReconcileOs: (keepMachine: boolean) => void
  reconciling: boolean
  isZh?: boolean
}) {
  if (!fingerprint) {
    return (
      <fieldset>
        <legend className="mb-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">
          {isZh ? '硬件特征' : 'Machine'}
        </legend>
        <p className="text-ink-faint">
          {isZh
            ? '首次启动时生成并固定，之后每次启动保持完全一致，如同真实固定的电脑。'
            : 'Assigned on the first launch, then reused every time so this profile stays the same computer.'}
        </p>
      </fieldset>
    )
  }

  const rows: [string, string | number | null | undefined][] = [
    [isZh ? '内核版本' : 'Browser', fingerprint.browser_major ? `Firefox ${fingerprint.browser_major}` : null],
    [isZh ? '屏幕分辨率' : 'Screen', fingerprint.screen],
    [isZh ? 'CPU 核心数' : 'CPU cores', fingerprint.hardware_concurrency ? `${fingerprint.hardware_concurrency} ${isZh ? '核' : 'cores'}` : null],
    [isZh ? '显卡渲染器' : 'GPU', fingerprint.gpu],
    [isZh ? '字体数量' : 'Fonts', fingerprint.font_count],
    [isZh ? 'User-Agent' : 'User agent', fingerprint.user_agent],
  ]

  return (
    <fieldset>
      <legend className="mb-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">
        {isZh ? '已固定硬件特征' : 'Machine'}
      </legend>
      <p className="mb-2.5 text-ink-faint">
        {isZh
          ? `跨会话保持固定 — 共锁定 ${fingerprint.property_count} 项指纹参数。点击下方“重新生成指纹”可将此环境迁移至不同硬件。`
          : `Pinned across launches — ${fingerprint.property_count} properties. Regenerate the fingerprint to move this profile to different hardware.`}
      </p>
      <div className="panel divide-y divide-line">
        {rows
          .filter(([, value]) => value !== null && value !== undefined && value !== '')
          .map(([label, value]) => (
            <div key={label} className="flex gap-3 px-3 py-1.5">
              <span className="w-[92px] shrink-0 text-ink-dim">{label}</span>
              <span className="min-w-0 flex-1 break-all font-mono text-ink">{value}</span>
            </div>
          ))}
      </div>

      {/* A pin never ages by itself. */}
      {fingerprint.browser_outdated && (
        <div className="mt-2 flex items-start gap-2.5 rounded-md border border-line bg-raised p-2.5">
          <TriangleAlert size={14} className="mt-0.5 shrink-0 text-signal" />
          <div className="flex-1">
            <p className="text-ink">
              {isZh
                ? `此环境当前报告为 Firefox ${fingerprint.browser_major}；已安装的最新内核为 ${fingerprint.installed_major}。`
                : `This profile still reports Firefox ${fingerprint.browser_major}; the installed browser is ${fingerprint.installed_major}.`}
            </p>
            <p className="mt-0.5 text-ink-faint">
              {isZh
                ? '升级内核仅改变浏览器版本号。屏幕尺寸、显卡、核心数、字体和 Canvas 完全不受影响。'
                : 'Updating changes only the browser version. The screen, GPU, cores, fonts and canvas stay exactly as they are — the same computer, with its browser updated.'}
            </p>
          </div>
          <button
            type="button"
            className="btn btn-default shrink-0"
            onClick={onRefreshBrowser}
            disabled={refreshing}
          >
            {refreshing && <LoaderCircle size={13} className="animate-spin" />}
            {isZh ? '同步更新' : 'Update'}
          </button>
        </div>
      )}

      {fingerprint.os_mismatch && (
        <div className="mt-2 rounded-md border border-line bg-raised p-2.5">
          <div className="flex items-start gap-2.5">
            <TriangleAlert size={14} className="mt-0.5 shrink-0 text-warn" />
            <div>
              <p className="text-ink">
                {isZh
                  ? `环境设置为 ${osLabel(fingerprint.settings_os)}，但锁定的硬件机器是 ${osLabel(fingerprint.pinned_os)} 特征 — 网站识别到的以底层硬件机器为准。`
                  : `This profile is set to ${osLabel(fingerprint.settings_os)}, but its pinned machine is a ${osLabel(fingerprint.pinned_os)} one — and the machine is what every page sees.`}
              </p>
              <p className="mt-0.5 text-ink-faint">
                {isZh
                  ? `保留机器将把设置调回 ${osLabel(fingerprint.pinned_os)}，且不改变任何指纹；若换用 ${osLabel(fingerprint.settings_os)} 机器则会分配全新硬件特征。`
                  : `Keeping the machine puts the setting back to ${osLabel(fingerprint.pinned_os)} and changes no fingerprint at all. Pinning a ${osLabel(fingerprint.settings_os)} machine instead gives this profile different hardware.`}
              </p>
            </div>
          </div>
          <div className="mt-2 flex justify-end gap-2">
            <button
              type="button"
              className="btn btn-default"
              onClick={() => onReconcileOs(true)}
              disabled={reconciling}
            >
              {reconciling && <LoaderCircle size={13} className="animate-spin" />}
              {isZh ? '保留当前硬件' : 'Keep this machine'}
            </button>
            <button
              type="button"
              className="btn btn-default"
              onClick={() => onReconcileOs(false)}
              disabled={reconciling}
            >
              {isZh ? `匹配新 ${osLabel(fingerprint.settings_os)} 硬件` : `New ${osLabel(fingerprint.settings_os)} machine`}
            </button>
          </div>
        </div>
      )}
    </fieldset>
  )
}

function osLabel(os?: string | null): string {
  return (os && OS_LABELS[os]) || os || 'unknown'
}

function Section({
  title,
  hint,
  children,
}: {
  title: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <fieldset>
      <legend className="mb-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">
        {title}
      </legend>
      {hint && <p className="mb-2.5 text-ink-faint">{hint}</p>}
      <div className="grid grid-cols-2 gap-3">{children}</div>
    </fieldset>
  )
}

/**
 * Proxy check findings display
 */
function ProxyCheckResult({ result, isZh = false }: { result: ProxyCheck | null; isZh?: boolean }) {
  if (!result) return null

  if (!result.reachable) {
    return (
      <div className="mt-2.5 p-3 rounded-lg border border-danger/30 bg-danger/10 text-xs text-danger flex items-start gap-2">
        <X size={14} className="mt-0.5 shrink-0" />
        <div>
          <span className="font-semibold">{isZh ? '网络连接失败: ' : 'Connection Failed: '}</span>
          <span>{result.error || (isZh ? '无法连通目标代理或外网' : 'Unreachable')}</span>
        </div>
      </div>
    )
  }

  const where = result.location
  const countryProfile = where?.country ? getCountryProfile(where.country) : null
  const flag = countryProfile?.flag || '🌐'
  const countryName = countryProfile?.name || where?.country || ''
  const locationText = [countryName, where?.region, where?.city].filter(Boolean).join(' · ')

  return (
    <div className="mt-2.5 p-3 rounded-lg border border-ok/30 bg-ok/5 text-xs space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-ok font-semibold">
          <Check size={14} />
          <span>{isZh ? '网络连通正常 (Reachable)' : 'Connection Successful'}</span>
        </div>
        {result.latency_ms !== null && (
          <span className="font-mono text-ink-dim px-2 py-0.5 rounded bg-surface border border-line/60">
            {result.latency_ms} ms
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 text-ink-muted pt-1 border-t border-line/40">
        <div>
          <span className="text-ink-faint mr-1.5">{isZh ? '出口 IP:' : 'Exit IP:'}</span>
          <span className="font-mono text-ink font-medium">{where?.ip || '未知'}</span>
        </div>
        <div>
          <span className="text-ink-faint mr-1.5">{isZh ? '地理位置:' : 'Location:'}</span>
          <span className="text-ink font-medium">{flag} {locationText || (isZh ? '未知' : 'Unknown')}</span>
        </div>
        <div>
          <span className="text-ink-faint mr-1.5">{isZh ? '匹配时区:' : 'Timezone:'}</span>
          <span className="font-mono text-ink font-medium">{where?.timezone || '未知'}</span>
        </div>
        <div>
          <span className="text-ink-faint mr-1.5">{isZh ? '首选语言:' : 'Languages:'}</span>
          <span className="text-ink font-medium">{where?.languages?.join(', ') || (isZh ? '自动匹配' : 'Auto')}</span>
        </div>
      </div>

      <div className="text-[11px] text-emerald-400/90 flex items-center gap-1 pt-0.5">
        <span>✓</span>
        <span>{isZh ? '系统已自动为该环境对齐出网 IP 的对应语言、时区及防关联特征' : 'Timezone & languages auto-adapted to exit IP'}</span>
      </div>

      {result.findings.length > 0 && (
        <div className="pt-1.5 border-t border-line/40 space-y-1">
          {result.findings.map((finding, index) => (
            <p
              key={index}
              className={`flex items-start gap-1.5 text-[11px] ${
                finding.level === 'error'
                  ? 'text-danger'
                  : finding.level === 'warning'
                    ? 'text-warn'
                    : 'text-ink-faint'
              }`}
            >
              {finding.level === 'info' ? (
                <Info size={12} className="mt-0.5 shrink-0" />
              ) : (
                <TriangleAlert size={12} className="mt-0.5 shrink-0" />
              )}
              <span>{finding.message}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
