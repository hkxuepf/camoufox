'use client'

import { useEffect, useState } from 'react'
import { CheckCircle2, Globe2, Loader2, Network, XCircle } from 'lucide-react'
import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { profilesAPI, proxiesAPI, type Profile, type ProxyCheck, type ProxyItem } from '@/lib/api'
import { getLanguagesForCountry, getTimezoneForCountry } from '@/lib/country-languages'

interface QuickProxyModalProps {
  open: boolean
  onClose: () => void
  profile: Profile | null
  onSaved?: () => void
}

export function QuickProxyModal({ open, onClose, profile, onSaved }: QuickProxyModalProps) {
  const [proxyType, setProxyType] = useState('none')
  const [server, setServer] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<ProxyCheck | null>(null)
  const [saving, setSaving] = useState(false)
  const [poolProxies, setPoolProxies] = useState<ProxyItem[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState('')
  const toast = useToast()

  useEffect(() => {
    if (open) {
      proxiesAPI.list().then((res) => setPoolProxies(res.proxies || [])).catch(() => {})
    }
  }, [open])

  useEffect(() => {
    if (open && profile) {
      setTestResult(null)
      setSelectedPoolId('')
      if (profile.proxy_config && profile.proxy_config.server) {
        setProxyType(profile.proxy_config.type || 'socks5')
        setServer(profile.proxy_config.server || '')
        setUsername(profile.proxy_config.username || '')
        setPassword(profile.proxy_config.password || '')
      } else {
        setProxyType('none')
        setServer('')
        setUsername('')
        setPassword('')
      }
    }
  }, [open, profile])

  const handleSelectPoolProxy = (poolId: string) => {
    setSelectedPoolId(poolId)
    if (!poolId) return
    const p = poolProxies.find((item) => item.id === poolId)
    if (p) {
      setProxyType(p.type || 'socks5')
      setServer(p.port ? `${p.server}:${p.port}` : p.server)
      setUsername(p.username || '')
      setPassword(p.password || '')
      toast('ok', `已填入代理池节点: ${p.name || p.server}`)
    }
  }

  const handleTest = async () => {
    if (proxyType === 'none' || !server.trim()) {
      toast('error', '请输入代理服务器地址')
      return
    }
    setTesting(true)
    setTestResult(null)
    try {
      const res = await profilesAPI.checkUnsavedProxy({
        proxy_config: {
          type: proxyType,
          server: server.trim(),
          username: username.trim() || null,
          password: password.trim() || null,
        },
        browser_settings: (profile?.browser_settings as unknown as Record<string, unknown>) || {},
      })
      setTestResult(res)
      if (res.reachable) {
        toast('ok', `代理连接成功！出口 IP: ${res.location?.ip || '已连接'}`)
      } else {
        toast('error', `代理连接失败: ${res.error || '超时'}`)
      }
    } catch (err) {
      toast('error', '测试失败', String(err))
    } finally {
      setTesting(false)
    }
  }

  const [syncGeo, setSyncGeo] = useState(true)

  const handleSave = async () => {
    if (!profile) return
    setSaving(true)
    try {
      const proxy_config =
        proxyType === 'none' || !server.trim()
          ? null
          : {
              type: proxyType,
              server: server.trim(),
              username: username.trim() || null,
              password: password.trim() || null,
            }
      const updatePayload: Record<string, unknown> = {
        proxy_config,
        row_version: profile.row_version,
      }
      if (syncGeo && testResult?.location) {
        const bs = (profile.browser_settings as unknown as Record<string, unknown>) || {}
        const langs = (testResult.location.languages && testResult.location.languages.length)
          ? testResult.location.languages
          : getLanguagesForCountry(testResult.location.country)
        const tz = testResult.location.timezone || getTimezoneForCountry(testResult.location.country)
        updatePayload.browser_settings = {
          ...bs,
          timezone: tz,
          languages: langs,
        }
      }
      await profilesAPI.updateProfile(profile.id, updatePayload)
      toast('ok', '代理配置已更新', syncGeo && testResult?.location ? '时区与语言已自动适配' : undefined)
      if (onSaved) onSaved()
      onClose()
    } catch (err) {
      toast('error', '保存失败', String(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={`修改代理 — ${profile?.name ?? ''}`}>
      <div className="flex flex-col gap-4 text-xs">
        <div className="flex items-center gap-2 rounded-lg bg-[#f8fafc] border border-line p-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-signal/10 text-signal">
            <Globe2 size={18} />
          </div>
          <div>
            <div className="font-semibold text-ink">独立代理网络配置</div>
            <div className="text-[11px] text-ink-dim">
              为当前环境指定专有 IP 与网络出口，隔离真实设备网络指纹
            </div>
          </div>
        </div>

        {poolProxies.length > 0 && (
          <div className="rounded-lg bg-[#eff6ff] border border-[#bfdbfe] p-2.5">
            <label className="text-[11px] font-bold text-[#1e40af] block mb-1">
              ⚡ 从代理池快速选用节点
            </label>
            <select
              value={selectedPoolId}
              onChange={(e) => handleSelectPoolProxy(e.target.value)}
              className="w-full bg-white text-xs border border-[#93c5fd] rounded-md px-2.5 py-1.5 text-[#1e293b] focus:outline-none focus:ring-1 focus:ring-[#1664ff]"
            >
              <option value="">-- 选择代理池已有节点快速填充 --</option>
              {poolProxies.map((p) => (
                <option key={p.id} value={p.id}>
                  [{p.type.toUpperCase()}] {p.name || p.server}:{p.port || 80}{p.country ? ` (${p.country})` : ''}{p.status === 'active' ? ` [${p.latency_ms || 0}ms]` : ''}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="flex flex-col gap-3">
          <div>
            <label className="field-label">代理类型</label>
            <select
              value={proxyType}
              onChange={(e) => setProxyType(e.target.value)}
              className="field"
            >
              <option value="none">不使用代理 (直连网络)</option>
              <option value="socks5">SOCKS5 代理</option>
              <option value="http">HTTP 代理</option>
              <option value="https">HTTPS 代理</option>
              <option value="socks4">SOCKS4 代理</option>
            </select>
          </div>

          {proxyType !== 'none' && (
            <>
              <div>
                <label className="field-label">代理主机与端口 (Host:Port)</label>
                <input
                  type="text"
                  value={server}
                  onChange={(e) => setServer(e.target.value)}
                  placeholder="例如: 127.0.0.1:7890 或 proxy.example.com:8080"
                  className="field font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="field-label">认证用户名 (可选)</label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Username"
                    className="field font-mono"
                  />
                </div>
                <div>
                  <label className="field-label">认证密码 (可选)</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Password"
                    className="field font-mono"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between rounded-md bg-[#f8fafc] border border-line p-2.5">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleTest}
                    disabled={testing || !server.trim()}
                    className="btn btn-default text-xs h-7 px-3"
                  >
                    {testing ? <Loader2 size={13} className="animate-spin" /> : <Network size={13} />}
                    <span>{testing ? '检测中...' : '一键测试代理'}</span>
                  </button>
                  {testResult && (
                    <div className="flex items-center gap-1.5 text-[11px]">
                      {testResult.reachable ? (
                        <>
                          <CheckCircle2 size={14} className="text-ok" />
                          <span className="font-semibold text-ok">
                            可用 ({testResult.latency_ms ?? 0}ms)
                          </span>
                          <span className="font-mono text-ink-dim">
                            {testResult.location?.ip} [{testResult.location?.country || 'Global'}]
                          </span>
                        </>
                      ) : (
                        <>
                          <XCircle size={14} className="text-danger" />
                          <span className="font-semibold text-danger">不可用</span>
                          <span className="text-ink-faint truncate max-w-[200px]">
                            {testResult.error || '连接超时'}
                          </span>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <label className="flex cursor-pointer items-center gap-2 rounded-md bg-[#eff6ff] border border-[#bfdbfe] p-2 text-[11px] text-[#1e40af]">
                <input
                  type="checkbox"
                  checked={syncGeo}
                  onChange={(e) => setSyncGeo(e.target.checked)}
                  className="rounded border-line text-signal focus:ring-signal"
                />
                <span>自动将环境时区与语言同步适配至该代理 IP 所在地区 (推荐)</span>
              </label>
            </>
          )}
        </div>

        <div className="flex items-center justify-end gap-2.5 border-t border-line pt-3">
          <button type="button" onClick={onClose} className="btn btn-default px-4">
            取消
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="btn btn-primary px-5 font-semibold"
          >
            {saving ? '保存中...' : '确定'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
