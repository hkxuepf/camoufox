// API client for the Camoufox Profile Manager backend.
//
// The UI is served by the API on the same origin, so the base URL is empty by
// default; NEXT_PUBLIC_API_URL overrides it for split deployments.

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

// Canonical API prefix. The backend still serves the unversioned /api paths as
// aliases for older scripts; the bundled UI always talks to the current one.
const API_PREFIX = '/api/v1'

export interface BrowserSettings {
  browser_ui?: 'desktop' | 'camoufox'
  browser_engine?: 'chromium' | 'camoufox'
  kernel_version?: string | null
  kernel_channel?: 'stable' | 'beta' | 'dev'
  kernel_auto_download?: boolean
  os: string
  screen: string
  user_agent?: string | null
  languages?: string[]
  timezone?: string | null
  locale?: string | null
  window_width?: number | null
  window_height?: number | null
  geolocation?: {
    lat?: number
    lon?: number
    latitude?: number
    longitude?: number
    accuracy?: number
  } | null
  hardware_concurrency?: number | null
  device_memory?: number | null
  max_touch_points?: number
  webrtc_mode?: string
  /** Keep the canvas reproducible across launches, at the cost of cross-site unlinkability. */
  stable_canvas?: boolean
  canvas_noise?: boolean
  webgl_noise?: boolean
  audio_noise?: boolean
  client_rects_noise?: boolean
  device_pixel_ratio?: number
  battery_spoofing?: boolean
  do_not_track?: boolean
  doh_provider?: string | null
  search_engine?: string | null
  webgl_vendor?: string | null
  webgl_renderer?: string | null
  remote_debugging_port?: number | null
  custom_args?: string[]
}

export interface ClientReleaseItem {
  id: string
  version: string
  title?: string
  changelog?: string
  changelog_en?: string
  min_version?: string
  is_force_update?: boolean
  is_active?: boolean
  mac_arm64_url?: string | null
  mac_x64_url?: string | null
  win_x64_url?: string | null
  created_at?: string
  updated_at?: string
}

export interface KernelReleaseItem {
  id: string
  engine: 'chromium' | 'camoufox'
  version: string
  display_name?: string
  changelog?: string
  is_recommended?: boolean
  is_active?: boolean
  mac_arm64_url?: string | null
  mac_arm64_sha256?: string | null
  mac_x64_url?: string | null
  mac_x64_sha256?: string | null
  win_x64_url?: string | null
  win_x64_sha256?: string | null
  created_at?: string
  updated_at?: string
}

export interface ClientUpdateCheckResult {
  has_update: boolean
  current_version: string
  latest_version: string
  title?: string
  changelog?: string
  changelog_en?: string
  is_force_update?: boolean
  download_url?: string | null
  download_mirror_url?: string | null
  published_at?: string
}

export interface ProxyConfig {
  type?: string
  server?: string
  username?: string | null
  password?: string | null
  country?: string | null
}

/** A short description of the machine a profile is pinned to. */
export interface FingerprintSummary {
  user_agent?: string | null
  platform?: string | null
  hardware_concurrency?: number | null
  screen?: string | null
  gpu?: string | null
  font_count?: number | null
  property_count?: number
  /** Firefox major version this pin claims. */
  browser_major?: number | null
  /** Firefox major version of the browser on disk. */
  installed_major?: number | null
  /** The pin claims an older browser than the one installed. */
  browser_outdated?: boolean
  /** The OS the pinned machine itself reports. */
  pinned_os?: string | null
  /** The OS the profile's settings ask for. */
  settings_os?: string | null
  /** The setting names one operating system and the pinned machine another. */
  os_mismatch?: boolean
}

export interface Profile {
  id: string
  name: string
  group?: string | null
  status: string
  browser_settings: BrowserSettings
  proxy_config?: ProxyConfig | null
  storage_path?: string | null
  notes?: string | null
  cookies?: string | null
  account?: string | null
  is_favorite?: boolean
  tags?: string[]
  created_at: string
  updated_at?: string
  last_used?: string | null
  fingerprint?: FingerprintSummary | null
  /** Null until the proxy is checked, and again whenever the proxy changes. */
  proxy_check?: ProxyCheckRecord | null
  /**
   * Bumped by every save. Sent back with an edit so that a save someone else
   * landed in the meantime is refused rather than silently overwritten.
   */
  row_version: number
  sync_status?: string | null
  last_synced_at?: string | null
  sync_size_kb?: number | null
  cloud_sync_enabled?: boolean
}

export interface ProfilesResponse {
  profiles: Profile[]
  total: number
  page: number
  per_page: number
  has_next: boolean
  has_prev: boolean
}

export interface Group {
  id: string
  name: string
  description?: string | null
  created_at: string
  profile_count: number
}

export interface SystemStatus {
  total_profiles: number
  active_profiles: number
  running_browsers: number
  total_groups: number
  system_load: number
  memory_usage: number
  disk_usage: number
  uptime_seconds: number
}

