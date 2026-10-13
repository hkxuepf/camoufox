'use client'

import { useEffect, useState } from 'react'
import { Check, Minus, Settings as SettingsIcon, TriangleAlert, Globe } from 'lucide-react'

import { BrowserSetup } from '@/components/browser-setup'
import { ChromiumSetup } from '@/components/chromium-setup'
import { BackupSettings, UpdateSettings } from '@/components/recovery-settings'
import { EmptyState } from '@/components/empty-state'
import { useToast } from '@/components/toast'
import { useI18n, type Language } from '@/lib/i18n'
import {
  getApiKey,
  setApiKey,
  systemAPI,
  type SystemConfig,
  type SystemStatus,
} from '@/lib/api'

function formatUptime(seconds: number, isZh: boolean): string {
  if (seconds < 60) return `${seconds}${isZh ? '秒' : 's'}`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}${isZh ? '分钟' : 'm'}`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}${isZh ? '小时' : 'h'} ${Math.floor((seconds % 3600) / 60)}${isZh ? '分钟' : 'm'}`
  return `${Math.floor(seconds / 86400)}${isZh ? '天' : 'd'} ${Math.floor((seconds % 86400) / 3600)}${isZh ? '小时' : 'h'}`
}

export default function SettingsPage() {
  const { t, lang, setLang, isZh } = useI18n()
  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [key, setKey] = useState('')
  const toast = useToast()

  useEffect(() => {
    // The key lives in localStorage, which does not exist when this page is
    // prerendered into the static export, so it can only be read after mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setKey(getApiKey())
    async function load() {
      try {
        setConfig(await systemAPI.config())
        setStatus(await systemAPI.status().catch(() => null))
      } catch (err) {
        setError(String(err instanceof Error ? err.message : err))
      }
    }
    load()
  }, [])

  function saveKey(event: React.FormEvent) {
    event.preventDefault()
    setApiKey(key.trim())
    toast(
      'ok',
      key.trim() ? (isZh ? 'API 密钥已保存' : 'API key saved') : (isZh ? 'API 密钥已清除' : 'API key cleared'),
      isZh ? '仅保存在当前浏览器本地，并在请求时作为 X-API-Key 头发送。' : 'Stored in this browser only, and sent as X-API-Key.',
    )
  }

  return (
    <>
      <header className="sticky top-0 z-20 flex h-[52px] items-center gap-3 border-b border-line bg-canvas/85 px-5 backdrop-blur">
        <h1 className="text-[14px] font-semibold">{t('nav.settings', 'Settings')}</h1>
      </header>

      {error ? (
        <EmptyState icon={<SettingsIcon size={18} />} title={isZh ? '无法连接到后端服务' : 'Cannot reach the API'} body={error} />
      ) : !config ? (
        <p className="px-5 py-8 text-ink-faint">{isZh ? '正在加载…' : 'Loading…'}</p>
      ) : (
        <div className="mx-auto flex max-w-[760px] flex-col gap-6 px-5 py-6">
          <BrowserSetup />
          <ChromiumSetup />
          <UpdateSettings />
          <BackupSettings />

          {/* 语言偏好设置 */}
          <Group
            title={isZh ? '语言偏好 / Language' : 'Language / 语言'}
            note={isZh ? '选择管理控制台的显示语言。' : 'Choose display language for the control panel.'}
          >
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-ink-dim flex items-center gap-2">
                <Globe size={15} />
                {isZh ? '界面语言' : 'Display Language'}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className={lang === 'zh' ? 'btn btn-default border-signal text-ink font-semibold' : 'btn btn-ghost text-ink-dim'}
                  onClick={() => setLang('zh')}
                >
                  简体中文
                </button>
                <button
                  type="button"
                  className={lang === 'en' ? 'btn btn-default border-signal text-ink font-semibold' : 'btn btn-ghost text-ink-dim'}
                  onClick={() => setLang('en')}
                >
                  English
                </button>
              </div>
            </div>
          </Group>

          {/* Security first: these two decide whether this instance is safe to expose. */}
          <Group
            title={isZh ? '安全与访问控制' : 'Security'}
            note={isZh ? '通过服务器环境变量配置；需重启服务生效。' : 'Configured with environment variables; restart to apply changes.'}
          >
            <Toggle
              on={config.encryption_enabled}
              label={isZh ? '代理密码加密' : 'Proxy password encryption'}
              onText={isZh ? '密码已通过 CPM_SECRET_KEY 进行静态加密存储。' : 'Passwords are encrypted at rest with CPM_SECRET_KEY.'}
              offText={isZh ? '密码以明文存储。配置 CPM_SECRET_KEY 环境变量即可启用加密。' : 'Passwords are stored as plain text. Set CPM_SECRET_KEY to encrypt them.'}
              warnWhenOff
            />
            <Toggle
              on={config.user_auth_enabled}
              label={isZh ? '用户账户管理' : 'User accounts'}
              onText={isZh ? '已启用登录鉴权。可使用命令管理：camoufox-pm user' : 'Login is required. Manage accounts with: camoufox-pm user'}
              offText={isZh ? '未启用多用户。可通过命令创建：camoufox-pm user add <name>' : 'No user accounts. Create one with: camoufox-pm user add <name>'}
              warnWhenOff={config.host !== '127.0.0.1' && !config.api_key_set}
            />
            <Toggle
              on={config.api_key_set}
              label={isZh ? 'API 密钥保护' : 'API key'}
              onText={isZh ? '外部请求必须携带匹配的 X-API-Key 请求头。' : 'Requests must send a matching X-API-Key header.'}
              offText={
                config.user_auth_enabled
                  ? (isZh ? '未设置 API 密钥。程序客户端无法调用；人类用户通过账号密码登录。' : 'No API key is set. Machine clients have no way in; humans log in.')
                  : (isZh ? '未设置 API 密钥。任何能访问此端口的人均可直接调用 API。' : 'No API key is set. Anyone who can reach this port can use the API.')
              }
              warnWhenOff={config.host !== '127.0.0.1' && !config.user_auth_enabled}
            />
            {config.api_key_set && (
              <form onSubmit={saveKey} className="flex items-start gap-4 px-4 py-2.5">
                <span className="w-[150px] shrink-0 text-ink-dim">{isZh ? '当前浏览器密钥' : "This browser's key"}</span>
                <span className="flex flex-1 gap-2">
                  <input
                    type="password"
                    className="field font-mono"
                    value={key}
                    onChange={(event) => setKey(event.target.value)}
                    placeholder={isZh ? '粘贴 CPM_API_KEY 以便在当前界面继续使用' : 'Paste CPM_API_KEY to keep using this UI'}
                    aria-label="API key for this browser"
                    autoComplete="off"
                  />
                  <button type="submit" className="btn btn-default shrink-0">
                    {isZh ? '保存' : 'Save'}
                  </button>
                </span>
              </form>
            )}
            <Row label={isZh ? '服务监听地址' : 'Bound to'}>
              <span className="font-mono">
                {config.host}:{config.port}
              </span>
              {config.host !== '127.0.0.1' && (
                <span className="ml-2 text-danger">{isZh ? '可通过外网/局域网访问' : 'reachable beyond this machine'}</span>
              )}
            </Row>
          </Group>

          <Group title={isZh ? '实例信息' : 'Instance'}>
            <Row label={isZh ? '版本号' : 'Version'}>
              <span className="font-mono">{config.version}</span>
            </Row>
            <Row label={isZh ? '运行时间' : 'Uptime'}>
              <span className="font-mono">{formatUptime(config.uptime_seconds, isZh)}</span>
            </Row>
            <Row label={isZh ? '数据库文件' : 'Database'}>
              <span className="break-all font-mono text-ink-dim">{config.database_path}</span>
            </Row>
          </Group>

          {status && (
            <Group title={isZh ? '系统用量' : 'Usage'}>
              <Row label={isZh ? '环境总数' : 'Profiles'}>
                <span className="font-mono">{status.total_profiles}</span>
              </Row>
              <Row label={isZh ? '分组总数' : 'Groups'}>
                <span className="font-mono">{status.total_groups}</span>
              </Row>
              <Row label={isZh ? '运行中浏览器' : 'Running browsers'}>
                <span className="font-mono">{status.running_browsers}</span>
              </Row>
              <Row label={isZh ? '内存 / 磁盘使用' : 'Memory / disk'}>
                <span className="font-mono text-ink-dim">
                  {Math.round(status.memory_usage)}% / {Math.round(status.disk_usage)}%
                </span>
              </Row>
            </Group>
          )}
        </div>
      )}
    </>
  )
}

