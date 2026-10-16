'use client'

import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import {
  AlertCircle,
  ArrowDown,
  ArrowRightLeft,
  ArrowUp,
  Bot,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Copy,
  Cloud,
  CloudDownload,
  CloudUpload,
  Dna,
  Download,
  Eraser,
  FileSpreadsheet,
  Globe,
  History,
  Info,
  KeyRound,
  Laptop,
  Layers,
  MoreVertical,
  PackageOpen,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings,
  Shield,
  ShieldCheck,
  SlidersHorizontal,
  Square,
  Star,
  Trash2,
  Upload,
  User,
  UserCheck,
  UserPlus,
  Users,
  Wrench,
} from 'lucide-react'

import { BrowserSetup } from '@/components/browser-setup'
import { EmptyState } from '@/components/empty-state'
import { ConfirmDialog, Modal } from '@/components/modal'
import { AndroidIcon, AppleIcon, IosIcon, LinuxIcon, ProfileForm, WindowsIcon } from '@/components/profile-form'
import { CookieModal } from '@/components/cookie-modal'
import { AccountModal } from '@/components/account-modal'
import { QuickProxyModal } from '@/components/quick-proxy-modal'
import { ClearCacheModal } from '@/components/clear-cache-modal'
import { CookieRobotModal } from '@/components/cookie-robot-modal'
import { ProfileDetailModal } from '@/components/profile-detail-modal'
import { SnapshotModal } from '@/components/snapshot-modal'
import { SynchronizerModal } from '@/components/synchronizer-modal'
import { useToast } from '@/components/toast'
import { useI18n } from '@/lib/i18n'
import {
  browsersAPI,
  formatLastUsed,
  formatProxyString,
  groupsAPI,
  hasGeography,
  OS_LABELS,
  profilesAPI,
  readProxyCheck,
  type Group,
  type Profile,
  type ProxyCheckRecord,
  windowManagerAPI,
  automationAPI,
} from '@/lib/api'

type SortKey = 'name' | 'id' | 'group' | 'os' | 'status' | 'last_used'

function AppleLogo({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-3.5 h-3.5 fill-current'} viewBox="0 0 170 170">
      <path d="M150.37 130.25c-2.45 5.66-5.35 10.87-8.71 15.66-4.58 6.53-8.33 11.05-11.22 13.56-4.48 4.12-9.28 6.23-14.42 6.35-3.69 0-8.14-1.05-13.32-3.18-5.19-2.12-9.97-3.17-14.34-3.17-4.58 0-9.49 1.05-14.74 3.17-5.26 2.13-9.5 3.24-12.74 3.35-4.35.13-9.16-1.9-14.42-6.08-3.69-3.04-7.67-7.89-11.96-14.54-6.49-10.15-11.66-21.75-15.5-34.8-3.85-13.06-5.77-24.97-5.77-35.74 0-14.15 3.5-25.96 10.5-35.43 7.01-9.46 16.03-14.28 27.07-14.45 4.89 0 10.37 1.34 16.44 4.02 6.07 2.68 9.94 4.08 11.61 4.2 1.9-.22 5.92-1.68 12.06-4.37 6.14-2.7 11.39-3.9 15.75-3.61 12.06.84 21.6 5.34 28.62 13.5-10.49 6.36-15.63 15.22-15.42 26.58.21 8.91 3.69 16.35 10.43 22.32 6.74 5.98 14.88 9.47 24.42 10.48-2.12 6.43-4.69 12.76-7.7 18.99zM119.22 33.5c-.21-4.14 1.15-8.49 4.07-13.05 2.92-4.57 6.88-8.2 11.87-10.9 0 0-2.45-3.03-4.46-4.22-3.87-2.28-8.2-3.33-13-3.15-6.72.63-12.95 3.99-16.7 9.07-3.76 5.09-5.32 10.87-4.69 17.35.63.21 1.7.35 3.2.42 5.03-.21 11.6-2.52 19.71-5.52z" />
    </svg>
  )
}

function WindowsLogo({ className }: { className?: string }) {
  return (
    <svg className={className || 'w-3.5 h-3.5 fill-current'} viewBox="0 0 88 88">
      <path d="M0 12.402l35.689-4.86.016 34.423-35.67.203zm35.67 33.529l.026 34.453-35.67-4.891-.026-29.562zm4.326-39.027l47.954-6.904v41.975l-47.954.183zm47.96 39.014l-.006 42.082-47.954-6.743-.024-35.339z" />
    </svg>
  )
}

export default function ProfilesPageWrapper() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-[#64748b]">正在加载环境列表…</div>}>
      <ProfilesPage />
    </Suspense>
  )
}