/**
 * A failed request, carrying enough to act on rather than only to display.
 *
 * The status and the API's own error code are what let a caller tell apart the
 * conflicts that share 409 — someone else saved this profile, versus someone
 * else is running it — and do something better than showing the message.
 */
export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message)
    this.name = 'ApiRequestError'
  }
}

/** The profile was saved by someone else since this client last read it. */
export function isStaleWrite(error: unknown): boolean {
  return error instanceof ApiRequestError && error.status === 409 && error.code === 'stale_write'
}

const API_KEY_STORAGE = 'camoufox-pm.api-key'
const SESSION_TOKEN_STORAGE = 'camouhub.session_token'

/** The key CPM_API_KEY expects, if the user has stored one. */
export function getApiKey(): string {
  if (typeof window === 'undefined') return ''
  return window.localStorage.getItem(API_KEY_STORAGE) ?? ''
}

export function setApiKey(key: string): void {
  if (typeof window === 'undefined') return
  if (key) window.localStorage.setItem(API_KEY_STORAGE, key)
  else window.localStorage.removeItem(API_KEY_STORAGE)
}

export function getSessionToken(): string {
  if (typeof window === 'undefined') return ''
  try {
    return window.localStorage.getItem(SESSION_TOKEN_STORAGE) ?? ''
  } catch {
    return ''
  }
}

export function setSessionToken(token?: string | null): void {
  if (typeof window === 'undefined') return
  try {
    if (token) window.localStorage.setItem(SESSION_TOKEN_STORAGE, token)
    else window.localStorage.removeItem(SESSION_TOKEN_STORAGE)
  } catch {
    // Ignore storage errors
  }
}

export function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {}
  const key = getApiKey()
  if (key) headers['X-API-Key'] = key
  const token = getSessionToken()
  if (token) {
    headers['X-Session-Token'] = token
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(options?.headers ?? {}),
    },
  })
  if (!response.ok) {
    let detail = response.statusText
    let code: string | undefined
    try {
      const body = await response.json()
      // Every API error carries error.message; detail is the legacy mirror,
      // kept as a fallback for anything not yet on the one error shape.
      const raw = body.error?.message ?? body.detail ?? body.message ?? detail
      detail = typeof raw === 'string' ? raw : JSON.stringify(raw)
      code = body.error?.code
    } catch {
      // response had no JSON body
    }
    throw new ApiRequestError(detail, response.status, code)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

function toQuery(params: Record<string, unknown>): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  }
  return query.toString() ? `?${query.toString()}` : ''
}

export interface ProxyLocation {
  ip: string
  country: string | null
  region?: string | null
  city?: string | null
  timezone: string | null
  latitude: number | null
  longitude: number | null
  languages?: string[] | null
}

export interface ProxyFinding {
  level: 'error' | 'warning' | 'info'
  field: string
  message: string
}

export interface ProxyCheck {
  reachable: boolean
  error: string | null
  latency_ms: number | null
  location: ProxyLocation | null
  findings: ProxyFinding[]
  /** Null when checking a proxy that is not saved yet, which is recorded nowhere. */
  checked_at: string | null
}

/** The last answer a profile's proxy gave, as the list shows it. */
export interface ProxyCheckRecord {
  checked_at: string
  reachable: boolean
  error: string | null
  latency_ms: number | null
  ip: string | null
  country: string | null
  timezone: string | null
  findings: ProxyFinding[]
}

