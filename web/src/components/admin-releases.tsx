'use client'

import { useEffect, useState } from 'react'
import {
  AlertCircle,
  ArrowUpRight,
  Check,
  CheckCircle2,
  Copy,
  Download,
  Edit2,
  ExternalLink,
  Layers,
  Monitor,
  Package,
  Plus,
  RefreshCw,
  Sparkles,
  Terminal,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react'
import {
  adminAPI,
  type ClientReleaseItem,
  type KernelReleaseItem,
} from '@/lib/api'

interface AdminReleasesProps {
  language: 'zh' | 'en'
}

export function AdminReleasesView({ language }: AdminReleasesProps) {
  const isZh = language === 'zh'
  const [activeSubTab, setActiveSubTab] = useState<'client' | 'kernels'>('client')
  const [loading, setLoading] = useState(false)
  const [copiedText, setCopiedText] = useState<string | null>(null)

  // Client releases state
  const [clientReleases, setClientReleases] = useState<ClientReleaseItem[]>([])
  const [showClientModal, setShowClientModal] = useState(false)
  const [clientForm, setClientForm] = useState({
    version: '',
    title: '',
    changelog: '',
    min_version: '1.0.0',
    is_force_update: false,
    mac_arm64_url: '',
    mac_x64_url: '',
    win_x64_url: '',
  })

  // Kernel releases state
  const [kernelReleases, setKernelReleases] = useState<KernelReleaseItem[]>([])
  const [showKernelModal, setShowKernelModal] = useState(false)
  const [kernelFilter, setKernelFilter] = useState<'all' | 'chromium' | 'camoufox'>('all')
  const [kernelForm, setKernelForm] = useState({
    engine: 'chromium' as 'chromium' | 'camoufox',
    version: '',
    display_name: '',
    changelog: '',
    is_recommended: false,
    mac_arm64_url: '',
    mac_x64_url: '',
    win_x64_url: '',
  })

  const loadData = async () => {
    setLoading(true)
    try {
      const [cList, kList] = await Promise.all([
        adminAPI.getClientReleases(),
        adminAPI.getKernelReleases(),
      ])
      setClientReleases(cList || [])
      setKernelReleases(kList || [])
    } catch (err) {
      console.error('Failed to load release data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    setCopiedText(label)
    setTimeout(() => setCopiedText(null), 2000)
  }

  // Handle client release submit
  const handleSaveClientRelease = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!clientForm.version) return
    try {
      await adminAPI.createClientRelease({
        version: clientForm.version.trim(),
        title: clientForm.title.trim() || `CamouHub ${clientForm.version}`,
        changelog: clientForm.changelog.trim(),
        min_version: clientForm.min_version.trim() || '1.0.0',
        is_force_update: clientForm.is_force_update,
        is_active: true,
        mac_arm64_url: clientForm.mac_arm64_url.trim() || null,
        mac_x64_url: clientForm.mac_x64_url.trim() || null,
        win_x64_url: clientForm.win_x64_url.trim() || null,
      })
      setShowClientModal(false)
      setClientForm({
        version: '',
        title: '',
        changelog: '',
        min_version: '1.0.0',
        is_force_update: false,
        mac_arm64_url: '',
        mac_x64_url: '',
        win_x64_url: '',
      })
      loadData()
    } catch (err) {
      alert(isZh ? '发布客户端版本失败: ' + err : 'Failed to publish client release: ' + err)
    }
  }

  // Handle kernel release submit
  const handleSaveKernelRelease = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!kernelForm.version) return
    try {
      await adminAPI.createKernelRelease({
        engine: kernelForm.engine,
        version: kernelForm.version.trim(),
        display_name: kernelForm.display_name.trim() || `${kernelForm.engine === 'chromium' ? 'Chrome' : 'Camoufox'} ${kernelForm.version}`,
        changelog: kernelForm.changelog.trim(),
        is_recommended: kernelForm.is_recommended,
        is_active: true,
        mac_arm64_url: kernelForm.mac_arm64_url.trim() || null,
        mac_x64_url: kernelForm.mac_x64_url.trim() || null,
        win_x64_url: kernelForm.win_x64_url.trim() || null,
      })
      setShowKernelModal(false)
      setKernelForm({
        engine: 'chromium',
        version: '',
        display_name: '',
        changelog: '',
        is_recommended: false,
        mac_arm64_url: '',
        mac_x64_url: '',
        win_x64_url: '',
      })
      loadData()
    } catch (err) {
      alert(isZh ? '发布内核版本失败: ' + err : 'Failed to publish kernel release: ' + err)
    }
  }

  const handleDeleteClientRelease = async (id: string, ver: string) => {
    if (!confirm(isZh ? `确定要删除客户端版本 ${ver} 吗？` : `Delete client release ${ver}?`)) return
    try {
      await adminAPI.deleteClientRelease(id)
      loadData()
    } catch (err) {
      alert('Delete failed: ' + err)
    }
  }

  const handleDeleteKernelRelease = async (id: string, ver: string) => {
    if (!confirm(isZh ? `确定要删除内核版本 ${ver} 吗？` : `Delete kernel release ${ver}?`)) return
    try {
      await adminAPI.deleteKernelRelease(id)
      loadData()
    } catch (err) {
      alert('Delete failed: ' + err)
    }
  }

  const filteredKernels = kernelReleases.filter((k) => {
    if (kernelFilter === 'all') return true
    return k.engine === kernelFilter
  })

  return (
    <div className="space-y-6">
      {/* 顶部中台导语与子 Tab 切换 */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-ink">
              {isZh ? '版本发布与内核中台' : 'Release & Kernel Center'}
            </h2>
            <span className="rounded bg-signal/10 px-2 py-0.5 font-mono text-[11px] font-medium text-signal">
              GitHub Releases 托管
            </span>
          </div>
          <p className="mt-1 text-xs text-ink-dim">
            {isZh
              ? '集中管理 CamouHub 客户端应用跨平台更新包，以及多引擎防关联原生内核（Chrome 155+, Camoufox 135+）。全球 CDN 零成本分发。'
              : 'Centrally manage desktop app releases and multi-engine anti-detect kernels with global GitHub CDN distribution.'}
          </p>
        </div>

        {/* 子 Tab 切换按钮 */}
        <div className="flex items-center rounded-lg border border-line bg-raised/40 p-1">
          <button
            onClick={() => setActiveSubTab('client')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
              activeSubTab === 'client'
                ? 'bg-surface text-signal shadow-sm font-semibold'
                : 'text-ink-dim hover:text-ink'
            }`}
          >
            <Monitor size={14} />
            {isZh ? '客户端应用更新' : 'Desktop App Updates'}
            {clientReleases.length > 0 && (
              <span className="ml-1 rounded-full bg-signal/15 px-1.5 py-0.2 font-mono text-[10px] text-signal">
                {clientReleases.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveSubTab('kernels')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
              activeSubTab === 'kernels'
                ? 'bg-surface text-signal shadow-sm font-semibold'
                : 'text-ink-dim hover:text-ink'
            }`}
          >
            <Layers size={14} />
            {isZh ? '多内核版本库' : 'Multi-Kernel Hub'}
            {kernelReleases.length > 0 && (
              <span className="ml-1 rounded-full bg-signal/15 px-1.5 py-0.2 font-mono text-[10px] text-signal">
                {kernelReleases.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* ================= 1. 客户端更新管理面板 ================= */}
      {activeSubTab === 'client' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-xs text-ink-dim">
              {isZh ? '客户端检测更新时，将向接口请求匹配自身平台（Mac/Win）的最新分发包。' : 'Clients query this API to fetch matching Mac/Win binary updates.'}
            </div>
            <button
              onClick={() => setShowClientModal(true)}
              className="btn btn-primary flex items-center gap-1.5 text-xs"
            >
              <Plus size={13} />
              {isZh ? '发布新客户端版本' : 'Publish Client Release'}
            </button>
          </div>

          {/* 客户端发布版本列表 */}
          <div className="rounded-lg border border-line bg-surface overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-line bg-canvas/60 font-medium text-ink-dim">
                <tr>
                  <th className="px-4 py-3">{isZh ? '客户端版本' : 'Version'}</th>
                  <th className="px-4 py-3">{isZh ? '更新标题 / 说明' : 'Title & Changelog'}</th>
                  <th className="px-4 py-3">{isZh ? '平台包配置' : 'Platform Packages'}</th>
                  <th className="px-4 py-3">{isZh ? '更新策略' : 'Strategy'}</th>
                  <th className="px-4 py-3">{isZh ? '发布时间' : 'Release Date'}</th>
                  <th className="px-4 py-3 text-right">{isZh ? '操作' : 'Actions'}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {clientReleases.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-xs text-ink-dim">
                      {isZh ? '暂无发布的客户端版本，点击右上角发布首个版本。' : 'No client releases published yet.'}
                    </td>
                  </tr>
                ) : (
                  clientReleases.map((cr, idx) => (
                    <tr key={cr.id} className="hover:bg-canvas/30 transition-colors">
                      <td className="px-4 py-3.5 font-mono">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-ink">v{cr.version}</span>
                          {idx === 0 && (
                            <span className="rounded bg-ok/15 px-1.5 py-0.5 text-[10px] font-sans font-semibold text-ok">
                              {isZh ? '最新版' : 'Latest'}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3.5 max-w-[280px]">
                        <div className="font-medium text-ink">{cr.title || 'CamouHub Update'}</div>
                        {cr.changelog && (
                          <div className="mt-0.5 truncate text-[11px] text-ink-dim font-sans" title={cr.changelog}>
                            {cr.changelog}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex flex-wrap gap-1.5">
                          {cr.mac_arm64_url && (
                            <span className="rounded bg-canvas px-1.5 py-0.5 font-mono text-[10px] text-ink border border-line" title={cr.mac_arm64_url}>
                              Mac Apple Silicon
                            </span>
                          )}
                          {cr.mac_x64_url && (
                            <span className="rounded bg-canvas px-1.5 py-0.5 font-mono text-[10px] text-ink border border-line" title={cr.mac_x64_url}>
                              Mac Intel
                            </span>
                          )}
                          {cr.win_x64_url && (
                            <span className="rounded bg-canvas px-1.5 py-0.5 font-mono text-[10px] text-ink border border-line" title={cr.win_x64_url}>
                              Win x64
                            </span>
                          )}
                          {!cr.mac_arm64_url && !cr.win_x64_url && (
                            <span className="text-[11px] text-danger">{isZh ? '未绑定包' : 'No packages'}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3.5">
                        {cr.is_force_update ? (
                          <span className="rounded bg-danger/15 px-1.5 py-0.5 text-[10px] font-semibold text-danger">
                            {isZh ? '强制更新' : 'Required'}
                          </span>
                        ) : (
                          <span className="rounded bg-raised px-1.5 py-0.5 text-[10px] text-ink-dim">
                            {isZh ? '普通更新' : 'Optional'}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-[11px] text-ink-dim">
                        {cr.created_at ? new Date(cr.created_at).toLocaleDateString() : '-'}
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <button
                          onClick={() => handleDeleteClientRelease(cr.id, cr.version)}
                          className="text-ink-dim hover:text-danger p-1 rounded transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ================= 2. 多内核版本库管理面板 ================= */}
      {activeSubTab === 'kernels' && (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-ink-dim">{isZh ? '内核引擎筛选:' : 'Engine:'}</span>
              <div className="flex items-center rounded border border-line bg-raised/30 p-0.5">
                {(['all', 'chromium', 'camoufox'] as const).map((eng) => (
                  <button
                    key={eng}
                    onClick={() => setKernelFilter(eng)}
                    className={`rounded px-2.5 py-1 text-[11px] font-medium transition-all ${
                      kernelFilter === eng ? 'bg-surface text-signal font-semibold shadow-xs' : 'text-ink-dim hover:text-ink'
                    }`}
                  >
                    {eng === 'all' ? (isZh ? '全部引擎' : 'All') : eng === 'chromium' ? 'Chromium' : 'Firefox'}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={() => setShowKernelModal(true)}
              className="btn btn-primary flex items-center gap-1.5 text-xs"
            >
              <Plus size={13} />
              {isZh ? '接入/发布新内核版本' : 'Register Kernel Release'}
            </button>
          </div>

          {/* 内核列表 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredKernels.map((k) => (
              <div
                key={k.id}
                className="rounded-lg border border-line bg-surface p-4 shadow-xs hover:border-signal/40 transition-colors flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-ok" />
                      <span className="font-mono text-sm font-bold text-ink">{k.version}</span>
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                          k.engine === 'chromium'
                            ? 'bg-[#1664ff]/10 text-[#1664ff]'
                            : 'bg-[#ff7d00]/10 text-[#ff7d00]'
                        }`}
                      >
                        {k.engine}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {k.is_recommended && (
                        <span className="rounded bg-ok/10 px-1.5 py-0.5 text-[10px] font-semibold text-ok">
                          {isZh ? '默认推荐' : 'Recommended'}
                        </span>
                      )}
                      <button
                        onClick={() => handleDeleteKernelRelease(k.id, k.version)}
                        className="text-ink-dim hover:text-danger p-1 transition-colors"
                        title="Delete"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>

                  <div className="mt-2 text-xs font-medium text-ink">
                    {k.display_name || `${k.engine} ${k.version}`}
                  </div>
                  {k.changelog && (
                    <div className="mt-1 text-[11px] text-ink-dim line-clamp-2">
                      {k.changelog}
                    </div>
                  )}

                  {/* 跨平台包地址卡片 */}
                  <div className="mt-3 space-y-1.5 rounded bg-canvas/60 p-2.5 font-mono text-[11px] border border-line/60">
                    <div className="flex items-center justify-between">
                      <span className="text-ink-dim font-sans">macOS (arm64):</span>
                      {k.mac_arm64_url ? (
                        <span className="truncate max-w-[200px] text-signal font-semibold" title={k.mac_arm64_url}>
                          ✓ GitHub CDN 就绪
                        </span>
                      ) : (
                        <span className="text-danger font-sans">{isZh ? '待上传' : 'Pending'}</span>
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-ink-dim font-sans">Windows (x64):</span>
                      {k.win_x64_url ? (
                        <span className="truncate max-w-[200px] text-signal font-semibold" title={k.win_x64_url}>
                          ✓ GitHub CDN 就绪
                        </span>
                      ) : (
                        <span className="text-danger font-sans">{isZh ? '待上传' : 'Pending'}</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between border-t border-line/60 pt-2 text-[11px] text-ink-dim">
                  <span>ID: {k.id}</span>
                  <span>{k.created_at ? new Date(k.created_at).toLocaleDateString() : ''}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ================= 3. 命令行一键自动发布助手卡片 ================= */}
      <div className="rounded-lg border border-signal/20 bg-signal/5 p-4 text-xs">
        <div className="flex items-center justify-between font-semibold text-ink">
          <div className="flex items-center gap-2">
            <Terminal size={15} className="text-signal" />
            <span>{isZh ? 'CLI 一键自动化发布工具 (GitHub Releases 同步)' : 'CLI Release Automation Tool'}</span>
          </div>
          <span className="font-mono text-[11px] text-signal">scripts/publish_release.py</span>
        </div>
        <p className="mt-1 text-ink-dim leading-relaxed">
          {isZh
            ? '编译完成后，无需在网页上手工创建 Release，通过自动化脚本即可一键打包、创建 GitHub Release 资产并自动同步回写本后台：'
            : 'After compilation, run this CLI to package, upload to GitHub Releases, and register directly to this console:'}
        </p>

        <div className="mt-2.5 space-y-2 font-mono text-[11px]">
          <div className="flex items-center justify-between rounded bg-canvas px-3 py-2 border border-line">
            <span className="text-ink break-all">
              python scripts/publish_release.py --type kernel --engine chromium --version 155.0.8059 --platform mac_arm64
            </span>
            <button
              onClick={() => copyToClipboard('python scripts/publish_release.py --type kernel --engine chromium --version 155.0.8059 --platform mac_arm64', 'cli_mac')}
              className="ml-3 shrink-0 text-ink-dim hover:text-signal"
            >
              {copiedText === 'cli_mac' ? <Check size={14} className="text-ok" /> : <Copy size={14} />}
            </button>
          </div>
        </div>
      </div>

      {/* ================= 模态弹窗: 发布客户端版本 ================= */}
      {showClientModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-xl border border-line bg-surface p-6 shadow-2xl animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <h3 className="text-sm font-semibold text-ink">
                {isZh ? '发布新客户端版本' : 'Publish Client Release'}
              </h3>
              <button onClick={() => setShowClientModal(false)} className="text-ink-dim hover:text-ink">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSaveClientRelease} className="mt-4 space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-medium text-ink">{isZh ? '版本号 *' : 'Version *'}</label>
                  <input
                    type="text"
                    required
                    placeholder="1.0.1"
                    value={clientForm.version}
                    onChange={(e) => setClientForm({ ...clientForm, version: e.target.value })}
                    className="input mt-1 w-full font-mono"
                  />
                </div>
                <div>
                  <label className="font-medium text-ink">{isZh ? '最低兼容版本' : 'Min Version'}</label>
                  <input
                    type="text"
                    placeholder="1.0.0"
                    value={clientForm.min_version}
                    onChange={(e) => setClientForm({ ...clientForm, min_version: e.target.value })}
                    className="input mt-1 w-full font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="font-medium text-ink">{isZh ? '发布标题' : 'Title'}</label>
                <input
                  type="text"
                  placeholder="CamouHub v1.0.1 性能与内核升级"
                  value={clientForm.title}
                  onChange={(e) => setClientForm({ ...clientForm, title: e.target.value })}
                  className="input mt-1 w-full"
                />
              </div>

              <div>
                <label className="font-medium text-ink">{isZh ? '更新说明 (Changelog)' : 'Changelog'}</label>
                <textarea
                  rows={2}
                  placeholder="修复了多开移动端视口溢出问题，全面升级 Chrome 155 防关联原生内核。"
                  value={clientForm.changelog}
                  onChange={(e) => setClientForm({ ...clientForm, changelog: e.target.value })}
                  className="input mt-1 w-full"
                />
              </div>

              <div className="space-y-2 border-t border-line/60 pt-2">
                <div>
                  <label className="font-medium text-ink">macOS Apple Silicon 下载 URL</label>
                  <input
                    type="url"
                    placeholder="https://github.com/hkxuepf/camoufox/releases/download/v1.0.1/CamouHub-mac-arm64.dmg"
                    value={clientForm.mac_arm64_url}
                    onChange={(e) => setClientForm({ ...clientForm, mac_arm64_url: e.target.value })}
                    className="input mt-1 w-full font-mono text-[11px]"
                  />
                </div>
                <div>
                  <label className="font-medium text-ink">Windows x64 下载 URL</label>
                  <input
                    type="url"
                    placeholder="https://github.com/hkxuepf/camoufox/releases/download/v1.0.1/CamouHub-win-x64-Setup.exe"
                    value={clientForm.win_x64_url}
                    onChange={(e) => setClientForm({ ...clientForm, win_x64_url: e.target.value })}
                    className="input mt-1 w-full font-mono text-[11px]"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="force_update"
                  checked={clientForm.is_force_update}
                  onChange={(e) => setClientForm({ ...clientForm, is_force_update: e.target.checked })}
                  className="h-4 w-4 rounded accent-signal"
                />
                <label htmlFor="force_update" className="text-ink font-medium cursor-pointer">
                  {isZh ? '强制更新（所有低于此版本的客户端必须更新后才能继续使用）' : 'Force update (Block older clients)'}
                </label>
              </div>

              <div className="mt-5 flex justify-end gap-2 border-t border-line pt-3">
                <button type="button" onClick={() => setShowClientModal(false)} className="btn btn-ghost">
                  {isZh ? '取消' : 'Cancel'}
                </button>
                <button type="submit" className="btn btn-primary">
                  {isZh ? '立即发布' : 'Publish'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= 模态弹窗: 接入/发布内核版本 ================= */}
      {showKernelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-xl border border-line bg-surface p-6 shadow-2xl animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <h3 className="text-sm font-semibold text-ink">
                {isZh ? '接入/发布防关联内核' : 'Register Anti-detect Kernel'}
              </h3>
              <button onClick={() => setShowKernelModal(false)} className="text-ink-dim hover:text-ink">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSaveKernelRelease} className="mt-4 space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-medium text-ink">{isZh ? '内核引擎 *' : 'Engine *'}</label>
                  <select
                    value={kernelForm.engine}
                    onChange={(e) => setKernelForm({ ...kernelForm, engine: e.target.value as any })}
                    className="input mt-1 w-full"
                  >
                    <option value="chromium">Chromium</option>
                    <option value="camoufox">Camoufox (Firefox)</option>
                  </select>
                </div>
                <div>
                  <label className="font-medium text-ink">{isZh ? '内核版本号 *' : 'Kernel Version *'}</label>
                  <input
                    type="text"
                    required
                    placeholder="155.0.8059"
                    value={kernelForm.version}
                    onChange={(e) => setKernelForm({ ...kernelForm, version: e.target.value })}
                    className="input mt-1 w-full font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="font-medium text-ink">{isZh ? '显示名称' : 'Display Name'}</label>
                <input
                  type="text"
                  placeholder="Chrome 155 (首发基准原生内核)"
                  value={kernelForm.display_name}
                  onChange={(e) => setKernelForm({ ...kernelForm, display_name: e.target.value })}
                  className="input mt-1 w-full"
                />
              </div>

              <div>
                <label className="font-medium text-ink">{isZh ? '特性描述' : 'Changelog / Notes'}</label>
                <textarea
                  rows={2}
                  placeholder="原生防关联视口沙盒锁，内置 Canvas/WebGL 指纹加噪引擎"
                  value={kernelForm.changelog}
                  onChange={(e) => setKernelForm({ ...kernelForm, changelog: e.target.value })}
                  className="input mt-1 w-full"
                />
              </div>

              <div className="space-y-2 border-t border-line/60 pt-2">
                <div>
                  <label className="font-medium text-ink">macOS (Apple Silicon arm64) 下载直链</label>
                  <input
                    type="url"
                    placeholder="https://github.com/hkxuepf/camoufox/releases/download/v155.0/chromium-155.0.8059-mac-arm64.tar.gz"
                    value={kernelForm.mac_arm64_url}
                    onChange={(e) => setKernelForm({ ...kernelForm, mac_arm64_url: e.target.value })}
                    className="input mt-1 w-full font-mono text-[11px]"
                  />
                </div>
                <div>
                  <label className="font-medium text-ink">Windows (x64) 下载直链</label>
                  <input
                    type="url"
                    placeholder="https://github.com/hkxuepf/camoufox/releases/download/v155.0/chromium-155.0.8059-win-x64.zip"
                    value={kernelForm.win_x64_url}
                    onChange={(e) => setKernelForm({ ...kernelForm, win_x64_url: e.target.value })}
                    className="input mt-1 w-full font-mono text-[11px]"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="recommended_kernel"
                  checked={kernelForm.is_recommended}
                  onChange={(e) => setKernelForm({ ...kernelForm, is_recommended: e.target.checked })}
                  className="h-4 w-4 rounded accent-signal"
                />
                <label htmlFor="recommended_kernel" className="text-ink font-medium cursor-pointer">
                  {isZh ? '设为新建环境默认推荐内核' : 'Set as default recommended kernel'}
                </label>
              </div>

              <div className="mt-5 flex justify-end gap-2 border-t border-line pt-3">
                <button type="button" onClick={() => setShowKernelModal(false)} className="btn btn-ghost">
                  {isZh ? '取消' : 'Cancel'}
                </button>
                <button type="submit" className="btn btn-primary">
                  {isZh ? '保存并上架' : 'Save & Publish'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