function ProfilesPage() {
  const { t, isZh } = useI18n()
  const searchParams = useSearchParams()
  const filterParam = searchParams.get('filter')

  const [profiles, setProfiles] = useState<Profile[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [running, setRunning] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [groupFilter, setGroupFilter] = useState('all')
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)

  const [checkingProxies, setCheckingProxies] = useState<Set<string>>(new Set())
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [menuFor, setMenuFor] = useState<string | null>(null)
  const [moreMenuOpen, setMoreMenuOpen] = useState(false)
  const [closeMenuOpen, setCloseMenuOpen] = useState(false)
  const [filterMenuOpen, setFilterMenuOpen] = useState(false)

  // Modals state
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Profile | null>(null)
  const [cookieModalProfile, setCookieModalProfile] = useState<Profile | null>(null)
  const [accountModalProfile, setAccountModalProfile] = useState<Profile | null>(null)
  const [proxyModalProfile, setProxyModalProfile] = useState<Profile | null>(null)
  const [cacheModalProfile, setCacheModalProfile] = useState<Profile | null>(null)
  const [robotModalProfile, setRobotModalProfile] = useState<Profile | null>(null)
  const [detailModalProfile, setDetailModalProfile] = useState<Profile | null>(null)
  const [snapshotModalProfile, setSnapshotModalProfile] = useState<Profile | null>(null)

  const [confirm, setConfirm] = useState<null | {
    title: string
    body: string
    label: string
    run: () => Promise<void>
  }>(null)
  const [exportOpen, setExportOpen] = useState(false)
  const [synchronizerOpen, setSynchronizerOpen] = useState(false)
  const [automationModalOpen, setAutomationModalOpen] = useState(false)
  const [activeSessions, setActiveSessions] = useState<any[]>([])
  const [loadingSessions, setLoadingSessions] = useState(false)

  const loadActiveSessions = async () => {
    try {
      setLoadingSessions(true)
      const res = await automationAPI.active()
      setActiveSessions(res.active_sessions || [])
    } catch {
      setActiveSessions([])
    } finally {
      setLoadingSessions(false)
    }
  }

  useEffect(() => {
    if (automationModalOpen) {
      loadActiveSessions()
    }
  }, [automationModalOpen])

  const toast = useToast()
  const importRef = useRef<HTMLInputElement>(null)
  const archiveRef = useRef<HTMLInputElement>(null)

  const loadProfiles = useCallback(async () => {
    try {
      setError(null)
      const collected: Profile[] = []
      for (let pageNumber = 1; pageNumber <= 200; pageNumber += 1) {
        const response = await profilesAPI.getProfiles({ page: pageNumber, per_page: 100 })
        collected.push(...response.profiles)
        if (!response.has_next) break
      }
      setProfiles(collected)
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
    } finally {
      setLoading(false)
    }
  }, [])

  const loadRunning = useCallback(async () => {
    try {
      const response = await browsersAPI.active()
      setRunning(new Set(response.active_browsers.map((b) => b.profile_id)))
    } catch {
      // transient poll
    }
  }, [])

  const loadGroups = useCallback(async () => {
    try {
      const response = await groupsAPI.list()
      setGroups(response.groups)
    } catch {
      // groups
    }
  }, [])

  useEffect(() => {
    loadProfiles()
    loadGroups()
    loadRunning()
    const timer = setInterval(loadRunning, 4000)
    return () => clearInterval(timer)
  }, [loadProfiles, loadGroups, loadRunning])

  // Real-time fleet WebSocket event bus
  useEffect(() => {
    let ws: WebSocket | null = null
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

    const connectWS = () => {
      try {
        const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const host = window.location.port === '3000' ? '127.0.0.1:8000' : window.location.host
        const url = `${proto}//${host}/api/v1/ws`
        ws = new WebSocket(url)

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.event === 'PROFILE_SYNC_COMPLETED') {
              setProfiles((prev) =>
                prev.map((p) =>
                  p.id === data.profile_id
                    ? {
                        ...p,
                        sync_status: data.sync_status || 'synced',
                        sync_size_kb: data.size_kb ?? p.sync_size_kb,
                      }
                    : p
                )
              )
            } else if (data.event === 'PROFILE_STATUS_CHANGED') {
              if (data.is_running) {
                setRunning((prev) => new Set([...prev, data.profile_id]))
              } else {
                setRunning((prev) => {
                  const next = new Set(prev)
                  next.delete(data.profile_id)
                  return next
                })
              }
            }
          } catch {
            // ignore non-json
          }
        }

        ws.onclose = () => {
          reconnectTimeout = setTimeout(connectWS, 3000)
        }
      } catch {
        reconnectTimeout = setTimeout(connectWS, 5000)
      }
    }

    connectWS()
    return () => {
      if (ws) ws.close()
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
    }
  }, [])


  useEffect(() => {
    const close = (event: MouseEvent) => {
      const target = event.target as Element | null
      if (target?.closest('[data-menu-trigger], [role="menu"]')) return
      setMenuFor(null)
      setMoreMenuOpen(false)
      setCloseMenuOpen(false)
      setFilterMenuOpen(false)
    }
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [])

  const groupNames = useMemo(
    () => new Map(groups.map((group) => [group.id, group.name])),
    [groups],
  )

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase()
    const filtered = profiles.filter((profile) => {
      // Sidebar filter param
      if (filterParam === 'favorite' && !profile.is_favorite) return false
      if (groupFilter !== 'all' && (profile.group || 'none') !== groupFilter) return false
      if (statusFilter !== 'all' && profile.status !== statusFilter) return false
      if (!needle) return true
      return (
        profile.name.toLowerCase().includes(needle) ||
        profile.id.toLowerCase().includes(needle) ||
        (profile.account && profile.account.toLowerCase().includes(needle))
      )
    })

    if (filterParam === 'recent') {
      return [...filtered].sort(
        (a, b) => new Date(b.last_used ?? 0).getTime() - new Date(a.last_used ?? 0).getTime()
      )
    }

    const direction = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      switch (sortKey) {
        case 'id':
          return a.id.localeCompare(b.id) * direction
        case 'group':
          return (groupNames.get(a.group ?? '') ?? '').localeCompare(
            groupNames.get(b.group ?? '') ?? '',
          ) * direction
        case 'os':
          return (a.browser_settings?.os ?? '').localeCompare(b.browser_settings?.os ?? '') * direction
        case 'status':
          return a.status.localeCompare(b.status) * direction
        case 'last_used':
          return (
            (new Date(a.last_used ?? 0).getTime() - new Date(b.last_used ?? 0).getTime()) * direction
          )
        default:
          return a.name.localeCompare(b.name) * direction
      }
    })
  }, [profiles, search, statusFilter, groupFilter, filterParam, sortKey, sortDir, groupNames])

  const totalPages = Math.max(1, Math.ceil(visible.length / perPage))
  const currentPage = Math.min(page, totalPages)
  const pageRows = visible.slice((currentPage - 1) * perPage, currentPage * perPage)
  const allOnPageSelected = pageRows.length > 0 && pageRows.every((row) => selected.has(row.id))

  function closeMenu(profileId: string) {
    document.querySelector<HTMLButtonElement>(`[data-menu-trigger="${profileId}"]`)?.focus()
    setMenuFor(null)
  }

  async function withBusy(id: string, action: () => Promise<void>) {
    setBusy((current) => new Set(current).add(id))
    try {
      await action()
    } finally {
      setBusy((current) => {
        const next = new Set(current)
        next.delete(id)
        return next
      })
    }
  }

  async function launch(profile: Profile) {
    await withBusy(profile.id, async () => {
      try {
        await profilesAPI.startProfile(profile.id)
        await Promise.all([loadRunning(), loadProfiles()])
      } catch (err) {
        toast('error', '启动浏览器失败', String(err))
      }
    })
  }

  async function stop(profile: Profile) {
    await withBusy(profile.id, async () => {
      try {
        await profilesAPI.closeProfile(profile.id)
        await loadRunning()
      } catch (err) {
        toast('error', '关闭浏览器失败', String(err))
      }
    })
  }

  async function toggleFavorite(profile: Profile) {
    try {
      const res = await profilesAPI.toggleFavorite(profile.id)
      setProfiles((prev) =>
        prev.map((p) => (p.id === profile.id ? { ...p, is_favorite: res.is_favorite } : p)),
      )
      toast('ok', res.is_favorite ? '已设为常用' : '已取消常用', profile.name)
    } catch (err) {
      toast('error', '更新常用状态失败', String(err))
    }
  }

  async function launchSelected() {
    const ids = Array.from(selected)
    if (!ids.length) return
    toast('info', `正在启动 ${ids.length} 个浏览器…`)
    for (const id of ids) {
      const p = profiles.find((item) => item.id === id)
      if (p && !running.has(p.id)) {
        await launch(p)
      }
    }
  }

  async function stopSelected() {
    const ids = Array.from(selected).filter((id) => running.has(id))
    if (!ids.length) return
    toast('info', `正在关闭 ${ids.length} 个浏览器…`)
    for (const id of ids) {
      const p = profiles.find((item) => item.id === id)
      if (p) await stop(p)
    }
  }

  async function cloneProfile(profile: Profile) {
    try {
      await profilesAPI.cloneProfile(profile.id, `${profile.name} 副本`)
      toast('ok', '已克隆环境', `${profile.name} 副本`)
      loadProfiles()
    } catch (err) {
      toast('error', '克隆环境失败', String(err))
    }
  }

  async function exportArchive(profile: Profile) {
    toast('info', '正在导出环境存档…')
    try {
      const blob = await profilesAPI.exportArchive(profile.id)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${profile.name || profile.id}.camoufox.zip`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      toast('ok', '已导出环境存档')
    } catch (err) {
      toast('error', '导出存档失败', String(err))
    }
  }

  function askDelete(profile: Profile) {
    setConfirm({
      title: '移入回收站',
      body: `"${profile.name}" 及其浏览器环境数据将被移入回收站。您可以随时在侧边栏回收站中将其恢复。`,
      label: '确认移入回收站',
      run: async () => {
        await profilesAPI.deleteProfile(profile.id)
        toast('ok', '环境已移入回收站', profile.name)
        setSelected((curr) => {
          const next = new Set(curr)
          next.delete(profile.id)
          return next
        })
        loadProfiles()
      },
    })
  }

  function askBulkDelete() {
    const count = selected.size
    setConfirm({
      title: `将 ${count} 个环境移入回收站`,
      body: '所选环境及其浏览器数据将全部移入回收站。您可以随时在侧边栏回收站中将其恢复。',
      label: '确认全部移入',
      run: async () => {
        for (const id of selected) await profilesAPI.deleteProfile(id)
        toast('ok', `已将 ${count} 个环境移入回收站`)
        setSelected(new Set())
        loadProfiles()
      },
    })
  }

  async function checkProxy(profile: Profile): Promise<ProxyCheckRecord | null> {
    setCheckingProxies((curr) => new Set(curr).add(profile.id))
    try {
      const result = await profilesAPI.checkProxy(profile.id)
      const record: ProxyCheckRecord = {
        checked_at: result.checked_at ?? new Date().toISOString(),
        reachable: result.reachable,
        error: result.error,
        latency_ms: result.latency_ms,
        ip: result.location?.ip ?? null,
        country: result.location?.country ?? null,
        timezone: result.location?.timezone ?? null,
        findings: result.findings,
      }
      setProfiles((curr) =>
        curr.map((r) => (r.id === profile.id ? { ...r, proxy_check: record } : r)),
      )
      toast(
        record.reachable ? 'ok' : 'error',
        record.reachable ? `代理连通正常 (${record.latency_ms ?? 0}ms)` : '代理无法连接',
        record.ip ? `出口 IP: ${record.ip}` : record.error || undefined,
      )
      return record
    } catch (err) {
      toast('error', '测试代理失败', String(err))
      return null
    } finally {
      setCheckingProxies((curr) => {
        const next = new Set(curr)
        next.delete(profile.id)
        return next
      })
    }
  }

  async function runConfirmed() {
    if (!confirm) return
    const action = confirm
    setConfirm(null)
    try {
      await action.run()
    } catch (err) {
      toast('error', '操作失败', String(err))
    }
  }

  return (
    <div className="flex h-full flex-col bg-[#f4f6fa] text-[#0f172a]">
      {/* ================= 1. Hubstudio Table Toolbar ================= */}
      <div className="flex items-center justify-between border-b border-[#eaedf1] bg-white px-4 py-2.5 shadow-sm">
        {/* Left Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            className="flex items-center gap-1.5 rounded bg-[#1664ff] px-3.5 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-[#1253d8] transition-colors"
            onClick={() => {
              setEditing(null)
              setFormOpen(true)
            }}
          >
            <Plus size={14} strokeWidth={2.5} />
            新建环境
          </button>

          <button
            className="flex items-center gap-1 rounded border border-[#eaedf1] bg-white px-3 py-1.5 text-xs font-normal text-[#334155] hover:bg-[#f8fafc] hover:border-[#cbd5e1] transition-colors"
            onClick={() => importRef.current?.click()}
          >
            批量导入
          </button>
          <input
            ref={importRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={async (e) => {
              const file = e.target.files?.[0]
              e.target.value = ''
              if (!file) return
              try {
                const res = await profilesAPI.importExcel(file)
                if (res.success) {
                  toast('ok', `导入成功：新增 ${res.data?.created_count ?? 0} 个环境`)
                  loadProfiles()
                } else {
                  toast('error', '导入遇到错误', res.message)
                }
              } catch (err) {
                toast('error', '导入失败', String(err))
              }
            }}
            className="hidden"
          />

          <button
            className="flex items-center gap-1 rounded border border-[#eaedf1] bg-white px-3 py-1.5 text-xs font-normal text-[#334155] hover:bg-[#f8fafc] hover:border-[#cbd5e1] disabled:opacity-40 transition-colors"
            disabled={selected.size === 0}
            onClick={launchSelected}
          >
            打开 {selected.size > 0 && `(${selected.size})`}
          </button>

          {/* Close Dropdown */}
          <div className="relative">
            <button
              className="flex items-center gap-1 rounded border border-[#eaedf1] bg-white px-3 py-1.5 text-xs font-normal text-[#334155] hover:bg-[#f8fafc] hover:border-[#cbd5e1] transition-colors"
              onClick={(e) => {
                e.stopPropagation()
                setCloseMenuOpen(!closeMenuOpen)
              }}
            >
              关闭
              <ChevronDown size={13} className="text-[#94a3b8]" />
            </button>
            {closeMenuOpen && (
              <div
                role="menu"
                className="absolute left-0 top-8 z-30 w-36 rounded-md border border-[#eaedf1] bg-white py-1 shadow-lg text-xs"
              >
                <button
                  className="w-full px-3 py-1.5 text-left text-[#334155] hover:bg-[#f1f5f9]"
                  onClick={() => {
                    setCloseMenuOpen(false)
                    stopSelected()
                  }}
                  disabled={selected.size === 0}
                >
                  关闭所选环境
                </button>
                <button
                  className="w-full px-3 py-1.5 text-left text-[#ef4444] hover:bg-rose-50"
                  onClick={() => {
                    setCloseMenuOpen(false)
                    browsersAPI.closeAll().then((r) => {
                      toast('ok', r.message)
                      loadRunning()
                    })
                  }}
                >
                  关闭全部运行中
                </button>
              </div>
            )}
          </div>

          {/* More Actions Dropdown */}
          <div className="relative">
            <button
              className="flex items-center gap-1 rounded border border-[#eaedf1] bg-white px-3 py-1.5 text-xs font-normal text-[#334155] hover:bg-[#f8fafc] hover:border-[#cbd5e1] transition-colors"
              onClick={(e) => {
                e.stopPropagation()
                setMoreMenuOpen(!moreMenuOpen)
              }}
            >
              更多
              <ChevronDown size={13} className="text-[#94a3b8]" />
            </button>
            {moreMenuOpen && (
              <div
                role="menu"
                className="absolute left-0 top-8 z-30 w-44 rounded-md border border-[#eaedf1] bg-white py-1 shadow-lg text-xs"
              >
                <button
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[#334155] hover:bg-[#f1f5f9]"
                  onClick={() => {
                    setMoreMenuOpen(false)
                    setExportOpen(true)
                  }}
                >
                  <Download size={13} />
                  导出环境至 Excel
                </button>
                <button
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[#334155] hover:bg-[#f1f5f9]"
                  onClick={() => {
                    setMoreMenuOpen(false)
                    archiveRef.current?.click()
                  }}
                >
                  <PackageOpen size={13} />
                  导入环境 ZIP 存档
                </button>
                <input
                  ref={archiveRef}
                  type="file"
                  accept=".zip"
                  onChange={async (e) => {
                    const file = e.target.files?.[0]
                    e.target.value = ''
                    if (!file) return
                    try {
                      const p = await profilesAPI.importArchive(file)
                      toast('ok', '环境导入成功', p.name)
                      loadProfiles()
                    } catch (err) {
                      toast('error', '存档导入失败', String(err))
                    }
                  }}
                  className="hidden"
                />
                {selected.size > 0 && (
                  <>
                    <div className="my-1 border-t border-[#eaedf1]" />
                    <button
                      className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[#ef4444] hover:bg-rose-50"
                      onClick={() => {
                        setMoreMenuOpen(false)
                        askBulkDelete()
                      }}
                    >
                      <Trash2 size={13} />
                      移至回收站 ({selected.size})
                    </button>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Synchronizer Button */}
          <button
            className="flex items-center gap-1 rounded border border-[#eaedf1] bg-white px-3 py-1.5 text-xs font-normal text-[#334155] hover:bg-[#f8fafc] hover:border-[#cbd5e1] transition-colors cursor-pointer"
            title="多窗口群控同步器：网格平铺、统一导航、拟人化录入"
            onClick={() => setSynchronizerOpen(true)}
          >
            <Layers size={13} className="text-[#1664ff]" />
            群控同步
          </button>
        </div>

        {/* Right Filter & Search */}
        <div className="flex items-center gap-2.5">
          {/* Refresh Button */}
          <button
            className="flex h-7 w-7 items-center justify-center rounded border border-[#eaedf1] bg-white text-[#64748b] hover:bg-[#f8fafc] hover:text-[#0f172a] transition-colors"
            title="刷新数据"
            onClick={() => {
              loadProfiles()
              loadRunning()
              toast('ok', '环境列表已刷新')
            }}
          >
            <RefreshCw size={13} />
          </button>

          {/* Group Filter Selector */}
          <div className="relative">
            <select
              className="h-7 appearance-none rounded border border-[#eaedf1] bg-white pl-2.5 pr-6 text-xs text-[#334155] hover:border-[#cbd5e1] focus:outline-none focus:border-[#1664ff]"
              value={groupFilter}
              onChange={(e) => setGroupFilter(e.target.value)}
            >
              <option value="all">所有分组</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
              <option value="none">未分组</option>
            </select>
            <ChevronDown
              size={12}
              className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[#94a3b8]"
            />
          </div>

          {/* Search Input */}
          <div className="relative w-48">
            <Search
              size={13}
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[#94a3b8]"
            />
            <input
              className="h-7 w-full rounded border border-[#eaedf1] bg-white pl-7 pr-3 text-xs text-[#0f172a] placeholder-[#94a3b8] focus:border-[#1664ff] focus:outline-none"
              placeholder="请输入环境名称"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Filter Popover Button */}
          <div className="relative">
            <button
              className={`flex items-center gap-1.5 h-7 rounded border border-[#eaedf1] bg-white px-2.5 text-xs transition-colors ${
                statusFilter !== 'all' ? 'text-[#1664ff] border-[#1664ff]/40 bg-blue-50/40' : 'text-[#334155] hover:bg-[#f8fafc]'
              }`}
              onClick={(e) => {
                e.stopPropagation()
                setFilterMenuOpen(!filterMenuOpen)
              }}
            >
              <SlidersHorizontal size={12} />
              <span>筛选</span>
              <ChevronDown size={11} className="text-[#94a3b8]" />
            </button>
            {filterMenuOpen && (
              <div
                role="menu"
                className="absolute right-0 top-8 z-30 w-44 rounded-md border border-[#eaedf1] bg-white p-2 shadow-lg text-xs"
              >
                <div className="mb-1.5 font-medium text-[#64748b]">运行状态</div>
                <div className="space-y-1">
                  {[
                    { id: 'all', label: '全部状态' },
                    { id: 'active', label: '正常' },
                    { id: 'inactive', label: '未激活' },
                    { id: 'blocked', label: '已封禁' },
                    { id: 'maintenance', label: '维护中' },
                  ].map((item) => (
                    <button
                      key={item.id}
                      className={`flex w-full items-center justify-between px-2 py-1 rounded text-left ${
                        statusFilter === item.id
                          ? 'bg-[#1664ff]/10 text-[#1664ff] font-medium'
                          : 'text-[#334155] hover:bg-[#f1f5f9]'
                      }`}
                      onClick={() => {
                        setStatusFilter(item.id)
                        setFilterMenuOpen(false)
                      }}
                    >
                      <span>{item.label}</span>
                      {statusFilter === item.id && <Check size={12} />}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ================= 2. Hubstudio Table View ================= */}
      <div className="flex-1 overflow-auto bg-white">
        {loading ? (
          <div className="flex h-64 items-center justify-center text-xs text-[#94a3b8]">
            正在加载环境数据…
          </div>
        ) : error ? (
          <EmptyState
            icon={<Users size={20} />}
            title="无法连接后端服务"
            body={error}
            action={
              <button className="btn btn-default text-xs" onClick={loadProfiles}>
                重试
              </button>
            }
          />
        ) : profiles.length === 0 ? (
          <EmptyState
            icon={<Users size={20} />}
            title="暂无任何环境"
            body="环境是隔离的独立浏览器身份，拥有自研反指纹引擎、独立 Cookie 与代理。点击下方按钮立即创建。"
            action={
              <button
                className="btn btn-primary text-xs"
                onClick={() => {
                  setEditing(null)
                  setFormOpen(true)
                }}
              >
                <Plus size={14} />
                创建首个环境
              </button>
            }
          />
        ) : (
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-[#eaedf1] bg-white text-[11px] font-medium text-[#64748b]">
                <th className="w-10 py-2.5 pl-4">
                  <input
                    type="checkbox"
                    className="accent-[#1664ff]"
                    checked={allOnPageSelected}
                    onChange={() => {
                      setSelected((curr) => {
                        const next = new Set(curr)
                        pageRows.forEach((r) =>
                          allOnPageSelected ? next.delete(r.id) : next.add(r.id),
                        )
                        return next
                      })
                    }}
                  />
                </th>
                <th className="w-24 py-2.5 pr-2 font-medium">序号</th>
                <th className="py-2.5 pr-4 font-medium">环境名称</th>
                <th className="py-2.5 pr-4 font-medium">代理信息</th>
                <th className="py-2.5 pr-4 font-medium">账号</th>
                <th className="py-2.5 pr-4 font-medium">备注</th>
                <th className="w-24 py-2.5 pr-4 font-medium">分组</th>
                <th className="w-32 py-2.5 pr-4 text-right font-medium">
                  <div className="flex items-center justify-end gap-1 text-[#64748b]">
                    <span>操作</span>
                    <Settings size={13} className="text-[#94a3b8]" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f1f5f9]">
              {pageRows.map((profile, index) => {
                const isRunning = running.has(profile.id)
                const isBusy = busy.has(profile.id)
                const os = profile.browser_settings?.os?.toLowerCase() || ''
                const engine = profile.browser_settings?.browser_engine || 'chromium'
                const rowNumber = (currentPage - 1) * perPage + index + 1
                const proxy = profile.proxy_config

                return (
                  <tr
                    key={profile.id}
                    className="hover:bg-[#f8fafc] transition-colors group text-[#0f172a]"
                  >
                    {/* Checkbox */}
                    <td className="py-3 pl-4">
                      <input
                        type="checkbox"
                        className="accent-[#1664ff]"
                        checked={selected.has(profile.id)}
                        onChange={() => {
                          setSelected((curr) => {
                            const next = new Set(curr)
                            if (next.has(profile.id)) next.delete(profile.id)
                            else next.add(profile.id)
                            return next
                          })
                        }}
                      />
                    </td>

                    {/* 序号 & ID */}
                    <td className="py-3 pr-2">
                      <div className="flex flex-col">
                        <span className="font-semibold text-xs text-[#0f172a]">{rowNumber}</span>
                        <span className="font-mono text-[10px] text-[#94a3b8] truncate max-w-[80px]" title={profile.id}>
                          {profile.id.slice(0, 10)}
                        </span>
                      </div>
                    </td>

                    {/* 环境名称 & OS 图标 (完全对齐新建环境的高清矢量品牌图标) */}
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <div className="flex h-5 w-5 shrink-0 items-center justify-center">
                          {os.includes('android') ? (
                            <AndroidIcon className="w-3.5 h-3.5" />
                          ) : os.includes('ios') || os.includes('iphone') || os.includes('ipad') ? (
                            <IosIcon className="w-3.5 h-3.5 text-slate-700" />
                          ) : os.includes('mac') || os.includes('darwin') ? (
                            <AppleIcon className="w-3.5 h-3.5 text-slate-700" />
                          ) : os.includes('linux') ? (
                            <LinuxIcon className="w-3.5 h-3.5" />
                          ) : (
                            <WindowsIcon className="w-3.5 h-3.5" />
                          )}
                        </div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-medium text-[#0f172a]">{profile.name}</span>
                          {profile.is_favorite && (
                            <Star size={12} className="fill-amber-400 text-amber-500" />
                          )}
                          {/* 全自动云漫游状态指示徽标 */}
                          {profile.sync_status === 'syncing' ? (
                            <span
                              title="正在自动同步 Cookie 与会话数据到云端漫游..."
                              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-sky-50 text-sky-600 border border-sky-200 animate-pulse font-normal"
                            >
                              <RefreshCw size={9} className="animate-spin text-sky-600" />
                              同步中
                            </span>
                          ) : profile.sync_status === 'failed' ? (
                            <span
                              title="上次云端漫游同步失败，请检查网络"
                              className="inline-flex items-center gap-0.5 px-1 py-0.5 rounded text-[10px] bg-amber-50 text-amber-600 border border-amber-200 font-normal"
                            >
                              <AlertCircle size={9} />
                              待同步
                            </span>
                          ) : (
                            <span
                              title={`全自动云漫游已就绪${profile.sync_size_kb ? ` (${profile.sync_size_kb} KB)` : ''}`}
                              className="inline-flex items-center text-[#94a3b8] hover:text-[#0284c7] transition-colors"
                            >
                              <Cloud size={11} className="text-[#0284c7]" />
                            </span>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* 代理信息 (Hubstudio format) */}
                    <td className="py-3 pr-4">
                      {proxy ? (
                        <div className="flex flex-col text-[11px] leading-tight">
                          <div className="flex items-center gap-1.5">
                            <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600 border border-blue-200">
                              [动] {(proxy.type || 'PROXY').toUpperCase()}
                            </span>
                            <span className="font-mono text-[#334155]">
                              {proxy.server || '已配置'}
                            </span>
                          </div>
                          <div className="mt-0.5 text-[10px] text-[#94a3b8]">
                            {profile.proxy_check?.reachable ? (
                              <span className="text-emerald-600">
                                {profile.proxy_check.country || '海外'} · {profile.proxy_check.latency_ms ?? 0}ms
                              </span>
                            ) : (
                              <span>已配置独立代理出口</span>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="flex flex-col text-[11px] leading-tight">
                          <div className="flex items-center gap-1.5">
                            <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 border border-emerald-200">
                              [直] 不使用代理
                            </span>
                            <span className="font-mono text-[#64748b]">
                              {profile.proxy_check?.ip || '45.192.2...'}
                            </span>
                          </div>
                          <div className="mt-0.5 text-[10px] text-[#94a3b8]">
                            {profile.proxy_check?.country || 'Japan, Tokyo, Tokyo'}
                          </div>
                        </div>
                      )}
                    </td>

                    {/* 账号 */}
                    <td className="py-3 pr-4 text-[#475569]">
                      {profile.account ? (
                        <div className="flex items-center gap-1.5">
                          <User size={12} className="text-[#64748b]" />
                          <span className="font-mono text-xs">{profile.account}</span>
                        </div>
                      ) : (
                        <span className="text-[#cbd5e1] font-mono">--</span>
                      )}
                    </td>

                    {/* 备注 */}
                    <td className="py-3 pr-4 text-[#475569]">
                      <span className="text-[#cbd5e1] font-mono">--</span>
                    </td>

                    {/* 分组 */}
                    <td className="py-3 pr-4">
                      <span className="rounded border border-[#eaedf1] bg-[#f8fafc] px-2 py-0.5 text-[11px] text-[#64748b]">
                        {profile.group ? (groupNames.get(profile.group) ?? profile.group) : '未分组'}
                      </span>
                    </td>

                    {/* 操作 (Hubstudio Blue Outline Button + ⋮ Menu) */}
                    <td className="py-3 pr-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          className={`flex items-center gap-1 rounded border px-2.5 py-1 text-xs font-medium transition-colors ${
                            isRunning
                              ? 'border-rose-200 bg-rose-50 text-rose-600 hover:bg-rose-100'
                              : profile.sync_status === 'syncing'
                              ? 'border-sky-200 bg-sky-50 text-sky-500 cursor-not-allowed'
                              : 'border-[#1664ff] bg-white text-[#1664ff] hover:bg-[#1664ff]/5'
                          }`}
                          disabled={isBusy || profile.sync_status === 'syncing'}
                          onClick={() => (isRunning ? stop(profile) : launch(profile))}
                        >
                          {isRunning ? (
                            <>
                              <Square size={11} fill="currentColor" />
                              <span>关闭</span>
                            </>
                          ) : profile.sync_status === 'syncing' ? (
                            <>
                              <RefreshCw size={11} className="animate-spin text-sky-500" />
                              <span>同步中...</span>
                            </>
                          ) : (
                            <>
                              {engine === 'camoufox' ? (
                                <span className="text-xs">🦊</span>
                              ) : (
                                <Globe size={13} className="text-[#1664ff]" />
                              )}
                              <span>打开</span>
                            </>
                          )}
                        </button>

                        {/* Hubstudio More Actions Dropdown ⋮ */}
                        <div className="relative">
                          <button
                            className="flex h-6 w-6 items-center justify-center rounded text-[#94a3b8] hover:bg-[#f1f5f9] hover:text-[#0f172a] transition-colors"
                            data-menu-trigger={profile.id}
                            onClick={(e) => {
                              e.stopPropagation()
                              setMenuFor(menuFor === profile.id ? null : profile.id)
                            }}
                          >
                            <MoreVertical size={14} />
                          </button>

                          {menuFor === profile.id && (
                            <div
                              role="menu"
                              className="absolute right-0 top-7 z-40 w-44 rounded-md border border-[#eaedf1] bg-white py-1 shadow-xl text-left text-xs"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  setDetailModalProfile(profile)
                                }}
                              >
                                <Info size={13} className="text-[#64748b]" />
                                详情
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  window.open(`http://127.0.0.1:18888/radar?profile_id=${profile.id}`, '_blank')
                                }}
                              >
                                <ShieldCheck size={13} className="text-[#10b981]" />
                                自检雷达
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  setEditing(profile)
                                  setFormOpen(true)
                                }}
                              >
                                <Pencil size={13} className="text-[#64748b]" />
                                编辑环境
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  setAccountModalProfile(profile)
                                }}
                              >
                                <UserCheck size={13} className="text-[#64748b]" />
                                编辑账号
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  setProxyModalProfile(profile)
                                }}
                              >
                                <Globe size={13} className="text-[#64748b]" />
                                修改代理
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  setCookieModalProfile(profile)
                                }}
                              >
                                <span className="text-[13px]">🍪</span>
                                编辑Cookie
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  setRobotModalProfile(profile)
                                }}
                              >
                                <Bot size={13} className="text-[#64748b]" />
                                CookieRobot
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  setCacheModalProfile(profile)
                                }}
                              >
                                <Eraser size={13} className="text-[#64748b]" />
                                清除缓存
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  cloneProfile(profile)
                                }}
                              >
                                <Copy size={13} className="text-[#64748b]" />
                                克隆环境
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  exportArchive(profile)
                                }}
                              >
                                <PackageOpen size={13} className="text-[#64748b]" />
                                导出环境存档
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={async () => {
                                  closeMenu(profile.id)
                                  if (!window.confirm(`确定为环境「${profile.name}」执行指纹基因突变？\n\n将保留已有 Cookie 和登录态，重新随机生成一套全新的 GPU、CPU、内存与硬件特征。`)) return
                                  try {
                                    const res = await profilesAPI.mutateFingerprint(profile.id)
                                    toast('ok', `指纹基因突变成功！已更新硬件: ${res.mutated_diff?.webgl_renderer || '已重铸'}`)
                                    loadProfiles()
                                  } catch (err: any) {
                                    toast('error', '指纹突变失败', err.message)
                                  }
                                }}
                              >
                                <Dna size={13} className="text-[#8b5cf6]" />
                                指纹基因突变
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  setSnapshotModalProfile(profile)
                                }}
                              >
                                <History size={13} className="text-[#1664ff]" />
                                快照历史时光机
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={async () => {
                                  closeMenu(profile.id)
                                  if (!window.confirm(`【应急恢复】确定强制从云端漫游恢复环境「${profile.name}」的最新会话数据？\n\n注意：此操作将使用云端数据覆盖本地当前 Cookie 与缓存。`)) return
                                  try {
                                    toast('info', `正在从云端拉取「${profile.name}」...`)
                                    const res = await profilesAPI.pullCloudSync(profile.id)
                                    if (res.success) {
                                      toast('ok', `云漫游恢复成功 (${res.size_kb} KB)`)
                                      loadProfiles()
                                    } else {
                                      toast('error', '云漫游恢复失败', (res as any).error)
                                    }
                                  } catch (err: any) {
                                    toast('error', '云漫游拉取异常', err.message)
                                  }
                                }}
                              >
                                <CloudDownload size={13} className="text-[#0284c7]" />
                                从云漫游恢复 (应急)
                              </button>

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#334155] hover:bg-[#f1f5f9]"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  toggleFavorite(profile)
                                }}
                              >
                                <Star
                                  size={13}
                                  className={profile.is_favorite ? 'fill-amber-400 text-amber-500' : 'text-[#64748b]'}
                                />
                                {profile.is_favorite ? '取消常用' : '设为常用'}
                              </button>

                              <div className="my-1 border-t border-[#eaedf1]" />

                              <button
                                className="flex w-full items-center gap-2.5 px-3 py-1.5 text-[#ef4444] hover:bg-rose-50"
                                onClick={() => {
                                  closeMenu(profile.id)
                                  askDelete(profile)
                                }}
                              >
                                <Trash2 size={13} />
                                删除环境
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* ================= 3. Hubstudio Footer Pagination ================= */}
      <div className="flex items-center justify-between border-t border-[#eaedf1] bg-white px-5 py-2.5 text-xs text-[#64748b]">
        <div>
          {selected.size > 0 && (
            <span className="text-[#1664ff] font-medium">已选择 {selected.size} 项 · </span>
          )}
          <span>共 {visible.length} 条记录</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Prev Page */}
          <button
            className="flex h-6 w-6 items-center justify-center rounded border border-[#eaedf1] bg-white text-[#64748b] hover:bg-[#f8fafc] disabled:opacity-40"
            disabled={currentPage === 1}
            onClick={() => setPage(currentPage - 1)}
          >
            <ChevronLeft size={13} />
          </button>

          {/* Current Page */}
          <span className="flex h-6 min-w-6 items-center justify-center rounded border border-[#1664ff] bg-white px-2 font-medium text-[#1664ff]">
            {currentPage}
          </span>

          {/* Next Page */}
          <button
            className="flex h-6 w-6 items-center justify-center rounded border border-[#eaedf1] bg-white text-[#64748b] hover:bg-[#f8fafc] disabled:opacity-40"
            disabled={currentPage === totalPages}
            onClick={() => setPage(currentPage + 1)}
          >
            <ChevronRight size={13} />
          </button>

          {/* Per Page Selector */}
          <select
            className="h-6 rounded border border-[#eaedf1] bg-white px-1.5 text-xs text-[#64748b] hover:border-[#cbd5e1] focus:outline-none"
            value={perPage}
            onChange={(e) => setPerPage(Number(e.target.value))}
          >
            <option value={10}>10 条/页</option>
            <option value={20}>20 条/页</option>
            <option value={50}>50 条/页</option>
            <option value={100}>100 条/页</option>
          </select>
        </div>
      </div>

      {/* ================= 4. Commercial Feature Modals ================= */}
      <ProfileForm
        open={formOpen}
        profile={editing}
        groups={groups}
        onClose={() => setFormOpen(false)}
        onSaved={loadProfiles}
      />

      <CookieModal
        open={cookieModalProfile !== null}
        profile={cookieModalProfile}
        onClose={() => setCookieModalProfile(null)}
        onSaved={loadProfiles}
      />

      <AccountModal
        open={accountModalProfile !== null}
        profile={accountModalProfile}
        onClose={() => setAccountModalProfile(null)}
        onSaved={loadProfiles}
      />

      <QuickProxyModal
        open={proxyModalProfile !== null}
        profile={proxyModalProfile}
        onClose={() => setProxyModalProfile(null)}
        onSaved={loadProfiles}
      />

      <ClearCacheModal
        open={cacheModalProfile !== null}
        profile={cacheModalProfile}
        onClose={() => setCacheModalProfile(null)}
        onCleared={loadProfiles}
      />

      <CookieRobotModal
        open={robotModalProfile !== null}
        profile={robotModalProfile}
        onClose={() => setRobotModalProfile(null)}
      />

      <ProfileDetailModal
        open={detailModalProfile !== null}
        profile={detailModalProfile}
        onClose={() => setDetailModalProfile(null)}
      />

      <SnapshotModal
        open={snapshotModalProfile !== null}
        profile={snapshotModalProfile}
        onClose={() => setSnapshotModalProfile(null)}
        onRollbackSuccess={loadProfiles}
      />

      <SynchronizerModal
        open={synchronizerOpen}
        onClose={() => setSynchronizerOpen(false)}
      />

      <ConfirmDialog
        open={confirm !== null}
        title={confirm?.title ?? ''}
        body={confirm?.body ?? ''}
        confirmLabel={confirm?.label}
        destructive={confirm?.label?.includes('删除') || confirm?.label?.includes('移入')}
        onConfirm={runConfirmed}
        onCancel={() => setConfirm(null)}
      />

      <Modal
        open={exportOpen}
        title="导出环境至 Excel"
        onClose={() => setExportOpen(false)}
        width={440}
        footer={
          <>
            <button className="btn btn-default text-xs" onClick={() => setExportOpen(false)}>
              取消
            </button>
            <button
              className="btn btn-primary text-xs"
              onClick={async () => {
                setExportOpen(false)
                try {
                  const blob = await profilesAPI.exportExcel()
                  const url = URL.createObjectURL(blob)
                  const link = document.createElement('a')
                  link.href = url
                  link.download = 'camoufox-profiles.xlsx'
                  document.body.appendChild(link)
                  link.click()
                  link.remove()
                  URL.revokeObjectURL(url)
                  toast('ok', '已导出 camoufox-profiles.xlsx')
                } catch (err) {
                  toast('error', '导出失败', String(err))
                }
              }}
            >
              导出文件
            </button>
          </>
        }
      >
        <p className="text-[#64748b] text-xs leading-relaxed">
          导出的 Excel 表格将包含所有环境的配置参数以便未来重新导入 — 包括
          <span className="text-[#0f172a] font-semibold"> 明文代理密码与指纹特征</span>
          。请务必将导出的文件存放在安全保密的位置。
        </p>
      </Modal>

      <Modal
        open={automationModalOpen}
        title="本地自动化 API 与 CDP 控制"
        onClose={() => setAutomationModalOpen(false)}
        width={680}
        footer={
          <button className="btn btn-default text-xs cursor-pointer" onClick={() => setAutomationModalOpen(false)}>
            关闭
          </button>
        }
      >
        <div className="space-y-4 text-xs">
          <div className="rounded-lg bg-[#f8fafc] border border-[#e2e8f0] p-3">
            <h4 className="font-semibold text-[#0f172a] mb-1">活跃 CDP 会话端口</h4>
            <p className="text-[#64748b] text-[11px] mb-2.5">
              支持 Playwright / Puppeteer / Selenium 直接通过 CDP WebSocket 远程接管浏览器。
            </p>
            {loadingSessions ? (
              <div className="py-2 text-center text-[#94a3b8]">查询中...</div>
            ) : activeSessions.length === 0 ? (
              <div className="rounded border border-dashed border-[#cbd5e1] p-3 text-center text-[#94a3b8]">
                当前暂无运行中的浏览器会话，启动环境后将在此自动显示 CDP 调试端点
              </div>
            ) : (
              <div className="space-y-2">
                {activeSessions.map((s) => (
                  <div key={s.profile_id} className="rounded border border-[#e2e8f0] bg-white p-2.5">
                    <div className="flex items-center justify-between font-mono font-medium text-[#0f172a]">
                      <span>环境 ID: {s.profile_id}</span>
                      <span className="text-[#1664ff]">CDP 端口: {s.cdp_port || '默认'}</span>
                    </div>
                    {s.ws_endpoint && (
                      <div className="mt-1 flex items-center justify-between rounded bg-[#f1f5f9] px-2 py-1 text-[11px] font-mono text-[#334155]">
                        <span className="truncate mr-2">{s.ws_endpoint}</span>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(s.ws_endpoint)
                            toast('ok', '已复制 WebSocket 调试 URL')
                          }}
                          className="shrink-0 text-[#1664ff] hover:underline cursor-pointer"
                        >
                          复制
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <h4 className="font-semibold text-[#0f172a] mb-1">Playwright (Python) 连接代码示例</h4>
            <pre className="rounded-lg bg-[#0f172a] p-3 font-mono text-[11px] text-[#e2e8f0] overflow-x-auto">
{`from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # 填入上方运行中的 ws_endpoint
    browser = p.chromium.connect_over_cdp("ws://127.0.0.1:PORT/devtools/browser/xxx")
    context = browser.contexts[0]
    page = context.new_page()
    page.goto("https://ipinfo.io")
    print(page.title())`}
            </pre>
          </div>

          <div>
            <h4 className="font-semibold text-[#0f172a] mb-1">商业本地 REST API 接口</h4>
            <div className="rounded-lg border border-[#e2e8f0] bg-white p-2.5 text-[11px] space-y-1 font-mono text-[#334155]">
              <div><span className="text-[#16a34a] font-bold">GET</span> /api/v1/automation/active — 获取所有打开环境的 CDP 接口</div>
              <div><span className="text-[#2563eb] font-bold">POST</span> /api/v1/automation/start — 启动指定 profile_id 并返回 ws_endpoint</div>
              <div><span className="text-[#dc2626] font-bold">POST</span> /api/v1/automation/stop — 关闭指定环境</div>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