export const profilesAPI = {
  getProfiles(params: Record<string, unknown> = {}): Promise<ProfilesResponse> {
    return request<ProfilesResponse>(`${API_PREFIX}/profiles${toQuery(params)}`)
  },

  getProfile(id: string): Promise<Profile> {
    return request<Profile>(`${API_PREFIX}/profiles/${id}`)
  },

  createProfile(data: Record<string, unknown>): Promise<Profile> {
    return request<Profile>(`${API_PREFIX}/profiles`, { method: 'POST', body: JSON.stringify(data) })
  },

  updateProfile(id: string, data: Record<string, unknown>): Promise<Profile> {
    return request<Profile>(`${API_PREFIX}/profiles/${id}`, { method: 'PUT', body: JSON.stringify(data) })
  },

  deleteProfile(id: string): Promise<void> {
    return request<void>(`${API_PREFIX}/profiles/${id}`, { method: 'DELETE' })
  },

  cloneProfile(id: string, newName: string): Promise<Profile> {
    return request<Profile>(`${API_PREFIX}/profiles/${id}/clone`, {
      method: 'POST',
      body: JSON.stringify({ new_name: newName }),
    })
  },

  startProfile(id: string): Promise<unknown> {
    return request<unknown>(`${API_PREFIX}/profiles/${id}/launch`, {
      method: 'POST',
      body: JSON.stringify({ headless: false }),
    })
  },

  closeProfile(id: string): Promise<unknown> {
    return request<unknown>(`${API_PREFIX}/profiles/${id}/close`, { method: 'POST' })
  },

  resetFingerprint(id: string): Promise<Profile> {
    return request<Profile>(`${API_PREFIX}/profiles/${id}/reset-fingerprint`, { method: 'POST' })
  },

  refreshBrowserVersion(id: string): Promise<Profile> {
    return request<Profile>(`${API_PREFIX}/profiles/${id}/refresh-browser`, { method: 'POST' })
  },

  /** keepMachine: move the OS setting to the pin. Otherwise: pin new hardware for the setting. */
  reconcileOs(id: string, keepMachine: boolean): Promise<Profile> {
    return request<Profile>(`${API_PREFIX}/profiles/${id}/reconcile-os`, {
      method: 'POST',
      body: JSON.stringify({ keep_machine: keepMachine }),
    })
  },

  // Takes a list because the profiles this exists for — created when every one
  // was given a random region — are all of them at once.
  clearGeography(ids: string[]): Promise<ClearGeographyResult> {
    return request<ClearGeographyResult>(`${API_PREFIX}/profiles/clear-geography`, {
      method: 'POST',
      body: JSON.stringify({ profile_ids: ids }),
    })
  },

  checkProxy(id: string): Promise<ProxyCheck> {
    return request<ProxyCheck>(`${API_PREFIX}/profiles/${id}/check-proxy`, { method: 'POST' })
  },

  getCookies(id: string): Promise<{ cookies: string }> {
    return request<{ cookies: string }>(`${API_PREFIX}/profiles/${id}/cookies`)
  },

  updateCookies(id: string, cookies: string): Promise<{ status: string }> {
    return request<{ status: string }>(`${API_PREFIX}/profiles/${id}/cookies`, {
      method: 'POST',
      body: JSON.stringify({ cookies }),
    })
  },

  clearCookies(id: string): Promise<{ status: string }> {
    return request<{ status: string }>(`${API_PREFIX}/profiles/${id}/cookies`, {
      method: 'DELETE',
    })
  },

  clearCache(id: string, options: { clear_cache?: boolean; clear_cookies?: boolean } = {}): Promise<{ status: string; cleared_items: string[] }> {
    return request<{ status: string; cleared_items: string[] }>(`${API_PREFIX}/profiles/${id}/clear-cache`, {
      method: 'POST',
      body: JSON.stringify(options),
    })
  },

  toggleFavorite(id: string): Promise<{ status: string; is_favorite: boolean }> {
    return request<{ status: string; is_favorite: boolean }>(`${API_PREFIX}/profiles/${id}/toggle-favorite`, {
      method: 'POST',
    })
  },

  updateAccount(id: string, account: string): Promise<{ status: string; account: string }> {
    return request<{ status: string; account: string }>(`${API_PREFIX}/profiles/${id}/account`, {
      method: 'POST',
      body: JSON.stringify({ account }),
    })
  },

  mutateFingerprint(id: string): Promise<{ status: string; profile_id: string; mutated_diff: Record<string, string>; profile: Profile }> {
    return request(`${API_PREFIX}/profiles/${id}/mutate-fingerprint`, {
      method: 'POST',
    })
  },

  pushCloudSync(id: string): Promise<{ success: boolean; profile_id: string; size_kb: number; uploaded_at: string }> {
    return request(`${API_PREFIX}/profiles/${id}/cloud-sync/push`, {
      method: 'POST',
    })
  },

  pullCloudSync(id: string): Promise<{ success: boolean; profile_id: string; size_kb: number; meta?: any }> {
    return request(`${API_PREFIX}/profiles/${id}/cloud-sync/pull`, {
      method: 'POST',
    })
  },

  listSnapshots(id: string): Promise<{
    profile_id: string
    snapshots: Array<{
      id: string
      profile_id: string
      snapshot_name: string
      size_kb: number
      r2_key: string
      created_at: string
    }>
  }> {
    return request(`${API_PREFIX}/profiles/${id}/snapshots`, {
      method: 'GET',
    })
  },

  rollbackSnapshot(
    profileId: string,
    snapshotId: string
  ): Promise<{ success: boolean; message: string; snapshot: any }> {
    return request(`${API_PREFIX}/profiles/${profileId}/snapshots/${snapshotId}/rollback`, {
      method: 'POST',
    })
  },

  deleteSnapshot(
    profileId: string,
    snapshotId: string
  ): Promise<{ success: boolean; snapshot_id: string }> {
    return request(`${API_PREFIX}/profiles/${profileId}/snapshots/${snapshotId}`, {
      method: 'DELETE',
    })
  },


  // The same check for a profile that is still being filled in, so the form can
  // answer before anything is saved.
  checkUnsavedProxy(body: {
    proxy_config: Record<string, unknown> | null
    browser_settings: Record<string, unknown>
  }): Promise<ProxyCheck> {
    return request<ProxyCheck>(`${API_PREFIX}/proxy/check`, { method: 'POST', body: JSON.stringify(body) })
  },

  async exportExcel(): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}${API_PREFIX}/profiles/export/excel`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(response.statusText)
    return response.blob()
  },

  async exportArchive(id: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}${API_PREFIX}/profiles/${id}/export`, {
      headers: authHeaders(),
    })
    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new Error(body?.detail ?? response.statusText)
    }
    return response.blob()
  },

  async importArchive(file: File): Promise<Profile> {
    const body = new FormData()
    body.append('file', file)
    // No Content-Type: the browser has to set the multipart boundary itself.
    const response = await fetch(`${API_BASE_URL}${API_PREFIX}/profiles/import`, {
      method: 'POST',
      headers: authHeaders(),
      body,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new Error(detail?.detail ?? response.statusText)
    }
    return response.json() as Promise<Profile>
  },

  async importExcel(file: File): Promise<ImportResult> {
    const body = new FormData()
    body.append('file', file)
    // No Content-Type: the browser has to set the multipart boundary itself.
    const response = await fetch(`${API_BASE_URL}${API_PREFIX}/profiles/import/excel`, {
      method: 'POST',
      headers: authHeaders(),
      body,
    })
    return response.json() as Promise<ImportResult>
  },
}

