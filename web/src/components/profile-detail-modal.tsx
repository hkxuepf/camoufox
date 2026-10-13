'use client'

import { Modal } from '@/components/modal'
import { formatLastUsed, OS_LABELS, type Profile } from '@/lib/api'
import {
  Activity,
  CheckCircle2,
  Clock,
  Cpu,
  Globe,
  HardDrive,
  Info,
  Key,
  Layers,
  Monitor,
  Shield,
  Smartphone,
  User,
  Volume2,
} from 'lucide-react'

interface ProfileDetailModalProps {
  open: boolean
  profile: Profile | null
  onClose: () => void
}

export function ProfileDetailModal({ open, profile, onClose }: ProfileDetailModalProps) {
  if (!profile) return null

  const s = profile.browser_settings || {}
  const proxy = profile.proxy_config

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`环境详情 — ${profile.name}`}
      width={680}
      footer={
        <button className="btn btn-default" onClick={onClose}>
          关闭
        </button>
      }
    >
      <div className="space-y-5 text-xs text-[#334155]">
        {/* Basic Header Badge Card */}
        <div className="flex items-center justify-between rounded-lg border border-[#eaedf1] bg-[#f8fafc] p-3.5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#1664ff]/10 text-[#1664ff]">
              <Monitor size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-[#0f172a]">{profile.name}</span>
                <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[11px] font-medium text-blue-600 border border-blue-200">
                  {s.browser_engine === 'chromium' ? 'Chromium 154' : 'Gecko Firefox'}
                </span>
                {profile.is_favorite && (
                  <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[11px] font-medium text-amber-600 border border-amber-200">
                    ★ 常用
                  </span>
                )}
              </div>
              <div className="mt-0.5 flex items-center gap-2 font-mono text-[11px] text-[#64748b]">
                <span>ID: {profile.id}</span>
                <span>·</span>
                <span>最后使用: {formatLastUsed(profile.last_used)}</span>
              </div>
            </div>
          </div>
          <div className="text-right">
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
                profile.status === 'active'
                  ? 'bg-emerald-50 text-emerald-600 border border-emerald-200'
                  : 'bg-slate-100 text-slate-600 border border-slate-200'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  profile.status === 'active' ? 'bg-emerald-500' : 'bg-slate-400'
                }`}
              />
              {profile.status === 'active' ? '正常' : profile.status}
            </span>
          </div>
        </div>

        {/* Section 1: 硬件与操作系统指纹 */}
        <div>
          <div className="mb-2 flex items-center gap-1.5 font-medium text-[#0f172a]">
            <Cpu size={14} className="text-[#1664ff]" />
            <span>硬件与系统指纹配置</span>
          </div>
          <div className="grid grid-cols-2 gap-2 rounded-lg border border-[#eaedf1] bg-white p-3 shadow-sm">
            <div className="flex justify-between py-1 border-b border-[#f1f5f9]">
              <span className="text-[#64748b]">操作系统 (OS)</span>
              <span className="font-medium text-[#0f172a]">{OS_LABELS[s.os ?? ''] ?? s.os ?? 'macOS'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#f1f5f9]">
              <span className="text-[#64748b]">CPU 核心数 (Concurrency)</span>
              <span className="font-mono text-[#0f172a]">{s.hardware_concurrency ?? '8'} Cores</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#f1f5f9]">
              <span className="text-[#64748b]">设备内存 (Device Memory)</span>
              <span className="font-mono text-[#0f172a]">{s.device_memory ?? '8'} GB</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#f1f5f9]">
              <span className="text-[#64748b]">屏幕分辨率</span>
              <span className="font-mono text-[#0f172a]">
                {s.window_width || '1920'} × {s.window_height || '1080'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#f1f5f9]">
              <span className="text-[#64748b]">WebGL 厂商 (Vendor)</span>
              <span className="truncate max-w-[180px] font-mono text-[#0f172a]" title={s.webgl_vendor || 'Apple'}>
                {s.webgl_vendor || 'Apple'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#f1f5f9]">
              <span className="text-[#64748b]">WebGL 渲染器 (Renderer)</span>
              <span
                className="truncate max-w-[180px] font-mono text-[#0f172a]"
                title={s.webgl_renderer || 'Apple M1 / ANGLE'}
              >
                {s.webgl_renderer || 'Apple M1 / ANGLE'}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-[#64748b]">音频指纹 (AudioContext)</span>
              <span className="text-emerald-600 font-medium">噪声混淆已启用 (Protected)</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-[#64748b]">Canvas 保护</span>
              <span className="text-emerald-600 font-medium">抗指纹混淆保护中</span>
            </div>
          </div>
        </div>

        {/* Section 2: 网络与代理配置 */}
        <div>
          <div className="mb-2 flex items-center gap-1.5 font-medium text-[#0f172a]">
            <Globe size={14} className="text-[#1664ff]" />
            <span>网络与代理信息</span>
          </div>
          <div className="rounded-lg border border-[#eaedf1] bg-white p-3 shadow-sm space-y-2">
            <div className="flex justify-between items-center py-1 border-b border-[#f1f5f9]">
              <span className="text-[#64748b]">代理协议与主机</span>
              {proxy ? (
                <span className="font-mono text-[#0f172a] font-medium">
                  {(proxy.type || 'PROXY').toUpperCase()}://{proxy.server}
                </span>
              ) : (
                <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-600">直连模式 (不使用代理)</span>
              )}
            </div>
            {profile.proxy_check && (
              <div className="flex justify-between items-center py-1 border-b border-[#f1f5f9]">
                <span className="text-[#64748b]">出口 IP & 地区</span>
                <span className="font-mono text-[#0f172a]">
                  {profile.proxy_check.ip || '未知'} ({profile.proxy_check.country || '本地'})
                </span>
              </div>
            )}
            <div className="flex justify-between items-center py-1">
              <span className="text-[#64748b]">WebRTC 策略</span>
              <span className="text-emerald-600 font-medium">
                {s.webrtc_mode || '跟随代理 IP 替换 (防泄露)'}
              </span>
            </div>
          </div>
        </div>

        {/* Section 3: 关联账号与商业数据 */}
        <div>
          <div className="mb-2 flex items-center gap-1.5 font-medium text-[#0f172a]">
            <Key size={14} className="text-[#1664ff]" />
            <span>关联账号与 Cookie 数据</span>
          </div>
          <div className="grid grid-cols-2 gap-2 rounded-lg border border-[#eaedf1] bg-white p-3 shadow-sm">
            <div className="flex justify-between py-1 border-b border-[#f1f5f9]">
              <span className="text-[#64748b]">绑定的业务账号</span>
              <span className="font-medium text-[#0f172a]">{profile.account || '未绑定'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#f1f5f9]">
              <span className="text-[#64748b]">Cookie 缓存状态</span>
              <span className="text-[#0f172a]">
                {profile.cookies ? (
                  <span className="text-blue-600 font-medium">已注入 Cookie 数据</span>
                ) : (
                  <span className="text-slate-400">无自定义 Cookie</span>
                )}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-[#64748b]">环境标签</span>
              <span className="text-[#0f172a]">
                {profile.tags && profile.tags.length > 0 ? profile.tags.join(', ') : '无标签'}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-[#64748b]">存储与隔离</span>
              <span className="text-emerald-600 font-medium">独立 Profile 物理隔离</span>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  )
}
