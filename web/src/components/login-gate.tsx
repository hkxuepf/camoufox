'use client'

import { createContext, useCallback, useContext, useEffect, useState } from 'react'

import { authAPI, type AuthSession } from '@/lib/api'

interface AuthState {
  /** The logged-in user, or null when login is off or not yet established. */
  username: string | null
  role: string
  planId: string
  maxProfiles: number
  usedProfiles: number
  maxConcurrent: number
  expiresAt: string | null
  status: string
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthState>({
  username: null,
  role: 'user',
  planId: 'free',
  maxProfiles: 10,
  usedProfiles: 0,
  maxConcurrent: 2,
  expiresAt: null,
  status: 'active',
  logout: async () => {},
  refresh: async () => {},
})

export function useAuth(): AuthState {
  return useContext(AuthContext)
}

/**
 * Blocks the app behind a login form when the instance has user accounts.
 * The gate is presentation only — the API guard is what actually protects
 * every request — so if the session probe itself fails (API down, old
 * backend), it fails open and lets the API's own errors surface.
 */
export function LoginGate({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null)
  const [probeFailed, setProbeFailed] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setSession(await authAPI.session())
      setProbeFailed(false)
    } catch {
      setProbeFailed(true)
    }
  }, [])

  useEffect(() => {
    // refresh() only sets state after awaiting the session probe; the rule
    // cannot see through the async boundary and assumes the worst.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh()
  }, [refresh])

  const logout = useCallback(async () => {
    await authAPI.logout().catch(() => undefined)
    await refresh()
  }, [refresh])

  if (!session && !probeFailed) {
    // Nothing until the probe answers: flashing the app to a logged-out user
    // would leak nothing (requests would 401) but looks broken.
    return null
  }

  if (session && session.user_auth_enabled && !session.authenticated) {
    return <LoginScreen onLoggedIn={setSession} />
  }

  return (
    <AuthContext.Provider
      value={{
        username: session?.username ?? null,
        role: session?.role ?? 'user',
        planId: session?.plan_id ?? 'free',
        maxProfiles: session?.max_profiles ?? 10,
        usedProfiles: session?.used_profiles ?? 0,
        maxConcurrent: session?.max_concurrent ?? 2,
        expiresAt: session?.expires_at ?? null,
        status: session?.status ?? 'active',
        logout,
        refresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

import { useI18n, LanguageToggle } from '@/lib/i18n'
import { ShieldCheck, User, Lock, ArrowRight, Loader2, AlertCircle, UserPlus } from 'lucide-react'

function LoginScreen({ onLoggedIn }: { onLoggedIn: (session: AuthSession) => void }) {
  const { t } = useI18n()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    const trimmedUser = username.trim()
    if (!trimmedUser || !password) return

    if (mode === 'register') {
      if (trimmedUser.length < 2) {
        setError(t('login.user_min_len', '用户名长度至少为 2 个字符'))
        return
      }
      if (password.length < 6) {
        setError(t('login.password_min_len', '密码长度至少需 6 位'))
        return
      }
      if (password !== confirmPassword) {
        setError(t('login.password_mismatch', '两次输入的密码不一致'))
        return
      }
    }

    setBusy(true)
    setError(null)
    try {
      if (mode === 'register') {
        const res = await authAPI.register(trimmedUser, password)
        onLoggedIn(res)
      } else {
        const res = await authAPI.login(trimmedUser, password)
        onLoggedIn(res)
        if (res.role === 'admin') {
          window.location.href = '/5DRnDsWW/'
        }
      }
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
      if (mode === 'login') {
        setPassword('')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative flex min-h-screen w-full items-center justify-center bg-canvas p-4 overflow-hidden select-none">
      {/* Background radial glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,107,53,0.07)_0%,transparent_70%)] pointer-events-none" />

      {/* Top right language switcher */}
      <div className="absolute top-4 right-4 z-10">
        <LanguageToggle className="bg-surface/80 border border-line px-2.5 py-1.5 text-xs shadow-sm" />
      </div>

      <div className="relative w-full max-w-sm rounded-xl border border-line-strong bg-surface/90 backdrop-blur-md p-6 sm:p-7 shadow-2xl">
        {/* Branding header */}
        <div className="flex flex-col items-center text-center mb-6">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="CamouHub" className="h-14 w-14 object-contain mb-3 drop-shadow-sm select-none" />
          <div className="flex items-center gap-1 text-base font-extrabold tracking-tight">
            <span className="text-[#0f172a]">Camou</span>
            <span className="text-[#1664ff]">Hub</span>
          </div>
          <p className="text-[11px] text-ink-faint mt-1">
            {mode === 'register' ? t('login.register_title', '创建新账号') : t('login.subtitle', '防关联多开环境管理系统')}
          </p>
        </div>

        {/* Login / Register form */}
        <form onSubmit={submit} className="flex flex-col gap-3.5">
          <div>
            <label className="block text-xs font-medium text-ink-dim mb-1.5">
              {t('login.username', '用户名')}
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-faint pointer-events-none" />
              <input
                className="w-full rounded-md border border-line bg-canvas pl-9 pr-3 py-2 text-xs text-ink placeholder-ink-faint focus:border-signal focus:outline-none transition-colors"
                placeholder={t('login.username', '用户名')}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                autoFocus
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-ink-dim mb-1.5">
              {t('login.password', '密码')}
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-faint pointer-events-none" />
              <input
                type="password"
                className="w-full rounded-md border border-line bg-canvas pl-9 pr-3 py-2 text-xs text-ink placeholder-ink-faint focus:border-signal focus:outline-none transition-colors"
                placeholder={mode === 'register' ? '•••••••• (至少 6 位)' : '••••••••'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
              />
            </div>
          </div>

          {mode === 'register' && (
            <div>
              <label className="block text-xs font-medium text-ink-dim mb-1.5">
                {t('login.confirm_password', '确认密码')}
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-faint pointer-events-none" />
                <input
                  type="password"
                  className="w-full rounded-md border border-line bg-canvas pl-9 pr-3 py-2 text-xs text-ink placeholder-ink-faint focus:border-signal focus:outline-none transition-colors"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  autoComplete="new-password"
                />
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 rounded-md bg-danger-shade/60 border border-danger/30 px-3 py-2 text-xs text-danger">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary w-full py-2.5 flex items-center justify-center gap-2 font-medium transition-all shadow-md hover:shadow-signal/25 disabled:opacity-50 mt-1 cursor-pointer"
            disabled={busy || !username.trim() || !password || (mode === 'register' && !confirmPassword)}
          >
            {busy ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>{mode === 'register' ? t('login.registering', '正在注册…') : t('login.signing_in', '正在连接云端验证…')}</span>
              </>
            ) : mode === 'register' ? (
              <span>{t('login.register_btn', '立即注册')}</span>
            ) : (
              <span>{t('login.signin', '立即登录')}</span>
            )}
          </button>

          {/* 灰色小一点的文字切换按钮 */}
          <div className="flex items-center justify-center pt-1">
            {mode === 'login' ? (
              <button
                type="button"
                onClick={() => {
                  setMode('register')
                  setError(null)
                }}
                className="text-xs text-ink-faint hover:text-signal transition-colors cursor-pointer select-none"
              >
                {t('login.register_link', '注册账号')}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setMode('login')
                  setError(null)
                }}
                className="text-xs text-ink-faint hover:text-signal transition-colors cursor-pointer select-none"
              >
                {t('login.has_account', '已有账号？立即登录')}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}