export interface ClearGeographyResult {
  cleared: string[]
  unchanged: string[]
  not_found: string[]
}

export interface ImportResult {
  success: boolean
  message: string
  data?: { created_count?: number; errors?: string[] }
}

export const browsersAPI = {
  active(): Promise<{ active_browsers: { profile_id: string }[]; count: number }> {
    return request(`${API_PREFIX}/browsers/active`)
  },

  closeAll(): Promise<{ closed_count: number; message: string }> {
    return request(`${API_PREFIX}/browsers/close-all`, { method: 'POST' })
  },
}

export const groupsAPI = {
  list(): Promise<{ groups: Group[]; total: number }> {
    return request(`${API_PREFIX}/groups`)
  },

  create(data: { name: string; description?: string }): Promise<Group> {
    return request<Group>(`${API_PREFIX}/groups`, { method: 'POST', body: JSON.stringify(data) })
  },

  update(id: string, data: { name?: string; description?: string }): Promise<Group> {
    return request<Group>(`${API_PREFIX}/groups/${id}`, { method: 'PUT', body: JSON.stringify(data) })
  },

  remove(id: string): Promise<void> {
    return request<void>(`${API_PREFIX}/groups/${id}`, { method: 'DELETE' })
  },
}

// --- Schedules ---------------------------------------------------------------

/** What a schedule does when it fires. Hardware regeneration is deliberately
 * not schedulable: it would hand a warmed-up account new hardware on a timer,
 * which is exactly what the pinned machine exists to prevent. */
export type ScheduleAction = 'launch' | 'refresh_browser'

export type ScheduleKind = 'interval' | 'daily'

export type ScheduleRunOutcome = 'ok' | 'skipped' | 'error' | 'missed'

export interface ScheduleRun {
  id: number | null
  schedule_id: string
  started_at: string
  finished_at: string | null
  outcome: ScheduleRunOutcome
  message: string | null
}

export interface Schedule {
  id: string
  profile_id: string
  profile_name: string | null
  action: ScheduleAction
  kind: ScheduleKind
  interval_minutes: number | null
  /** HH:MM on the server's clock. */
  at_time: string | null
  /** Weekdays a daily schedule fires, 0=Monday … 6=Sunday; null = every day. */
  days: number[] | null
  run_minutes: number | null
  enabled: boolean
  next_run_at: string | null
  last_run: ScheduleRun | null
  created_at: string
  updated_at: string
}

export interface SchedulePayload {
  profile_id?: string
  action?: ScheduleAction
  kind?: ScheduleKind
  interval_minutes?: number | null
  at_time?: string | null
  days?: number[] | null
  run_minutes?: number | null
  enabled?: boolean
}

export const schedulesAPI = {
  list(): Promise<{ schedules: Schedule[]; total: number }> {
    return request(`${API_PREFIX}/schedules`)
  },

  create(data: SchedulePayload): Promise<Schedule> {
    return request<Schedule>(`${API_PREFIX}/schedules`, { method: 'POST', body: JSON.stringify(data) })
  },

  update(id: string, data: SchedulePayload): Promise<Schedule> {
    return request<Schedule>(`${API_PREFIX}/schedules/${id}`, { method: 'PUT', body: JSON.stringify(data) })
  },

  remove(id: string): Promise<void> {
    return request<void>(`${API_PREFIX}/schedules/${id}`, { method: 'DELETE' })
  },

  runNow(id: string): Promise<ScheduleRun> {
    return request<ScheduleRun>(`${API_PREFIX}/schedules/${id}/run`, { method: 'POST' })
  },

  runs(id: string): Promise<{ runs: ScheduleRun[]; total: number }> {
    return request(`${API_PREFIX}/schedules/${id}/runs`)
  },
}

export interface SystemConfig {
  version: string
  host: string
  port: number
  database_path: string
  api_key_set: boolean
  user_auth_enabled: boolean
  encryption_enabled: boolean
  cors_origins: string[]
  camoufox_available: boolean
  uptime_seconds: number
}

