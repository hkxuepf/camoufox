'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'

import { useAuth } from '@/components/login-gate'
import { BillingModal } from '@/components/billing-modal'
import { AdminTab, useAdminContext } from '@/components/admin-context'
import { systemAPI } from '@/lib/api'
import { useI18n, LanguageToggle } from '@/lib/i18n'
import {
  Bell,
  Clock,
  FolderTree,
  Globe,
  Layers,
  LayoutDashboard,
  LogOut,
  Monitor,
  Package,
  RotateCw,
  Settings,
  Shield,
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
    { href: '/api-service/', id: 'api-service', label: '开发者中心', icon: Terminal },
    { href: '/trash/', id: 'trash', label: '回收站', icon: Trash2 },
    { href: '/settings/', id: 'settings', label: '系统设置', icon: Settings },
  ]

  // Actual supported top tabs
  const TOP_TABS = [
    { id: 'browser', label: '浏览器', href: '/' },
    { id: 'proxies', label: '代理管理', href: '/proxies/' },
    { id: 'extensions', label: '扩展中心', href: '/extensions/' },
    { id: 'groups', label: '环境分组', href: '/groups/' },
    { id: 'schedules', label: '定时计划', href: '/schedules/' },
    { id: 'api-service', label: '开发者中心', href: '/api-service/' },
    { id: 'billing', label: '费用与套餐', onClick: () => setBillingOpen(true) },
    { id: 'settings', label: '系统设置', href: '/settings/' },
  ]

  return (
    <div className="flex h-screen flex-col bg-[#f4f6fa] select-none text-[#1e293b]">
      {/* ================= 1. TOP HEADER (Hub Commercial Style) ================= */}
      <header className="flex h-[46px] shrink-0 items-center justify-between border-b border-[#eaedf1] bg-white px-3.5 z-20">
        {/* Left: Brand Logo & Title */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
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

          {/* Top Navigation Tabs (Only our actual real features) */}
          {!isAdmin && (
            <nav className="flex items-center gap-1 pl-2">
              {TOP_TABS.map((tab) => {
                const isTabActive = tab.href
                  ? tab.href === '/'
                    ? current === '/' && !filterParam
                    : current.startsWith(tab.href.replace(/\/$/, ''))
                  : false

                if (tab.href) {
                  return (
                    <Link
                      key={tab.id}
                      href={tab.href}
                      className={`relative flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium transition-colors cursor-pointer ${
                        isTabActive
                          ? 'text-[#1664ff] font-semibold'
                          : 'text-[#475569] hover:text-[#0f172a]'
                      }`}
                    >
                      <span>{tab.label}</span>
                      {isTabActive && (
                        <span className="absolute bottom-[-6px] left-3 right-3 h-[2px] rounded-full bg-[#1664ff]" />
                      )}
                    </Link>
                  )
                }

                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={tab.onClick}
                    className="relative flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium transition-colors cursor-pointer text-[#475569] hover:text-[#0f172a]"
                  >
                    <span>{tab.label}</span>
                  </button>
                )
              })}
            </nav>
          )}
        </div>

        {/* Right Status & User Panel */}
        <div className="flex items-center gap-3">
          {/* Refresh / Server status */}
          <div
            className="flex items-center gap-1 text-[11px] text-[#64748b] bg-[#f8fafc] border border-[#eaedf1] px-2 py-0.5 rounded"
            title="本地服务核心"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-[#10b981]" />
            <span className="font-mono">{address || '127.0.0.1'}</span>
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
                管理控制台
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
                    <span>{item.labelZh}</span>
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
        <main className="min-w-0 flex-1 overflow-y-auto bg-[#f4f6fa] p-3">
          {children}
        </main>
      </div>

      <BillingModal open={billingOpen} onClose={() => setBillingOpen(false)} />
    </div>
  )
}