function Group({
  title,
  note,
  children,
}: {
  title: string
  note?: string
  children: React.ReactNode
}) {
  return (
    <section>
      <h2 className="mb-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">
        {title}
      </h2>
      {note && <p className="mb-2 text-ink-faint">{note}</p>}
      <div className="panel divide-y divide-line">{children}</div>
    </section>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-4 px-4 py-2.5">
      <span className="w-[150px] shrink-0 text-ink-dim">{label}</span>
      <span className="flex-1">{children}</span>
    </div>
  )
}

function Toggle({
  on,
  label,
  onText,
  offText,
  warnWhenOff = false,
}: {
  on: boolean
  label: string
  onText: string
  offText: string
  warnWhenOff?: boolean
}) {
  const warn = !on && warnWhenOff
  return (
    <div className="flex gap-4 px-4 py-2.5">
      <span className="w-[150px] shrink-0 text-ink-dim">{label}</span>
      <span className="flex flex-1 items-start gap-2">
        {on ? (
          <Check size={14} className="mt-0.5 shrink-0 text-ok" />
        ) : warn ? (
          <TriangleAlert size={14} className="mt-0.5 shrink-0 text-danger" />
        ) : (
          <Minus size={14} className="mt-0.5 shrink-0 text-ink-faint" />
        )}
        <span className={warn ? 'text-danger' : on ? '' : 'text-ink-dim'}>
          {on ? onText : offText}
        </span>
      </span>
    </div>
  )
}