export interface BrowserReadiness {
  installed: boolean
  version: string | null
  state: 'idle' | 'downloading' | 'ready' | 'error'
  progress: number | null
  message: string
  error: string | null
}

export interface AppUpdate {
  current_version: string
  latest_version: string | null
  available: boolean
  release_url: string | null
  assets: { name: string; url: string }[]
  error?: string | null
}

export interface BackupInfo {
  id: string
  profile_id: string
  profile_name: string
  created_at: string
  reason: string
  size_bytes: number
}

export interface BackupResult {
  backups: BackupInfo[]
  skipped: { profile_id: string; reason: string }[]
}

export const recoveryAPI = {
  async trash(): Promise<(Profile & { deleted_at: string })[]> {
    const body = await request<{ data: { profiles: (Profile & { deleted_at: string })[] } }>(`${API_PREFIX}/trash/profiles`)
    return body.data.profiles
  },
  async restoreProfile(id: string): Promise<Profile> {
    const body = await request<{ data: Profile }>(`${API_PREFIX}/trash/profiles/${id}/restore`, { method: 'POST' })
    return body.data
  },
  permanentlyDelete(id: string): Promise<unknown> {
    return request(`${API_PREFIX}/trash/profiles/${id}?confirm=true`, { method: 'DELETE' })
  },
  async backups(): Promise<BackupInfo[]> {
    const body = await request<{ data: { backups: BackupInfo[] } }>(`${API_PREFIX}/system/backups`)
    return body.data.backups
  },
  async createBackup(): Promise<BackupResult> {
    const body = await request<{ data: BackupResult }>(`${API_PREFIX}/system/backups`, { method: 'POST', body: JSON.stringify({ reason: 'manual' }) })
    return body.data
  },
  async restoreBackup(id: string): Promise<Profile> {
    const body = await request<{ data: Profile }>(`${API_PREFIX}/system/backups/${id}/restore`, { method: 'POST', body: JSON.stringify({}) })
    return body.data
  },
}

/** A fingerprint captured from a real machine, bundled with Camoufox. */
export interface DevicePreset {
  id: string
  os: string
  screen?: string | null
  hardware_concurrency?: number | null
  gpu?: string | null
  vendor?: string | null
  user_agent?: string | null
}

export const presetsAPI = {
  async list(os?: string): Promise<DevicePreset[]> {
    const body = await request<{ data: { presets: DevicePreset[] } }>(
      `${API_PREFIX}/fingerprints/presets${toQuery({ os })}`,
    )
    return body.data.presets
  },
}

/** The caller's authentication state, from GET /auth/session. */
export interface AuthSession {
  user_auth_enabled: boolean
  authenticated: boolean
  token?: string | null
  username: string | null
  role?: string
  plan_id?: string
  max_profiles?: number
  used_profiles?: number
  max_concurrent?: number
  expires_at?: string | null
  status?: string
}

export interface Plan {
  id: string
  name: string
  max_profiles: number
  max_concurrent: number
  duration_days: number
  price_usdt: number
  description?: string
}

export interface Order {
  id: string
  order_no: string
  user_id: string
  username: string
  plan_id: string
  plan_name: string
  amount_usdt: number
  status: 'pending' | 'paid' | 'cancelled'
  pay_network: string
  pay_address: string
  tx_hash?: string | null
  created_at: string
  paid_at?: string | null
}

export interface AdminStats {
  user_count: number
  profile_count: number
  active_running: number
  total_orders: number
  paid_orders: number
  total_revenue_usdt: number
}

export interface AdminUser {
  id: string
  username: string
  role: string
  plan_id: string
  max_profiles: number
  max_concurrent: number
  used_profiles?: number
  expires_at: string | null
  status: string
  created_at: string
}

export const authAPI = {
  async session(): Promise<AuthSession> {
    const res = await request<AuthSession>(`${API_PREFIX}/auth/session`)
    if (res.authenticated && res.token) {
      setSessionToken(res.token)
    } else if (!res.authenticated) {
      setSessionToken(null)
    }
    return res
  },

  async login(username: string, password: string): Promise<AuthSession> {
    const res = await request<AuthSession>(`${API_PREFIX}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    if (res.authenticated && res.token) {
      setSessionToken(res.token)
    }
    return res
  },

  async register(username: string, password: string): Promise<AuthSession> {
    const res = await request<AuthSession>(`${API_PREFIX}/auth/register`, {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    if (res.authenticated && res.token) {
      setSessionToken(res.token)
    }
    return res
  },


  async logout(): Promise<unknown> {
    try {
      return await request<unknown>(`${API_PREFIX}/auth/logout`, { method: 'POST' })
    } finally {
      setSessionToken(null)
    }
  },
}

export const billingAPI = {
  async getPlans(): Promise<Plan[]> {
    const res = await request<{ data: Plan[] }>(`${API_PREFIX}/billing/plans`)
    return res.data
  },
  async getOrders(): Promise<Order[]> {
    const res = await request<{ data: Order[] }>(`${API_PREFIX}/billing/orders`)
    return res.data
  },
  async createOrder(plan_id: string): Promise<Order> {
    const res = await request<{ data: Order }>(`${API_PREFIX}/billing/orders`, {
      method: 'POST',
      body: JSON.stringify({ plan_id }),
    })
    return res.data
  },
  async getOrder(order_no: string): Promise<Order> {
    const res = await request<{ data: Order }>(`${API_PREFIX}/billing/orders/${order_no}`)
    return res.data
  },
  async submitTx(order_no: string, tx_hash: string): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/billing/orders/${order_no}/submit-tx`, {
      method: 'POST',
      body: JSON.stringify({ tx_hash }),
    })
    return res.data
  },
}

