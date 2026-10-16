'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'

import { useAuth } from '@/components/login-gate'
import { BillingModal } from '@/components/billing-modal'
import { AdminTab, useAdminContext } from '@/components/admin-context'
import { systemAPI, type ClientUpdateCheckResult, type KernelReleaseItem } from '@/lib/api'
import { useI18n, LanguageToggle } from '@/lib/i18n'
import {
  Bell,
  CheckCircle2,
  Clock,
  DownloadCloud,
  FolderTree,
  Globe,
  Layers,
  LayoutDashboard,
  LogOut,
  Monitor,
  Package,
  RefreshCw,
  RotateCw,
  Settings,
  Shield,
  Sparkles,
  Star,
  Terminal,
  Trash2,
  Users,
  Wallet,
  Zap,
} from 'lucide-react'

const ADMIN_NAV_ITEMS: { id: AdminTab; labelZh: string; labelEn: string; icon: any }[] = [
  { id: 'dashboard', labelZh: '数据看板', labelEn: 'Dashboard', icon: LayoutDashboard },
  { id: 'users', labelZh: '用户管理', labelEn: 'Users', icon: Users },
  { id: 'plans', labelZh: '套餐配置', labelEn: 'Plans', icon: Package },
  { id: 'orders', labelZh: 'USDT 订单', labelEn: 'USDT Orders', icon: Wallet },
  { id: 'releases', labelZh: '版本与内核', labelEn: 'Releases & Kernels', icon: Layers },
  { id: 'settings', labelZh: '支付与系统', labelEn: 'Settings', icon: Settings },
]

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const current = pathname.replace(/\/+$/, '') || '/'
  const filterParam = searchParams.get('filter')

  const { username, role, planId, maxProfiles, usedProfiles, expiresAt, logout } = useAuth()
  const isAdmin = role === 'admin'
  const { activeTab, setActiveTab } = useAdminContext()

  const [address, setAddress] = useState<string | null>(null)
  const [billingOpen, setBillingOpen] = useState(false)
  const { t, language } = useI18n()

  const [updateOpen, setUpdateOpen] = useState(false)
  const [checkingUpdate, setCheckingUpdate] = useState(false)
  const [clientUpdate, setClientUpdate] = useState<ClientUpdateCheckResult | null>(null)
  const [kernelReleases, setKernelReleases] = useState<KernelReleaseItem[]>([])

  const handleCheckUpdate = async () => {
    setCheckingUpdate(true)
    try {
      const [update, kernels] = await Promise.all([
        systemAPI.checkClientUpdate('mac_arm64', '1.0.0'),
        systemAPI.getKernelsManifest('mac_arm64'),
      ])
      setClientUpdate(update)
      setKernelReleases(kernels || [])
    } catch (e) {
      console.error('Update check failed:', e)
    } finally {
      setCheckingUpdate(false)
    }
  }

  useEffect(() => {
    handleCheckUpdate()
  }, [])

  useEffect(() => {
    if (isAdmin && !current.startsWith('/5DRnDsWW')) {
      router.replace('/5DRnDsWW/')
    }
  }, [isAdmin, current, router])

  useEffect(() => {
    systemAPI
      .config()
      .then((config) => setAddress(`${config.host}:${config.port}`))
      .catch(() => setAddress(null))
  }, [])

  // Actual supported sidebar links
  const SIDEBAR_ITEMS = [
    { href: '/', id: 'environments', label: '我的环境', icon: Monitor },
    { href: '/?filter=favorite', id: 'favorite', label: '常用环境', icon: Star },
    { href: '/?filter=recent', id: 'recent', label: '最近打开', icon: Clock },
    { href: '/proxies/', id: 'proxies', label: '代理池管理', icon: Globe },
    { href: '/extensions/', id: 'extensions', label: '应用与插件', icon: Package },
    { href: '/groups/', id: 'groups', label: '环境分组', icon: FolderTree },
    { href: '/schedules/', id: 'schedules', label: '定时计划', icon: Layers },
  ]

  if (current.startsWith('/5DRnDsWW') && !isAdmin) {
    return <>{children}</>
  }

  return (
    <div className="flex h-screen flex-col bg-[#f4f6fa] select-none text-[#1e293b]">
      {/* ================= 1. TOP HEADER (Clean Commercial Style) ================= */}
      <header className="flex h-[46px] shrink-0 items-center justify-between border-b border-[#eaedf1] bg-white px-3.5 z-20">
        {/* Left: Brand Logo & Title */}
        <div className="flex items-center gap-6">
          <Link href={isAdmin ? '/5DRnDsWW/' : '/'} className="flex items-center gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="CamouHub" className="h-7 w-7 object-contain select-none" />
            <div className="flex items-baseline gap-0.5">
              <span className="text-[16px] font-extrabold tracking-tight text-[#0f172a]">
                Camou
              </span>
              <span className="text-[16px] font-extrabold tracking-tight text-[#1664ff]">
                Hub
              </span>
              <span className="text-[10px] font-mono text-[#94a3b8] ml-1.5 px-1.5 py-0.2 rounded bg-[#f1f5f9] border border-[#e2e8f0]">
                v1.0
              </span>
            </div>
          </Link>
        </div>

        {/* Right Status & User Panel */}
        <div className="relative flex items-center gap-3">
          {/* HubStudio-grade 更新中心 Button */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setUpdateOpen(!updateOpen)}
              title="更新中心"
              className="relative flex h-7 w-7 items-center justify-center rounded text-[#64748b] hover:bg-[#f1f5f9] hover:text-[#1664ff] transition-colors"
            >
              <DownloadCloud size={15} />
              {clientUpdate?.has_update && (
                <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-rose-500 ring-2 ring-white animate-pulse" />
              )}
            </button>

            {/* 更新中心 Popover 浮层 */}
            {updateOpen && (
              <div className="absolute right-0 top-[38px] z-50 w-[340px] rounded-lg border border-[#e2e8f0] bg-white p-4 shadow-xl text-xs animate-in fade-in zoom-in-95 duration-100">
                {/* Popover Header */}
                <div className="flex items-center justify-between border-b border-[#f1f5f9] pb-2.5 mb-3">
                  <div className="flex items-center gap-1.5 font-bold text-[#0f172a] text-sm">
                    <Sparkles size={14} className="text-[#1664ff]" />
                    <span>更新中心</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleCheckUpdate}
                    disabled={checkingUpdate}
                    className="flex items-center gap-1 text-[11px] font-medium text-[#1664ff] hover:text-[#0f54d4] transition-colors disabled:opacity-50"
                  >
                    <RefreshCw size={12} className={checkingUpdate ? 'animate-spin' : ''} />
                    <span>{checkingUpdate ? '正在检查...' : '检查更新'}</span>
                  </button>
                </div>

                {/* State B: Client update available */}
                {clientUpdate?.has_update ? (
                  <div className="mb-3 rounded-md border border-amber-200 bg-amber-50/70 p-3">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-semibold text-amber-900">
                        发现客户端新版本 v{clientUpdate.latest_version}
                      </span>
                      <span className="rounded bg-amber-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
                        NEW
                      </span>
                    </div>
                    {clientUpdate.changelog && (
                      <p className="text-[11px] text-amber-800/90 whitespace-pre-line mb-2.5 line-clamp-3">
                        {clientUpdate.changelog}
                      </p>
                    )}
                    <div className="flex items-center gap-2">
                      <a
                        href={clientUpdate.download_url || '#'}
                        target="_blank"
                        rel="noreferrer"
                        className="flex-1 rounded bg-[#1664ff] py-1.5 text-center text-xs font-semibold text-white shadow-sm hover:bg-[#0f54d4] transition-colors"
                      >
                        立即升级下载
                      </a>
                    </div>
                  </div>
                ) : null}

                {/* State C: Kernels section */}
                <div className="mb-3 space-y-1.5">
                  <div className="text-[11px] font-semibold text-[#64748b]">多引擎内核库资产</div>
                  <div className="rounded-md border border-[#f1f5f9] bg-[#f8fafc] p-2.5 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                        <span className="font-medium text-[#1e293b]">Chrome 155 (首发基准自研)</span>
                      </div>
                      <span className="text-[10px] text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">本地已激活</span>
                    </div>
                    <div className="flex items-center justify-between pt-1 border-t border-[#e2e8f0]/60">
                      <div className="flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-sky-500" />
                        <span className="font-medium text-[#1e293b]">Chrome 146 (Cloak 87项补丁)</span>
                      </div>
                      <span className="text-[10px] text-sky-600 bg-sky-50 px-1.5 py-0.5 rounded border border-sky-200">云端就绪 · 秒开</span>
                    </div>
                    <div className="flex items-center justify-between pt-1 border-t border-[#e2e8f0]/60">
                      <div className="flex items-center gap-1.5">
                        <span className="text-amber-500 text-[11px]">🦊</span>
                        <span className="font-medium text-[#1e293b]">Firefox 135 (Camoufox 原生)</span>
                      </div>
                      <span className="text-[10px] text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">本地已激活</span>
                    </div>
                  </div>
                </div>

                {/* State A: Status footer */}
                {!clientUpdate?.has_update && (
                  <div className="rounded-md bg-[#f1f5f9]/60 px-3 py-2 text-center text-[#64748b]">
                    <div className="flex items-center justify-center gap-1 text-[11px] font-medium text-emerald-600 mb-0.5">
                      <CheckCircle2 size={12} />
                      <span>客户端已是最新版本 (v1.0.0)</span>
                    </div>
                    <div className="text-[10px] text-[#94a3b8]">宿主: macOS Apple Silicon (arm64)</div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* User Profile & Plan Badge */}
          {username ? (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 pl-1">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[#e8f3ff] text-xs font-semibold text-[#1664ff]">
                  {username.slice(0, 1).toUpperCase()}
                </div>
                <span className="text-xs font-medium text-[#0f172a]">{username}</span>
                <span className="rounded bg-[#fff7e6] px-1.5 py-0.2 text-[10px] font-bold text-[#d48806] border border-[#ffe58f]">
                  {role === 'admin'
                    ? 'ADMIN'
                    : language === 'zh'
                    ? (planId === 'enterprise' ? '企业版' : planId === 'pro' ? '专业版' : planId === 'starter' ? '入门版' : planId === 'free' ? '免费版' : planId?.toUpperCase() || 'VIP')
                    : (planId || 'VIP').toUpperCase()}
                </span>
              </div>

              {/* Logout Button */}
              <button
                type="button"
                onClick={logout}
                title="退出登录"
                className="flex h-7 w-7 items-center justify-center rounded text-[#94a3b8] hover:bg-[#f1f5f9] hover:text-[#ef4444] transition-colors"
              >
                <LogOut size={13} />
              </button>
            </div>
          ) : (
            <LanguageToggle />
          )}
        </div>
      </header>

      {/* ================= 2. MAIN WORKSPACE (Sidebar + Content) ================= */}
      <div className="flex flex-1 min-h-0">
        {/* Left Sidebar */}
        <aside className="flex w-[180px] shrink-0 flex-col border-r border-[#eaedf1] bg-white select-none">
          {isAdmin ? (
            /* Admin navigation */
            <div className="flex flex-col gap-1 p-2">
              <div className="px-2.5 py-2 text-[11px] font-semibold text-[#94a3b8] uppercase">
                {language === 'zh' ? '管理控制台' : 'ADMIN CONSOLE'}
              </div>
              {ADMIN_NAV_ITEMS.map((item) => {
                const Icon = item.icon
                const active = activeTab === item.id
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setActiveTab(item.id)}
                    className={`flex items-center gap-2.5 rounded-md px-2.5 py-2 text-xs font-medium transition-all text-left cursor-pointer ${
                      active
                        ? 'bg-[#e8f3ff] text-[#1664ff] font-semibold'
                        : 'text-[#475569] hover:bg-[#f8fafc] hover:text-[#0f172a]'
                    }`}
                  >
                    <Icon size={15} strokeWidth={1.8} className={active ? 'text-[#1664ff]' : ''} />
                    <span>{language === 'zh' ? item.labelZh : item.labelEn}</span>
                  </button>
                )
              })}
            </div>
          ) : (
            /* Client Commercial Sidebar (Real features only) */
            <>
              <nav className="flex flex-col gap-0.5 p-2">
                {SIDEBAR_ITEMS.map((item) => {
                  const Icon = item.icon
                  const active =
                    item.id === 'environments'
                      ? current === '/' && !filterParam
                      : item.id === 'favorite'
                        ? current === '/' && filterParam === 'favorite'
                        : item.id === 'recent'
                          ? current === '/' && filterParam === 'recent'
                          : current.startsWith(item.href.replace(/\/$/, ''))

                  return (
                    <Link
                      key={item.id}
                      href={item.href}
                      className={`flex items-center justify-between rounded-md px-2.5 py-2 text-xs font-medium transition-colors ${
                        active
                          ? 'bg-[#e8f3ff] text-[#1664ff] font-semibold'
                          : 'text-[#475569] hover:bg-[#f8fafc] hover:text-[#0f172a]'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon size={15} strokeWidth={1.8} className={active ? 'text-[#1664ff]' : ''} />
                        <span>{item.label}</span>
                      </div>
                    </Link>
                  )
                })}
              </nav>

              {/* Bottom Quota Status Card */}
              <div className="mt-auto p-2.5 flex flex-col gap-2">
                <div className="rounded-lg border border-[#e2e8f0] bg-[#f8fafc] p-2.5 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="rounded bg-[#f1f5f9] px-1.5 py-0.5 text-[10px] font-semibold text-[#1664ff] border border-[#d0e2ff]">
                      {language === 'zh'
                        ? (planId === 'enterprise' ? '企业版' : planId === 'pro' ? '专业版' : planId === 'starter' ? '入门版' : planId === 'free' ? '免费版' : planId?.toUpperCase() || '标准版')
                        : (planId ? planId.toUpperCase() : 'STANDARD')}
                    </span>
                    <button
                      type="button"
                      onClick={() => setBillingOpen(true)}
                      className="text-[11px] font-semibold text-[#1664ff] hover:underline cursor-pointer"
                    >
                      升级套餐
                    </button>
                  </div>
                  <div className="mt-2 text-[11px] text-[#64748b]">
                    环境配额使用{' '}
                    <span className="font-semibold text-[#0f172a]">
                      {usedProfiles} / {maxProfiles || 20}
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}
        </aside>

        {/* Right Work Content Area */}
        <main className="min-w-0 flex-1 overflow-y-auto bg-[#f4f6fa]">
          {children}
        </main>
      </div>

      <BillingModal open={billingOpen} onClose={() => setBillingOpen(false)} />
    </div>
  )
}
