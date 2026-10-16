'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle,
  Copy,
  DollarSign,
  Edit2,
  KeyRound,
  Layers,
  LayoutDashboard,
  Loader2,
  Lock,
  Package,
  Plus,
  RefreshCw,
  Save,
  Search,
  Server,
  Settings,
  Shield,
  Trash2,
  UserCheck,
  Users,
  Wallet,
  X,
} from 'lucide-react'

import {
  adminAPI,
  type AdminStats,
  type AdminUser,
  type Order,
  type Plan,
} from '@/lib/api'
import { useAuth } from '@/components/login-gate'
import { useAdminContext } from '@/components/admin-context'
import { useI18n, LanguageToggle } from '@/lib/i18n'
import { AdminReleasesView } from '@/components/admin-releases'

export default function AdminConsolePage() {
  const { role } = useAuth()
  const { t, language } = useI18n()
  const { activeTab, setActiveTab } = useAdminContext()
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [userRoleTab, setUserRoleTab] = useState<'client' | 'admin'>('client')
  const [plans, setPlans] = useState<Plan[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [adminSettings, setAdminSettings] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [actionBusy, setActionBusy] = useState(false)

  // Dialog states
  const [createUserOpen, setCreateUserOpen] = useState(false)
  const [newUserData, setNewUserData] = useState({
    username: '',
    password: '',
    role: 'user',
    plan_id: 'pro',
    max_profiles: 60,
    max_concurrent: 5,
    duration_days: 30,
  })

  const [editUser, setEditUser] = useState<AdminUser | null>(null)
  const [resetPwdUser, setResetPwdUser] = useState<AdminUser | null>(null)
  const [newPassword, setNewPassword] = useState('')

  const [editPlan, setEditPlan] = useState<Plan | null>(null)

  const [settingsForm, setSettingsForm] = useState({
    usdt_wallet_address: '',
    usdt_network: 'TRC20',
    payment_gateway_url: '',
    payment_gateway_secret: '',
  })

  const [userSearch, setUserSearch] = useState('')
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3000)
  }

  const loadData = async () => {
    setLoading(true)
    try {
      const [s, u, p, o, set] = await Promise.all([
        adminAPI.getDashboard(),
        adminAPI.getUsers(),
        adminAPI.getPlans(),
        adminAPI.getOrders(),
        adminAPI.getSettings(),
      ])
      setStats(s)
      setUsers(u)
      setPlans(p)
      setOrders(o)
      setAdminSettings(set)
      setSettingsForm({
        usdt_wallet_address: set.usdt_wallet_address || '',
        usdt_network: set.usdt_network || 'TRC20',
        payment_gateway_url: set.payment_gateway_url || '',
        payment_gateway_secret: set.payment_gateway_secret || '',
      })
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  if (role !== 'admin') {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-canvas p-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-danger/15 text-danger">
          <Lock size={32} />
        </div>
        <h1 className="text-xl font-bold text-ink">
          {language === 'zh' ? '访问受限：需要管理员权限' : 'Access Restricted: Administrator Only'}
        </h1>
        <p className="max-w-md text-sm text-ink-dim">
          {language === 'zh'
            ? '当前登录账户不是系统管理员，无法访问此后台。请使用管理员账户登录。'
            : 'Your current account does not have administrator privileges to access this console.'}
        </p>
        <Link href="/" className="btn btn-primary mt-2">
          {language === 'zh' ? '返回工作台' : 'Back to Workbench'}
        </Link>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas text-ink">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-lg border border-line bg-surface px-4 py-2.5 text-xs font-medium text-ink shadow-2xl animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle size={16} className="text-emerald-400" />
          {toastMessage}
        </div>
      )}

      {/* Top Header */}
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-line bg-surface/90 px-6 backdrop-blur">
        <div className="flex items-center gap-3">
          <span className="flex h-6 items-center rounded bg-signal/15 px-2 font-mono text-xs font-semibold text-signal">
            ADMIN
          </span>
          <span className="text-sm font-semibold text-ink">
            {language === 'zh' ? '管理控制台' : 'Admin Console'}
          </span>
          <span className="text-xs text-ink-dim">
            / {
              activeTab === 'dashboard' ? (language === 'zh' ? '数据看板' : 'Dashboard') :
              activeTab === 'users' ? (language === 'zh' ? '用户与配额管理' : 'User Management') :
              activeTab === 'plans' ? (language === 'zh' ? '套餐配置' : 'Plan Settings') :
              activeTab === 'orders' ? (language === 'zh' ? 'USDT 订单记录' : 'USDT Orders') :
              activeTab === 'releases' ? (language === 'zh' ? '版本与内核中台' : 'Releases & Kernels') :
              (language === 'zh' ? '支付与系统设置' : 'Payment & System Settings')
            }
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-md border border-line bg-raised/50 px-2.5 py-1 text-xs text-ink-dim hover:bg-raised hover:text-ink transition-colors cursor-pointer"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            {language === 'zh' ? '刷新数据' : 'Refresh'}
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-6">
        {/* --- TAB 1: DASHBOARD --- */}
        {activeTab === 'dashboard' && (
          <div className="flex flex-col gap-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-line bg-surface p-4">
                <div className="flex items-center justify-between text-ink-dim">
                  <span className="text-xs">{language === 'zh' ? '总注册用户' : 'Total Users'}</span>
                  <Users size={16} className="text-signal" />
                </div>
                <div className="mt-2 text-2xl font-bold text-ink">
                  {stats?.user_count ?? '—'}
                </div>
                <div className="mt-1 text-[11px] text-ink-dim">
                  {language === 'zh' ? '系统已注册账号总数' : 'Registered user accounts'}
                </div>
              </div>

              <div className="rounded-xl border border-line bg-surface p-4">
                <div className="flex items-center justify-between text-ink-dim">
                  <span className="text-xs">{language === 'zh' ? '指纹环境总数' : 'Total Profiles'}</span>
                  <Layers size={16} className="text-blue-400" />
                </div>
                <div className="mt-2 text-2xl font-bold text-ink">
                  {stats?.profile_count ?? '—'}
                </div>
                <div className="mt-1 text-[11px] text-ink-dim">
                  {language === 'zh' ? '未进回收站的活跃环境' : 'Active browser profiles'}
                </div>
              </div>

              <div className="rounded-xl border border-line bg-surface p-4">
                <div className="flex items-center justify-between text-ink-dim">
                  <span className="text-xs">{language === 'zh' ? '多开运行中' : 'Running Browsers'}</span>
                  <Activity size={16} className="text-emerald-400" />
                </div>
                <div className="mt-2 text-2xl font-bold text-emerald-400">
                  {stats?.active_running ?? 0}
                </div>
                <div className="mt-1 text-[11px] text-ink-dim">
                  {language === 'zh' ? '当前正在打开的浏览器实例' : 'Currently active browser instances'}
                </div>
              </div>

              <div className="rounded-xl border border-line bg-surface p-4">
                <div className="flex items-center justify-between text-ink-dim">
                  <span className="text-xs">{language === 'zh' ? 'USDT 累计收入' : 'USDT Revenue'}</span>
                  <DollarSign size={16} className="text-amber-400" />
                </div>
                <div className="mt-2 text-2xl font-bold text-amber-400">
                  {stats?.total_revenue_usdt ?? 0} USDT
                </div>
                <div className="mt-1 text-[11px] text-ink-dim">
                  {language === 'zh'
                    ? `已完成 ${stats?.paid_orders ?? 0} 笔支付订单`
                    : `${stats?.paid_orders ?? 0} orders fulfilled`}
                </div>
              </div>
            </div>

            {/* Quick Actions & Recent orders */}
            <div className="rounded-xl border border-line bg-surface p-5">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <h3 className="text-sm font-semibold text-ink">
                  {language === 'zh' ? '最新 USDT 交易记录' : 'Recent USDT Orders'}
                </h3>
                <button
                  onClick={() => setActiveTab('orders')}
                  className="text-xs text-signal hover:underline"
                >
                  {language === 'zh' ? '查看全部订单' : 'View All'}
                </button>
              </div>

              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-line text-ink-dim">
                    <tr>
                      <th className="py-2">{language === 'zh' ? '订单编号' : 'Order No.'}</th>
                      <th className="py-2">{language === 'zh' ? '用户' : 'User'}</th>
                      <th className="py-2">{language === 'zh' ? '套餐' : 'Plan'}</th>
                      <th className="py-2">{language === 'zh' ? '金额' : 'Amount'}</th>
                      <th className="py-2">{language === 'zh' ? '网络' : 'Network'}</th>
                      <th className="py-2">{language === 'zh' ? '状态' : 'Status'}</th>
                      <th className="py-2">{language === 'zh' ? '时间' : 'Time'}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line/60">
                    {orders.slice(0, 5).map((order) => (
                      <tr key={order.id} className="hover:bg-raised/40">
                        <td className="py-2 font-mono text-ink">{order.order_no}</td>
                        <td className="py-2 text-ink">{order.username}</td>
                        <td className="py-2 text-ink">{order.plan_name}</td>
                        <td className="py-2 font-bold text-signal">{order.amount_usdt} USDT</td>
                        <td className="py-2 text-ink-dim">{order.pay_network}</td>
                        <td className="py-2">
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                              order.status === 'paid'
                                ? 'bg-emerald-500/15 text-emerald-400'
                                : 'bg-amber-500/15 text-amber-400'
                            }`}
                          >
                            {order.status}
                          </span>
                        </td>
                        <td className="py-2 text-ink-dim">
                          {new Date(order.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                    {orders.length === 0 && (
                      <tr>
                        <td colSpan={7} className="py-6 text-center text-ink-dim">
                          {language === 'zh' ? '暂无订单' : 'No orders yet'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* --- TAB 2: USERS MANAGEMENT --- */}
        {activeTab === 'users' && (() => {
          const clientUsers = users.filter((u) => u.role !== 'admin')
          const adminUsers = users.filter((u) => u.role === 'admin')

          return (
            <div className="flex flex-col gap-4">
              {/* Sub-tab selection & Actions */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
                <div className="flex items-center gap-1.5 rounded-lg border border-line bg-raised/40 p-1">
                  <button
                    type="button"
                    onClick={() => setUserRoleTab('client')}
                    className={`flex items-center gap-2 rounded-md px-3.5 py-1.5 text-xs font-medium transition-all cursor-pointer ${
                      userRoleTab === 'client'
                        ? 'bg-signal text-white shadow-xs font-semibold'
                        : 'text-ink-dim hover:text-ink hover:bg-raised'
                    }`}
                  >
                    <Users size={14} />
                    <span>{language === 'zh' ? '客户账号列表' : 'Client Accounts'}</span>
                    <span
                      className={`rounded-full px-1.5 py-0.2 text-[10px] font-mono ${
                        userRoleTab === 'client' ? 'bg-black/25 text-white' : 'bg-line text-ink-dim'
                      }`}
                    >
                      {clientUsers.length}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setUserRoleTab('admin')}
                    className={`flex items-center gap-2 rounded-md px-3.5 py-1.5 text-xs font-medium transition-all cursor-pointer ${
                      userRoleTab === 'admin'
                        ? 'bg-signal text-white shadow-xs font-semibold'
                        : 'text-ink-dim hover:text-ink hover:bg-raised'
                    }`}
                  >
                    <Shield size={14} />
                    <span>{language === 'zh' ? '平台管理员列表' : 'Platform Administrators'}</span>
                    <span
                      className={`rounded-full px-1.5 py-0.2 text-[10px] font-mono ${
                        userRoleTab === 'admin' ? 'bg-black/25 text-white' : 'bg-line text-ink-dim'
                      }`}
                    >
                      {adminUsers.length}
                    </span>
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search size={14} className="absolute left-2.5 top-2.5 text-ink-dim" />
                    <input
                      type="text"
                      placeholder={language === 'zh' ? '搜索账号...' : 'Search username...'}
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      className="field pl-8 text-xs w-52"
                    />
                  </div>

                  {userRoleTab === 'client' ? (
                    <button
                      onClick={() => {
                        setNewUserData({
                          username: '',
                          password: '',
                          role: 'user',
                          plan_id: plans[0]?.id || 'pro',
                          max_profiles: 60,
                          max_concurrent: 5,
                          duration_days: 30,
                        })
                        setCreateUserOpen(true)
                      }}
                      className="btn btn-primary flex items-center gap-1.5 text-xs cursor-pointer"
                    >
                      <Plus size={14} />
                      {language === 'zh' ? '新建客户账号' : 'Add Client'}
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        setNewUserData({
                          username: '',
                          password: '',
                          role: 'admin',
                          plan_id: 'admin',
                          max_profiles: 0,
                          max_concurrent: 0,
                          duration_days: 0,
                        })
                        setCreateUserOpen(true)
                      }}
                      className="btn btn-primary flex items-center gap-1.5 text-xs cursor-pointer"
                    >
                      <Plus size={14} />
                      {language === 'zh' ? '添加管理员' : 'Add Admin'}
                    </button>
                  )}
                </div>
              </div>

              {/* View 1: Client Users Table */}
              {userRoleTab === 'client' && (
                <div className="overflow-x-auto rounded-xl border border-line bg-surface">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-line bg-raised/30 text-ink-dim">
                      <tr>
                        <th className="p-3">{language === 'zh' ? '客户账号' : 'Client Username'}</th>
                        <th className="p-3">{language === 'zh' ? '当前订阅套餐' : 'Plan'}</th>
                        <th className="p-3">{language === 'zh' ? '环境配额 (已用/上限)' : 'Quota'}</th>
                        <th className="p-3">{language === 'zh' ? '多开并发数' : 'Max Concurrent'}</th>
                        <th className="p-3">{language === 'zh' ? '套餐到期时间' : 'Expires At'}</th>
                        <th className="p-3">{language === 'zh' ? '账号状态' : 'Status'}</th>
                        <th className="p-3 text-right">{language === 'zh' ? '操作' : 'Actions'}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line/60">
                      {clientUsers
                        .filter((u) => u.username.toLowerCase().includes(userSearch.toLowerCase()))
                        .map((user) => (
                          <tr key={user.id} className="hover:bg-raised/40">
                            <td className="p-3 font-semibold text-ink">{user.username}</td>
                            <td className="p-3">
                              <span className="rounded bg-signal/15 px-2 py-0.5 text-[11px] font-semibold text-signal">
                                {user.plan_id}
                              </span>
                            </td>
                            <td className="p-3 font-mono">
                              <span className="text-signal font-semibold">{user.used_profiles ?? 0}</span> / {user.max_profiles}
                            </td>
                            <td className="p-3 font-mono text-ink">{user.max_concurrent}</td>
                            <td className="p-3 text-ink-dim">
                              {user.expires_at ? new Date(user.expires_at).toLocaleDateString() : '永久有效 / 无限制'}
                            </td>
                            <td className="p-3">
                              <span
                                className={`rounded px-1.5 py-0.5 text-[10px] ${
                                  user.status === 'active'
                                    ? 'bg-emerald-500/15 text-emerald-400'
                                    : 'bg-danger/15 text-danger'
                                }`}
                              >
                                {user.status}
                              </span>
                            </td>
                            <td className="p-3 text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                <button
                                  onClick={() => setEditUser(user)}
                                  className="rounded p-1 text-ink-dim hover:bg-raised hover:text-ink cursor-pointer"
                                  title={language === 'zh' ? '编辑客户配额与套餐' : 'Edit Quota'}
                                >
                                  <Edit2 size={13} />
                                </button>
                                <button
                                  onClick={() => {
                                    setResetPwdUser(user)
                                    setNewPassword('')
                                  }}
                                  className="rounded p-1 text-ink-dim hover:bg-raised hover:text-ink cursor-pointer"
                                  title={language === 'zh' ? '重置客户密码' : 'Reset Password'}
                                >
                                  <KeyRound size={13} />
                                </button>
                                <button
                                  onClick={async () => {
                                    if (confirm(`确认删除客户账号 ${user.username}？`)) {
                                      await adminAPI.deleteUser(user.username)
                                      showToast('客户账号已删除')
                                      loadData()
                                    }
                                  }}
                                  className="rounded p-1 text-ink-dim hover:bg-danger/15 hover:text-danger cursor-pointer"
                                  title={language === 'zh' ? '删除客户' : 'Delete'}
                                >
                                  <Trash2 size={13} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      {clientUsers.length === 0 && (
                        <tr>
                          <td colSpan={7} className="p-8 text-center text-ink-dim">
                            {language === 'zh'
                              ? '暂无客户账号。客户在本地客户端使用云端模式登录注册，或点击右上角「新建客户账号」添加。'
                              : 'No client accounts found.'}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {/* View 2: Administrators Table */}
              {userRoleTab === 'admin' && (
                <div className="overflow-x-auto rounded-xl border border-line bg-surface">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-line bg-raised/30 text-ink-dim">
                      <tr>
                        <th className="p-3">{language === 'zh' ? '管理员账号' : 'Admin Account'}</th>
                        <th className="p-3">{language === 'zh' ? '管理级别' : 'Access Level'}</th>
                        <th className="p-3">{language === 'zh' ? '管理职责范围' : 'Permissions Scope'}</th>
                        <th className="p-3">{language === 'zh' ? '账号状态' : 'Status'}</th>
                        <th className="p-3 text-right">{language === 'zh' ? '操作' : 'Actions'}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line/60">
                      {adminUsers
                        .filter((u) => u.username.toLowerCase().includes(userSearch.toLowerCase()))
                        .map((user) => (
                          <tr key={user.id} className="hover:bg-raised/40">
                            <td className="p-3 font-semibold text-ink">
                              <div className="flex items-center gap-2">
                                <div className="flex h-6 w-6 items-center justify-center rounded bg-signal/15 text-signal">
                                  <Shield size={13} />
                                </div>
                                <span className="text-ink font-semibold">{user.username}</span>
                              </div>
                            </td>
                            <td className="p-3">
                              <span className="rounded bg-signal/20 px-2 py-0.5 text-[10px] font-bold text-signal font-mono">
                                SUPER_ADMIN
                              </span>
                            </td>
                            <td className="p-3 text-ink-dim">
                              {language === 'zh'
                                ? '平台最高管理控制权限（用户、套餐规格、USDT 收款财务、系统网关）'
                                : 'Full platform control over users, plans, billing, and system settings'}
                            </td>
                            <td className="p-3">
                              <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] text-emerald-400 font-medium">
                                {user.status}
                              </span>
                            </td>
                            <td className="p-3 text-right">
                              <div className="flex items-center justify-end gap-1.5">
                                <button
                                  onClick={() => {
                                    setResetPwdUser(user)
                                    setNewPassword('')
                                  }}
                                  className="btn btn-secondary py-1 px-2.5 text-[11px] flex items-center gap-1.5 cursor-pointer"
                                  title={language === 'zh' ? '重置管理员密码' : 'Reset Password'}
                                >
                                  <KeyRound size={12} />
                                  <span>{language === 'zh' ? '修改密码' : 'Change Password'}</span>
                                </button>
                                {user.username !== 'fgwl' && user.username !== 'admin' && (
                                  <button
                                    onClick={async () => {
                                      if (confirm(`确认移除管理员 ${user.username}？`)) {
                                        await adminAPI.deleteUser(user.username)
                                        showToast('管理员已移除')
                                        loadData()
                                      }
                                    }}
                                    className="rounded p-1 text-ink-dim hover:bg-danger/15 hover:text-danger cursor-pointer"
                                    title={language === 'zh' ? '删除管理员' : 'Delete'}
                                  >
                                    <Trash2 size={13} />
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )
        })()}

        {/* --- TAB 3: PLANS CONFIGURATION --- */}
        {activeTab === 'plans' && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-ink">
                  {language === 'zh' ? '订阅套餐列表' : 'Subscription Plans'}
                </h3>
                <p className="text-xs text-ink-dim">
                  {language === 'zh' ? '配置前台用户充值所购买的套餐规格与限制' : 'Configure subscription tiers & quotas'}
                </p>
              </div>
              <button
                onClick={() =>
                  setEditPlan({
                    id: 'custom_' + Date.now().toString().slice(-4),
                    name: '新套餐',
                    max_profiles: 50,
                    max_concurrent: 4,
                    duration_days: 30,
                    price_usdt: 20,
                    description: '',
                  })
                }
                className="btn btn-primary flex items-center gap-1.5 text-xs"
              >
                <Plus size={14} />
                {language === 'zh' ? '添加套餐' : 'New Plan'}
              </button>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {plans.map((plan) => (
                <div key={plan.id} className="flex flex-col justify-between rounded-xl border border-line bg-surface p-4">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold text-ink">{plan.name}</span>
                      <span className="font-mono text-xs text-ink-dim">ID: {plan.id}</span>
                    </div>
                    <div className="mt-2 flex items-baseline gap-1">
                      <span className="text-2xl font-black text-signal">{plan.price_usdt}</span>
                      <span className="text-xs text-ink-dim">USDT / {plan.duration_days} 天</span>
                    </div>
                    <p className="mt-2 text-xs text-ink-dim">{plan.description || '—'}</p>

                    <div className="mt-4 flex flex-col gap-1.5 border-t border-line pt-3 text-xs">
                      <div className="flex justify-between">
                        <span className="text-ink-dim">环境上限:</span>
                        <span className="font-semibold text-ink">{plan.max_profiles}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-ink-dim">多开并发:</span>
                        <span className="font-semibold text-ink">{plan.max_concurrent}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 flex justify-end gap-2 border-t border-line pt-3">
                    <button
                      onClick={() => setEditPlan(plan)}
                      className="btn btn-secondary text-xs"
                    >
                      {language === 'zh' ? '编辑' : 'Edit'}
                    </button>
                    {plan.id !== 'free' && (
                      <button
                        onClick={async () => {
                          if (confirm(`确定删除套餐 ${plan.name}？`)) {
                            await adminAPI.deletePlan(plan.id)
                            showToast('套餐已删除')
                            loadData()
                          }
                        }}
                        className="btn btn-danger text-xs"
                      >
                        {language === 'zh' ? '删除' : 'Delete'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* --- TAB 4: USDT ORDERS & MANUAL CONFIRM --- */}
        {activeTab === 'orders' && (
          <div className="flex flex-col gap-4">
            <div>
              <h3 className="text-sm font-semibold text-ink">
                {language === 'zh' ? 'USDT 充值订单列表' : 'USDT Recharge Orders'}
              </h3>
              <p className="text-xs text-ink-dim">
                {language === 'zh'
                  ? '如用户已在链上转账，可点击“确认到账/手动补单”，系统将即刻为用户升级并延长有效期'
                  : 'Click "Manual Confirm" to activate subscription instantly for pending orders.'}
              </p>
            </div>

            <div className="overflow-x-auto rounded-xl border border-line bg-surface">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-line bg-raised/30 text-ink-dim">
                  <tr>
                    <th className="p-3">{language === 'zh' ? '订单编号' : 'Order No.'}</th>
                    <th className="p-3">{language === 'zh' ? '用户账号' : 'Username'}</th>
                    <th className="p-3">{language === 'zh' ? '订阅套餐' : 'Plan'}</th>
                    <th className="p-3">{language === 'zh' ? '金额' : 'Amount'}</th>
                    <th className="p-3">{language === 'zh' ? '网络' : 'Network'}</th>
                    <th className="p-3">{language === 'zh' ? '交易哈希 TxHash' : 'TxHash'}</th>
                    <th className="p-3">{language === 'zh' ? '状态' : 'Status'}</th>
                    <th className="p-3">{language === 'zh' ? '创建时间' : 'Created At'}</th>
                    <th className="p-3 text-right">{language === 'zh' ? '操作' : 'Action'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/60">
                  {orders.map((order) => (
                    <tr key={order.id} className="hover:bg-raised/40">
                      <td className="p-3 font-mono font-medium text-ink">{order.order_no}</td>
                      <td className="p-3 text-ink font-semibold">{order.username}</td>
                      <td className="p-3 text-ink">{order.plan_name}</td>
                      <td className="p-3 font-bold text-signal">{order.amount_usdt} USDT</td>
                      <td className="p-3 text-ink-dim">{order.pay_network}</td>
                      <td className="p-3 font-mono text-[11px] text-ink-dim max-w-[140px] truncate" title={order.tx_hash || ''}>
                        {order.tx_hash || '—'}
                      </td>
                      <td className="p-3">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                            order.status === 'paid'
                              ? 'bg-emerald-500/15 text-emerald-400'
                              : 'bg-amber-500/15 text-amber-400'
                          }`}
                        >
                          {order.status}
                        </span>
                      </td>
                      <td className="p-3 text-ink-dim">
                        {new Date(order.created_at).toLocaleString()}
                      </td>
                      <td className="p-3 text-right">
                        {order.status === 'pending' ? (
                          <button
                            onClick={async () => {
                              if (confirm(`确认手动给用户 ${order.username} 确认该笔 ${order.amount_usdt} USDT 订单并开通套餐？`)) {
                                await adminAPI.confirmOrder(order.order_no)
                                showToast('已成功确认到账并开通套餐')
                                loadData()
                              }
                            }}
                            className="btn btn-primary text-[11px] py-1 px-2.5 font-medium"
                          >
                            {language === 'zh' ? '确认到账 (补单)' : 'Manual Confirm'}
                          </button>
                        ) : (
                          <span className="text-[11px] text-emerald-400 flex items-center justify-end gap-1">
                            <Check size={12} /> {language === 'zh' ? '已开通' : 'Fulfilled'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {orders.length === 0 && (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-ink-dim">
                        {language === 'zh' ? '暂无订单记录' : 'No order records'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* --- TAB: RELEASES & MULTI-KERNEL CENTER --- */}
        {activeTab === 'releases' && (
          <AdminReleasesView language={language} />
        )}

        {/* --- TAB 5: PAYMENT GATEWAY SETTINGS --- */}
        {activeTab === 'settings' && (
          <div className="flex max-w-2xl flex-col gap-5 rounded-xl border border-line bg-surface p-6">
            <div>
              <h3 className="text-sm font-semibold text-ink">
                {language === 'zh' ? 'USDT 支付收款配置' : 'USDT Gateway Configuration'}
              </h3>
              <p className="text-xs text-ink-dim">
                {language === 'zh'
                  ? '配置前台充值弹窗所显示的 USDT 收款地址以及自动回调参数'
                  : 'Set receiving wallet address and webhook parameters'}
              </p>
            </div>

            <div className="flex flex-col gap-4 text-xs">
              <label className="flex flex-col gap-1.5">
                <span className="font-medium text-ink">
                  {language === 'zh' ? 'USDT (TRC20) 收款钱包地址' : 'USDT TRC20 Wallet Address'}
                </span>
                <input
                  type="text"
                  value={settingsForm.usdt_wallet_address}
                  onChange={(e) => setSettingsForm({ ...settingsForm, usdt_wallet_address: e.target.value })}
                  placeholder="TYDnyQfxxxxxxxSAMPLEWALLETaddress"
                  className="field font-mono"
                />
                <span className="text-ink-dim text-[11px]">
                  {language === 'zh' ? '用户在客户端或网页充值时将直接转账至此地址' : 'Users transfer directly to this address'}
                </span>
              </label>

              <label className="flex flex-col gap-1.5">
                <span className="font-medium text-ink">
                  {language === 'zh' ? '网络类型' : 'Network Type'}
                </span>
                <input
                  type="text"
                  value={settingsForm.usdt_network}
                  onChange={(e) => setSettingsForm({ ...settingsForm, usdt_network: e.target.value })}
                  placeholder="TRC20"
                  className="field"
                />
              </label>

              <label className="flex flex-col gap-1.5">
                <span className="font-medium text-ink">
                  {language === 'zh' ? '第三方支付网关 URL (可选)' : 'Payment Gateway Webhook URL (Optional)'}
                </span>
                <input
                  type="text"
                  value={settingsForm.payment_gateway_url}
                  onChange={(e) => setSettingsForm({ ...settingsForm, payment_gateway_url: e.target.value })}
                  placeholder="https://api.gateway.com/webhook"
                  className="field"
                />
              </label>

              <label className="flex flex-col gap-1.5">
                <span className="font-medium text-ink">
                  {language === 'zh' ? '支付网关签名密钥 (Secret)' : 'Gateway Secret Key'}
                </span>
                <input
                  type="password"
                  value={settingsForm.payment_gateway_secret}
                  onChange={(e) => setSettingsForm({ ...settingsForm, payment_gateway_secret: e.target.value })}
                  placeholder="secret key for validating webhook signatures"
                  className="field"
                />
              </label>

              <div className="pt-2">
                <button
                  onClick={async () => {
                    setActionBusy(true)
                    try {
                      await adminAPI.updateSettings(settingsForm)
                      showToast('支付配置已保存')
                    } catch (err) {
                      alert(err)
                    } finally {
                      setActionBusy(false)
                    }
                  }}
                  disabled={actionBusy}
                  className="btn btn-primary flex items-center gap-1.5 text-xs px-5 py-2 font-medium"
                >
                  <Save size={14} />
                  {language === 'zh' ? '保存支付配置' : 'Save Settings'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* --- CREATE USER MODAL --- */}
      {createUserOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-md flex-col gap-4 rounded-xl border border-line bg-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <h3 className="text-sm font-semibold text-ink">
                {language === 'zh' ? '创建新用户' : 'Create User'}
              </h3>
              <button onClick={() => setCreateUserOpen(false)} className="text-ink-dim hover:text-ink">
                <X size={16} />
              </button>
            </div>

            <div className="flex flex-col gap-3 text-xs">
              <label className="flex flex-col gap-1">
                <span className="text-ink-dim">用户名</span>
                <input
                  type="text"
                  value={newUserData.username}
                  onChange={(e) => setNewUserData({ ...newUserData, username: e.target.value })}
                  className="field"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-ink-dim">登录密码</span>
                <input
                  type="password"
                  value={newUserData.password}
                  onChange={(e) => setNewUserData({ ...newUserData, password: e.target.value })}
                  className="field"
                />
              </label>
              <div className="grid grid-cols-2 gap-2">
                <label className="flex flex-col gap-1">
                  <span className="text-ink-dim">账号类型</span>
                  <select
                    value={newUserData.role}
                    onChange={(e) => setNewUserData({ ...newUserData, role: e.target.value })}
                    className="field"
                  >
                    <option value="user">普通客户账号 (Client)</option>
                    <option value="admin">平台管理员 (Administrator)</option>
                  </select>
                </label>
                {newUserData.role === 'user' ? (
                  <label className="flex flex-col gap-1">
                    <span className="text-ink-dim">绑定套餐</span>
                    <select
                      value={newUserData.plan_id}
                      onChange={(e) => setNewUserData({ ...newUserData, plan_id: e.target.value })}
                      className="field"
                    >
                      {plans.map((p) => (
                        <option key={p.id} value={p.id}>{p.name} ({p.id})</option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <div className="flex flex-col justify-end">
                    <span className="rounded bg-signal/15 px-2.5 py-2 text-xs text-signal font-semibold">
                      全站超级管理权限
                    </span>
                  </div>
                )}
              </div>

              {newUserData.role === 'user' && (
                <div className="grid grid-cols-3 gap-2">
                  <label className="flex flex-col gap-1">
                    <span className="text-ink-dim">环境上限</span>
                    <input
                      type="number"
                      value={newUserData.max_profiles}
                      onChange={(e) => setNewUserData({ ...newUserData, max_profiles: parseInt(e.target.value) || 10 })}
                      className="field"
                    />
                  </label>
                  <label className="flex flex-col gap-1">
                    <span className="text-ink-dim">多开并发</span>
                    <input
                      type="number"
                      value={newUserData.max_concurrent}
                      onChange={(e) => setNewUserData({ ...newUserData, max_concurrent: parseInt(e.target.value) || 2 })}
                      className="field"
                    />
                  </label>
                  <label className="flex flex-col gap-1">
                    <span className="text-ink-dim">有效期(天)</span>
                    <input
                      type="number"
                      value={newUserData.duration_days}
                      onChange={(e) => setNewUserData({ ...newUserData, duration_days: parseInt(e.target.value) || 30 })}
                      className="field"
                    />
                  </label>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 border-t border-line pt-3">
              <button onClick={() => setCreateUserOpen(false)} className="btn btn-secondary text-xs">
                取消
              </button>
              <button
                onClick={async () => {
                  if (!newUserData.username || !newUserData.password) {
                    alert('请填写完整账号与密码')
                    return
                  }
                  setActionBusy(true)
                  try {
                    await adminAPI.createUser(newUserData)
                    setCreateUserOpen(false)
                    showToast('用户创建成功')
                    loadData()
                  } catch (err: any) {
                    alert(err.message || String(err))
                  } finally {
                    setActionBusy(false)
                  }
                }}
                disabled={actionBusy}
                className="btn btn-primary text-xs"
              >
                确认创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- EDIT USER MODAL --- */}
      {editUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-md flex-col gap-4 rounded-xl border border-line bg-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <h3 className="text-sm font-semibold text-ink">
                编辑用户: {editUser.username}
              </h3>
              <button onClick={() => setEditUser(null)} className="text-ink-dim hover:text-ink">
                <X size={16} />
              </button>
            </div>

            <div className="flex flex-col gap-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <label className="flex flex-col gap-1">
                  <span className="text-ink-dim">账号类型</span>
                  <select
                    value={editUser.role}
                    onChange={(e) => setEditUser({ ...editUser, role: e.target.value })}
                    className="field"
                  >
                    <option value="user">普通客户 (user)</option>
                    <option value="admin">平台管理员 (admin)</option>
                  </select>
                </label>
                {editUser.role === 'user' ? (
                  <label className="flex flex-col gap-1">
                    <span className="text-ink-dim">客户套餐</span>
                    <select
                      value={editUser.plan_id}
                      onChange={(e) => setEditUser({ ...editUser, plan_id: e.target.value })}
                      className="field"
                    >
                      {plans.map((p) => (
                        <option key={p.id} value={p.id}>{p.name} ({p.id})</option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <div className="flex flex-col justify-end">
                    <span className="rounded bg-signal/15 px-2.5 py-2 text-xs text-signal font-semibold">
                      全站超级管理权限
                    </span>
                  </div>
                )}
              </div>

              {editUser.role === 'user' && (
                <>
                  <div className="grid grid-cols-2 gap-2">
                    <label className="flex flex-col gap-1">
                      <span className="text-ink-dim">环境数量上限</span>
                      <input
                        type="number"
                        value={editUser.max_profiles}
                        onChange={(e) => setEditUser({ ...editUser, max_profiles: parseInt(e.target.value) || 0 })}
                        className="field"
                      />
                    </label>
                    <label className="flex flex-col gap-1">
                      <span className="text-ink-dim">多开并发上限</span>
                      <input
                        type="number"
                        value={editUser.max_concurrent}
                        onChange={(e) => setEditUser({ ...editUser, max_concurrent: parseInt(e.target.value) || 0 })}
                        className="field"
                      />
                    </label>
                  </div>

                  <label className="flex flex-col gap-1">
                    <span className="text-ink-dim">到期时间 (ISO 格式)</span>
                    <input
                      type="text"
                      value={editUser.expires_at || ''}
                      onChange={(e) => setEditUser({ ...editUser, expires_at: e.target.value })}
                      placeholder="YYYY-MM-DDTHH:MM:SS"
                      className="field font-mono"
                    />
                  </label>
                </>
              )}

              <label className="flex flex-col gap-1">
                <span className="text-ink-dim">账号状态</span>
                <select
                  value={editUser.status}
                  onChange={(e) => setEditUser({ ...editUser, status: e.target.value })}
                  className="field"
                >
                  <option value="active">正常 (active)</option>
                  <option value="banned">封禁 (banned)</option>
                </select>
              </label>
            </div>

            <div className="flex justify-end gap-2 border-t border-line pt-3">
              <button onClick={() => setEditUser(null)} className="btn btn-secondary text-xs">
                取消
              </button>
              <button
                onClick={async () => {
                  setActionBusy(true)
                  try {
                    await adminAPI.updateUser(editUser.username, {
                      role: editUser.role,
                      plan_id: editUser.plan_id,
                      max_profiles: editUser.max_profiles,
                      max_concurrent: editUser.max_concurrent,
                      expires_at: editUser.expires_at,
                      status: editUser.status,
                    })
                    setEditUser(null)
                    showToast('用户信息已更新')
                    loadData()
                  } catch (err: any) {
                    alert(err.message || String(err))
                  } finally {
                    setActionBusy(false)
                  }
                }}
                disabled={actionBusy}
                className="btn btn-primary text-xs"
              >
                保存修改
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- RESET PASSWORD MODAL --- */}
      {resetPwdUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-sm flex-col gap-4 rounded-xl border border-line bg-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <h3 className="text-sm font-semibold text-ink">
                重置密码: {resetPwdUser.username}
              </h3>
              <button onClick={() => setResetPwdUser(null)} className="text-ink-dim hover:text-ink">
                <X size={16} />
              </button>
            </div>

            <label className="flex flex-col gap-1 text-xs">
              <span className="text-ink-dim">输入新密码 (不少于 6 位)</span>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="New password"
                className="field"
              />
            </label>

            <div className="flex justify-end gap-2 border-t border-line pt-3">
              <button onClick={() => setResetPwdUser(null)} className="btn btn-secondary text-xs">
                取消
              </button>
              <button
                onClick={async () => {
                  if (newPassword.length < 6) {
                    alert('密码不能少于 6 位')
                    return
                  }
                  setActionBusy(true)
                  try {
                    await adminAPI.resetPassword(resetPwdUser.username, newPassword)
                    setResetPwdUser(null)
                    showToast('密码重置成功')
                  } catch (err: any) {
                    alert(err.message || String(err))
                  } finally {
                    setActionBusy(false)
                  }
                }}
                disabled={actionBusy}
                className="btn btn-primary text-xs"
              >
                确认重置
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- EDIT PLAN MODAL --- */}
      {editPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-md flex-col gap-4 rounded-xl border border-line bg-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <h3 className="text-sm font-semibold text-ink">
                编辑套餐: {editPlan.name}
              </h3>
              <button onClick={() => setEditPlan(null)} className="text-ink-dim hover:text-ink">
                <X size={16} />
              </button>
            </div>

            <div className="flex flex-col gap-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <label className="flex flex-col gap-1">
                  <span className="text-ink-dim">套餐标识 ID</span>
                  <input
                    type="text"
                    value={editPlan.id}
                    onChange={(e) => setEditPlan({ ...editPlan, id: e.target.value })}
                    className="field font-mono"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-ink-dim">套餐名称</span>
                  <input
                    type="text"
                    value={editPlan.name}
                    onChange={(e) => setEditPlan({ ...editPlan, name: e.target.value })}
                    className="field"
                  />
                </label>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <label className="flex flex-col gap-1">
                  <span className="text-ink-dim">价格 (USDT)</span>
                  <input
                    type="number"
                    value={editPlan.price_usdt}
                    onChange={(e) => setEditPlan({ ...editPlan, price_usdt: parseFloat(e.target.value) || 0 })}
                    className="field font-bold text-signal"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-ink-dim">有效期天数</span>
                  <input
                    type="number"
                    value={editPlan.duration_days}
                    onChange={(e) => setEditPlan({ ...editPlan, duration_days: parseInt(e.target.value) || 30 })}
                    className="field"
                  />
                </label>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <label className="flex flex-col gap-1">
                  <span className="text-ink-dim">独立环境上限</span>
                  <input
                    type="number"
                    value={editPlan.max_profiles}
                    onChange={(e) => setEditPlan({ ...editPlan, max_profiles: parseInt(e.target.value) || 10 })}
                    className="field"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-ink-dim">多开并发上限</span>
                  <input
                    type="number"
                    value={editPlan.max_concurrent}
                    onChange={(e) => setEditPlan({ ...editPlan, max_concurrent: parseInt(e.target.value) || 2 })}
                    className="field"
                  />
                </label>
              </div>

              <label className="flex flex-col gap-1">
                <span className="text-ink-dim">套餐描述说明</span>
                <textarea
                  value={editPlan.description || ''}
                  onChange={(e) => setEditPlan({ ...editPlan, description: e.target.value })}
                  rows={2}
                  className="field"
                />
              </label>
            </div>

            <div className="flex justify-end gap-2 border-t border-line pt-3">
              <button onClick={() => setEditPlan(null)} className="btn btn-secondary text-xs">
                取消
              </button>
              <button
                onClick={async () => {
                  setActionBusy(true)
                  try {
                    await adminAPI.savePlan(editPlan)
                    setEditPlan(null)
                    showToast('套餐已保存')
                    loadData()
                  } catch (err: any) {
                    alert(err.message || String(err))
                  } finally {
                    setActionBusy(false)
                  }
                }}
                disabled={actionBusy}
                className="btn btn-primary text-xs"
              >
                保存套餐
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