export const adminAPI = {
  async getDashboard(): Promise<AdminStats> {
    const res = await request<{ data: AdminStats }>(`${API_PREFIX}/admin/dashboard`)
    return res.data
  },
  async getUsers(): Promise<AdminUser[]> {
    const res = await request<{ data: AdminUser[] }>(`${API_PREFIX}/admin/users`)
    return res.data
  },
  async createUser(data: {
    username: string
    password: string
    role: string
    plan_id: string
    max_profiles: number
    max_concurrent: number
    duration_days?: number
  }): Promise<{ id: string; username: string }> {
    const res = await request<{ data: { id: string; username: string } }>(`${API_PREFIX}/admin/users`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return res.data
  },
  async updateUser(username: string, data: Partial<AdminUser>): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/admin/users/${username}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return res.data
  },
  async resetPassword(username: string, password: string): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/admin/users/${username}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ password }),
    })
    return res.data
  },
  async deleteUser(username: string): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/admin/users/${username}`, {
      method: 'DELETE',
    })
    return res.data
  },
  async getPlans(): Promise<Plan[]> {
    const res = await request<{ data: Plan[] }>(`${API_PREFIX}/admin/plans`)
    return res.data
  },
  async savePlan(plan: Plan): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/admin/plans`, {
      method: 'POST',
      body: JSON.stringify(plan),
    })
    return res.data
  },
  async deletePlan(plan_id: string): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/admin/plans/${plan_id}`, {
      method: 'DELETE',
    })
    return res.data
  },
  async getOrders(): Promise<Order[]> {
    const res = await request<{ data: Order[] }>(`${API_PREFIX}/admin/orders`)
    return res.data
  },
  async confirmOrder(order_no: string): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/admin/orders/${order_no}/confirm`, {
      method: 'POST',
    })
    return res.data
  },
  async getSettings(): Promise<Record<string, string>> {
    const res = await request<{ data: Record<string, string> }>(`${API_PREFIX}/admin/settings`)
    return res.data
  },
  async updateSettings(settings: Record<string, string>): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/admin/settings`, {
      method: 'POST',
      body: JSON.stringify(settings),
    })
    return res.data
  },
  async getClientReleases(): Promise<ClientReleaseItem[]> {
    const res = await request<{ data: ClientReleaseItem[] }>(`${API_PREFIX}/admin/releases/client`)
    return res.data
  },
  async createClientRelease(data: Partial<ClientReleaseItem>): Promise<ClientReleaseItem> {
    const res = await request<{ data: ClientReleaseItem }>(`${API_PREFIX}/admin/releases/client`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return res.data
  },
  async updateClientRelease(id: string, data: Partial<ClientReleaseItem>): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/admin/releases/client/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return res.data
  },
  async deleteClientRelease(id: string): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/admin/releases/client/${id}`, {
      method: 'DELETE',
    })
    return res.data
  },
  async getKernelReleases(engine?: string): Promise<KernelReleaseItem[]> {
    const q = engine ? `?engine=${engine}` : ''
    const res = await request<{ data: KernelReleaseItem[] }>(`${API_PREFIX}/admin/releases/kernel${q}`)
    return res.data
  },
  async createKernelRelease(data: Partial<KernelReleaseItem>): Promise<KernelReleaseItem> {
    const res = await request<{ data: KernelReleaseItem }>(`${API_PREFIX}/admin/releases/kernel`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return res.data
  },
  async updateKernelRelease(id: string, data: Partial<KernelReleaseItem>): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/admin/releases/kernel/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return res.data
  },
  async deleteKernelRelease(id: string): Promise<boolean> {
    const res = await request<{ data: boolean }>(`${API_PREFIX}/admin/releases/kernel/${id}`, {
      method: 'DELETE',
    })
    return res.data
  },
}

export const systemAPI = {
  async browser(): Promise<BrowserReadiness> {
    const body = await request<{ data: BrowserReadiness }>(`${API_PREFIX}/system/browser`)
    return body.data
  },
  async installBrowser(): Promise<BrowserReadiness> {
    const body = await request<{ data: BrowserReadiness }>(`${API_PREFIX}/system/browser/install`, { method: 'POST' })
    return body.data
  },
  async chromium(): Promise<BrowserReadiness> {
    const body = await request<{ data: BrowserReadiness }>(`${API_PREFIX}/system/chromium`)
    return body.data
  },
  async installChromium(): Promise<BrowserReadiness> {
    const body = await request<{ data: BrowserReadiness }>(`${API_PREFIX}/system/chromium/install`, { method: 'POST' })
    return body.data
  },
  async updates(): Promise<AppUpdate> {
    const body = await request<{ data: AppUpdate }>(`${API_PREFIX}/system/updates`)
    return body.data
  },
  async prepareUpdate(): Promise<{ release_url: string; backup_count: number; message: string }> {
    const body = await request<{ data: { release_url: string; backup_count: number; message: string } }>(`${API_PREFIX}/system/updates/prepare`, { method: 'POST' })
    return body.data
  },
  status(): Promise<SystemStatus> {
    return request<SystemStatus>(`${API_PREFIX}/system/status`)
  },

  async config(): Promise<SystemConfig> {
    const body = await request<{ data: SystemConfig }>(`${API_PREFIX}/system/config`)
    return body.data
  },

  async checkClientUpdate(platform = 'mac_arm64', currentVersion = '1.0.0'): Promise<ClientUpdateCheckResult> {
    const res = await request<{ data: ClientUpdateCheckResult }>(
      `${API_PREFIX}/system/client/check-update?platform=${platform}&current_version=${currentVersion}`
    )
    return res.data
  },

  async getKernelsManifest(platform = 'mac_arm64'): Promise<KernelReleaseItem[]> {
    const res = await request<{ data: KernelReleaseItem[] }>(
      `${API_PREFIX}/system/kernels/manifest?platform=${platform}`
    )
    return res.data
  },
}

// --- Display helpers ---------------------------------------------------------

/** Whether a profile states where it is instead of letting its proxy say. */
export function hasGeography(profile: Profile): boolean {
  const bs = profile.browser_settings ?? {}
  return Boolean(bs.timezone || bs.geolocation)
}

export function formatProxyString(proxy?: ProxyConfig | null): string {
  if (!proxy || !proxy.server) return ''
  const scheme = proxy.type ? `${proxy.type}://` : ''
  return `${scheme}${proxy.server}`
}

/** How a checked proxy reads: what colour it is, and why.
 *
 * Derived rather than stored, so a row written by an older version cannot
 * disagree with the rules here. An error-level finding is red even when the
 * proxy answered — SOCKS credentials that Camoufox will drop means the launch
 * is wrong, which is not a milder problem than an unreachable proxy.
 */
export function readProxyCheck(check: ProxyCheckRecord): {
  tone: 'ok' | 'warn' | 'danger'
  label: string
  detail: string
} {
  const notes = check.findings.filter((finding) => finding.level !== 'info')
  const worst = notes.find((finding) => finding.level === 'error') ?? notes[0]
  // Repeats what the row shows on purpose: the line truncates, and an IPv6 exit
  // address is long enough to be cut off mid-address, taking the country and the
  // latency with it. The tooltip is the only place left to read them.
  const lines = [
    check.reachable ? 'Proxy answered' : 'Proxy did not answer',
    check.error,
    check.ip,
    [check.country, check.timezone].filter(Boolean).join(' · ') || null,
    check.latency_ms !== null ? `${check.latency_ms} ms` : null,
    ...notes.map((finding) => finding.message),
    `Checked ${formatLastUsed(check.checked_at).toLowerCase()}`,
  ].filter(Boolean)

  const tone = !check.reachable || worst?.level === 'error' ? 'danger' : worst ? 'warn' : 'ok'

  return {
    tone,
    // Green and amber differ only in hue at six pixels, which is exactly the
    // pair a deuteranope cannot separate. The table's other indicator pairs its
    // dot with a word; this one says the word to screen readers.
    label: tone === 'ok' ? 'Healthy' : tone === 'warn' ? 'Needs attention' : 'Failing',
    detail: lines.join('\n'),
  }
}

export function formatLastUsed(value?: string | null): string {
  if (!value) return 'Never'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Never'

  const seconds = Math.round((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return 'Just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`
  return date.toLocaleDateString()
}

export const OS_LABELS: Record<string, string> = {
  windows: 'Windows',
  android: 'Android',
  ios: 'iOS',
  macos: 'macOS',
  linux: 'Linux',
}

export interface ProxyItem {
  id: string
  name: string
  type: string
  server: string
  port?: number | null
  username?: string | null
  password?: string | null
  status: 'active' | 'failed' | 'uncheck'
  latency_ms?: number | null
  country?: string | null
  city?: string | null
  ip?: string | null
  user_id?: string | null
  created_at: string
  last_checked_at?: string | null
}

export const proxiesAPI = {
  list: async (): Promise<{ proxies: ProxyItem[]; total: number }> => {
    return request(`${API_PREFIX}/proxies`)
  },
  create: async (data: Partial<ProxyItem>): Promise<ProxyItem> => {
    return request(`${API_PREFIX}/proxies`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  batchImport: async (params: { content?: string; default_type?: string; proxies?: any[] }): Promise<{ imported: number }> => {
    return request(`${API_PREFIX}/proxies/batch`, {
      method: 'POST',
      body: JSON.stringify(params),
    })
  },
  update: async (id: string, updates: Partial<ProxyItem>): Promise<{ updated: boolean }> => {
    return request(`${API_PREFIX}/proxies/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    })
  },
  delete: async (id: string): Promise<{ deleted: boolean }> => {
    return request(`${API_PREFIX}/proxies/${id}`, {
      method: 'DELETE',
    })
  },
  batchDelete: async (ids: string[]): Promise<{ deleted: number }> => {
    return request(`${API_PREFIX}/proxies/batch-delete`, {
      method: 'POST',
      body: JSON.stringify({ ids }),
    })
  },
  check: async (id: string): Promise<any> => {
    return request(`${API_PREFIX}/proxies/${id}/check`, {
      method: 'POST',
    })
  },
  batchCheck: async (ids?: string[]): Promise<{ checked: number; results: any[] }> => {
    return request(`${API_PREFIX}/proxies/batch-check`, {
      method: 'POST',
      body: JSON.stringify({ ids }),
    })
  },
}

export interface ExtensionItem {
  id: string
  name: string
  version?: string | null
  icon_url?: string | null
  description?: string | null
  category: string
  crx_id?: string | null
  download_url?: string | null
  local_path?: string | null
  is_preset: boolean | number
  enabled: boolean | number
  created_at: string
}

export const extensionsAPI = {
  list: async (): Promise<{ extensions: ExtensionItem[]; total: number }> => {
    return request(`${API_PREFIX}/extensions`)
  },
  toggle: async (id: string, enabled: boolean): Promise<{ id: string; enabled: boolean }> => {
    return request(`${API_PREFIX}/extensions/toggle/${id}`, {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    })
  },
  installPreset: async (id: string): Promise<{ id: string; installed: boolean; local_path?: string }> => {
    return request(`${API_PREFIX}/extensions/install-preset/${id}`, {
      method: 'POST',
    })
  },
  upload: async (formData: FormData): Promise<ExtensionItem> => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('cpm_session_token') : null
    const res = await fetch(`${API_BASE_URL}${API_PREFIX}/extensions/upload`, {
      method: 'POST',
      headers: {
        ...(token ? { 'X-Session-Token': token, Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
      throw new Error(err.detail || 'Upload failed')
    }
    return res.json()
  },
  importWebstore: async (url_or_id: string): Promise<ExtensionItem> => {
    return request(`${API_PREFIX}/extensions/import-webstore`, {
      method: 'POST',
      body: JSON.stringify({ url_or_id }),
    })
  },
  delete: async (id: string): Promise<{ deleted: boolean }> => {
    return request(`${API_PREFIX}/extensions/${id}`, {
      method: 'DELETE',
    })
  },
}

export const windowManagerAPI = {
  tile: async (params?: { cols?: number; rows?: number; padding?: number }): Promise<{ success: boolean; windows_count: number; message: string }> => {
    return request(`${API_PREFIX}/windows/tile`, {
      method: 'POST',
      body: JSON.stringify(params || {}),
    })
  },
  active: async (): Promise<{ sessions: any[]; total: number }> => {
    return request(`${API_PREFIX}/windows/active`)
  },
  broadcast: async (action: string, payload: Record<string, any> = {}, targetProfileIds?: string[]): Promise<{
    success: boolean
    action: string
    total_targets: number
    results: any[]
  }> => {
    return request(`${API_PREFIX}/windows/synchronizer/broadcast`, {
      method: 'POST',
      body: JSON.stringify({
        action,
        payload,
        target_profile_ids: targetProfileIds || null,
      }),
    })
  },
}

export const automationAPI = {
  active: async (): Promise<{ active_sessions: any[]; total: number }> => {
    return request(`${API_PREFIX}/automation/active`)
  },
  start: async (profileId: string, headless = false): Promise<any> => {
    return request(`${API_PREFIX}/automation/start`, {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId, headless }),
    })
  },
  stop: async (profileId: string): Promise<any> => {
    return request(`${API_PREFIX}/automation/stop`, {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId }),
    })
  },
  credentials: async (): Promise<{
    username: string
    is_member: boolean
    role: string
    plan_id: string
    plan_name: string
    has_applied: boolean
    status: string
    local_endpoint: string
    app_id: string
    app_secret: string
    rate_limit: string
    max_devices: number
    documentation_url: string
  }> => {
    return request(`${API_PREFIX}/automation/credentials`)
  },
  apply: async (): Promise<any> => {
    return request(`${API_PREFIX}/automation/apply`, {
      method: 'POST',
    })
  },
  resetSecret: async (): Promise<any> => {
    return request(`${API_PREFIX}/automation/reset-secret`, {
      method: 'POST',
    })
  },
}

