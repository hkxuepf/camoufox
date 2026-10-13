'use client'

import { useEffect, useState, useMemo } from 'react'
import {
  Check,
  CheckCircle2,
  Download,
  FolderArchive,
  Globe,
  Layers,
  Loader2,
  Package,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react'

import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { extensionsAPI, type ExtensionItem } from '@/lib/api'

function ExtensionAvatar({
  name,
  iconUrl,
  category,
}: {
  name: string
  iconUrl?: string | null
  category: string
}) {
  const [imgFailed, setImgFailed] = useState(false)

  // Reset imgFailed if iconUrl changes
  useEffect(() => {
    setImgFailed(false)
  }, [iconUrl])

  if (iconUrl && !imgFailed) {
    return (
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white border border-[#eaedf1] p-1.5 overflow-hidden shadow-2xs">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={iconUrl}
          alt={name}
          className="h-full w-full object-contain"
          onError={() => setImgFailed(true)}
        />
      </div>
    )
  }

  // Stylish fallback gradient avatar badge
  const gradient =
    category === 'crypto'
      ? 'from-amber-500 to-orange-600'
      : category === 'proxy'
      ? 'from-emerald-500 to-teal-600'
      : category === 'custom'
      ? 'from-indigo-500 to-violet-600'
      : 'from-blue-500 to-cyan-600'

  const initial = (name || 'E').slice(0, 1).toUpperCase()

  return (
    <div
      className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${gradient} text-white font-bold text-lg shadow-2xs select-none`}
    >
      {initial}
    </div>
  )
}

export default function ExtensionsPage() {
  const [extensions, setExtensions] = useState<ExtensionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importUrlOrId, setImportUrlOrId] = useState('')
  const [installingId, setInstallingId] = useState<string | null>(null)
  const [fileToUpload, setFileToUpload] = useState<File | null>(null)

  const toast = useToast()

  const loadExtensions = async () => {
    try {
      setLoading(true)
      const res = await extensionsAPI.list()
      setExtensions(res.extensions || [])
    } catch (err: any) {
      toast('error', '加载插件列表失败', err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadExtensions()
  }, [])

  const filtered = useMemo(() => {
    return extensions.filter((e) => {
      if (category !== 'all') {
        if (category === 'custom' && Boolean(e.is_preset)) return false
        if (category !== 'custom' && e.category !== category) return false
      }
      if (!search.trim()) return true
      const q = search.toLowerCase()
      return (
        e.name.toLowerCase().includes(q) ||
        (e.description && e.description.toLowerCase().includes(q))
      )
    })
  }, [extensions, category, search])

  const handleToggle = async (e: ExtensionItem) => {
    const nextState = !Boolean(e.enabled)
    try {
      await extensionsAPI.toggle(e.id, nextState)
      setExtensions((prev) =>
        prev.map((item) => (item.id === e.id ? { ...item, enabled: nextState ? 1 : 0 } : item))
      )
      toast('ok', `${e.name} 已${nextState ? '启用' : '禁用'}`)
    } catch (err: any) {
      toast('error', '操作失败', err.message)
    }
  }

  const handleInstallPreset = async (e: ExtensionItem) => {
    setInstallingId(e.id)
    try {
      const res = await extensionsAPI.installPreset(e.id)
      setExtensions((prev) =>
        prev.map((item) =>
          item.id === e.id ? { ...item, local_path: res.local_path, enabled: 1 } : item
        )
      )
      toast('ok', `${e.name} 安装准备就绪`)
      // Reload to pick up extracted base64 icon if updated
      loadExtensions()
    } catch (err: any) {
      toast('error', '安装失败', err.message)
    } finally {
      setInstallingId(null)
    }
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确定删除自定义扩展 “${name}” 吗？`)) return
    try {
      await extensionsAPI.delete(id)
      setExtensions((prev) => prev.filter((item) => item.id !== id))
      toast('ok', '插件已删除')
    } catch (err: any) {
      toast('error', '删除失败', err.message)
    }
  }

  const handleUploadSubmit = async () => {
    if (!fileToUpload) {
      toast('error', '请先选择 .crx 或 .zip 插件文件')
      return
    }
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', fileToUpload)
      const res = await extensionsAPI.upload(fd)
      toast('ok', `成功安装自定义扩展: ${res.name}`)
      setUploadOpen(false)
      setFileToUpload(null)
      loadExtensions()
    } catch (err: any) {
      toast('error', '上传安装失败', err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleImportSubmit = async () => {
    if (!importUrlOrId.trim()) {
      toast('error', '请输入 Chrome 商店链接或插件 ID')
      return
    }
    setImporting(true)
    try {
      const res = await extensionsAPI.importWebstore(importUrlOrId.trim())
      toast('ok', `成功导入并就绪扩展: ${res.name}`)
      setImportOpen(false)
      setImportUrlOrId('')
      loadExtensions()
    } catch (err: any) {
      toast('error', '导入失败', err.message)
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="flex h-full flex-col bg-[#f8fafc] text-[#1e293b] overflow-hidden">
      {/* 1. Header */}
      <div className="shrink-0 border-b border-[#e2e8f0] bg-white px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[#0f172a] flex items-center gap-2">
              <Package className="h-5 w-5 text-[#1664ff]" />
              应用与扩展中心
            </h1>
            <p className="mt-0.5 text-xs text-[#64748b]">
              集成热门 Web3 钱包、双重验证、自动翻译与常用运营扩展，支持一键从谷歌插件商店直接导入，随环境启动静默加载
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setImportOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-[#1664ff] bg-[#1664ff]/10 px-3.5 py-2 text-xs font-semibold text-[#1664ff] shadow-2xs hover:bg-[#1664ff]/15 transition cursor-pointer"
            >
              <Download className="h-4 w-4" />
              从谷歌商店导入
            </button>
            <button
              onClick={() => setUploadOpen(true)}
              className="flex items-center gap-1.5 rounded-lg bg-[#1664ff] px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#0e52db] transition cursor-pointer"
            >
              <Upload className="h-4 w-4" />
              上传本地扩展 (.crx / .zip)
            </button>
            <button
              onClick={loadExtensions}
              className="flex items-center gap-1.5 rounded-lg border border-[#e2e8f0] bg-white px-3 py-2 text-xs font-medium text-[#334155] shadow-2xs hover:bg-[#f1f5f9] transition cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              刷新
            </button>
          </div>
        </div>

        {/* Categories Bar */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex rounded-lg bg-[#f1f5f9] p-0.5 text-xs font-medium text-[#64748b]">
            {[
              { id: 'all', label: '全部应用' },
              { id: 'crypto', label: 'Web3 / 钱包' },
              { id: 'tool', label: '效率与工具' },
              { id: 'proxy', label: '网络代理' },
              { id: 'custom', label: '自定义 / 导入' },
            ].map((cat) => (
              <button
                key={cat.id}
                onClick={() => setCategory(cat.id)}
                className={`rounded-md px-3.5 py-1.5 cursor-pointer transition ${
                  category === cat.id
                    ? 'bg-white text-[#1664ff] shadow-xs font-semibold'
                    : 'hover:text-[#0f172a]'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          <div className="relative w-64">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[#94a3b8]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索扩展名称或说明..."
              className="w-full rounded-md border border-[#e2e8f0] bg-[#f8fafc] py-1.5 pl-8 pr-3 text-xs text-[#0f172a] placeholder-[#94a3b8] focus:border-[#1664ff] focus:bg-white focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* 2. Grid Cards */}
      <div className="flex-1 overflow-auto p-6">
        {loading ? (
          <div className="py-20 text-center text-[#94a3b8]">
            <Loader2 className="mx-auto h-7 w-7 animate-spin text-[#1664ff]" />
            <span className="mt-2 block text-xs">加载扩展应用目录...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-20 text-center text-[#94a3b8]">
            <Package className="mx-auto h-9 w-9 text-[#cbd5e1]" />
            <p className="mt-2 text-sm font-medium text-[#475569]">未找到相关插件</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filtered.map((ext) => {
              const isEnabled = Boolean(ext.enabled)
              const isInstalled = Boolean(ext.local_path)
              const isInstalling = installingId === ext.id

              return (
                <div
                  key={ext.id}
                  className="group flex flex-col justify-between rounded-xl border border-[#eaedf1] bg-white p-4 shadow-2xs transition-all hover:border-[#cbd5e1] hover:shadow-xs"
                >
                  <div>
                    <div className="flex items-start justify-between gap-3">
                      {/* Icon with robust vector / base64 / gradient fallback */}
                      <ExtensionAvatar
                        name={ext.name}
                        iconUrl={ext.icon_url}
                        category={ext.category}
                      />

                      {/* Status switch / preset badge */}
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                            ext.category === 'crypto'
                              ? 'bg-[#e0e7ff] text-[#4338ca]'
                              : ext.category === 'proxy'
                              ? 'bg-[#dcfce7] text-[#15803d]'
                              : ext.category === 'custom'
                              ? 'bg-[#fae8ff] text-[#86198f]'
                              : 'bg-[#f1f5f9] text-[#475569]'
                          }`}
                        >
                          {ext.category.toUpperCase()}
                        </span>

                        {!ext.is_preset && (
                          <button
                            onClick={() => handleDelete(ext.id, ext.name)}
                            className="text-[#94a3b8] hover:text-[#ef4444] transition p-1 cursor-pointer"
                            title="删除"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="mt-3">
                      <div className="flex items-baseline gap-1.5">
                        <h3 className="font-semibold text-sm text-[#0f172a] truncate" title={ext.name}>
                          {ext.name}
                        </h3>
                        <span className="text-[10px] text-[#94a3b8]">v{ext.version}</span>
                      </div>
                      <p
                        className="mt-1 line-clamp-2 text-xs text-[#64748b] leading-relaxed min-h-[36px]"
                        title={ext.description || ''}
                      >
                        {ext.description || '无详细说明'}
                      </p>
                    </div>
                  </div>

                  {/* Actions footer */}
                  <div className="mt-4 pt-3 border-t border-[#f1f5f9] flex items-center justify-between">
                    <span className="text-[11px] text-[#94a3b8] flex items-center gap-1">
                      {ext.is_preset ? (
                        <>
                          <CheckCircle2 className="h-3 w-3 text-[#1664ff]" />
                          官方精选
                        </>
                      ) : (
                        <>
                          <Globe className="h-3 w-3 text-[#8b5cf6]" />
                          自定义/导入
                        </>
                      )}
                    </span>

                    <div>
                      {ext.is_preset && !isInstalled ? (
                        <button
                          onClick={() => handleInstallPreset(ext)}
                          disabled={isInstalling}
                          className="flex items-center gap-1 rounded-md bg-[#f1f5f9] px-2.5 py-1 text-xs font-semibold text-[#1664ff] hover:bg-[#e0e7ff] transition cursor-pointer disabled:opacity-50"
                        >
                          {isInstalling ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Download className="h-3 w-3" />
                          )}
                          安装就绪
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleToggle(ext)}
                          className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                            isEnabled ? 'bg-[#1664ff]' : 'bg-[#cbd5e1]'
                          }`}
                        >
                          <span
                            className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                              isEnabled ? 'translate-x-4' : 'translate-x-0'
                            }`}
                          />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* 3. Chrome Web Store Import Modal */}
      <Modal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="从谷歌插件商店导入扩展"
        subtitle="粘贴 Chrome Web Store 链接或 32 位插件 ID，自动下载官方正版安装包并解析图标"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#334155] mb-1.5">
              谷歌商店网址或插件 ID
            </label>
            <input
              type="text"
              value={importUrlOrId}
              onChange={(e) => setImportUrlOrId(e.target.value)}
              placeholder="例如: https://chromewebstore.google.com/detail/... 或 32位字母ID"
              className="w-full rounded-lg border border-[#cbd5e1] bg-white px-3.5 py-2 text-xs text-[#0f172a] placeholder-[#94a3b8] focus:border-[#1664ff] focus:outline-none focus:ring-1 focus:ring-[#1664ff]"
            />
          </div>

          {/* Quick recommendations */}
          <div className="rounded-lg bg-[#f8fafc] border border-[#e2e8f0] p-3 text-xs">
            <div className="flex items-center gap-1.5 font-medium text-[#475569] mb-2">
              <Sparkles className="h-3.5 w-3.5 text-[#1664ff]" />
              快速填入热门扩展尝试：
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                { name: 'Tampermonkey 油猴', id: 'dhdgffkkebhmkfjojejmpbldmpobfkfo' },
                { name: 'MetaMask', id: 'nkbihfbeogaeaoehlefnkodbefgpgknn' },
                { name: 'Cookie-Editor', id: 'hlkenndednhfkekhgcdicdfddnkalmdm' },
                { name: 'uBlock Origin Lite', id: 'ddkjiahejlhfcafbddmgiahcphecmpfh' },
                { name: '2FA Authenticator', id: 'bhghoamapcdpbohphigoooaddinpkbai' },
              ].map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setImportUrlOrId(item.id)}
                  className="rounded bg-white border border-[#cbd5e1] px-2 py-1 text-[11px] text-[#334155] hover:border-[#1664ff] hover:text-[#1664ff] transition cursor-pointer"
                >
                  {item.name}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-[#f1f5f9]">
            <button
              type="button"
              onClick={() => setImportOpen(false)}
              className="rounded-lg border border-[#e2e8f0] px-4 py-2 text-xs font-medium text-[#475569] hover:bg-[#f8fafc] cursor-pointer"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleImportSubmit}
              disabled={importing || !importUrlOrId.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-[#1664ff] px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#0e52db] disabled:opacity-50 cursor-pointer"
            >
              {importing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  正在下载与解析扩展...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  立即导入安装
                </>
              )}
            </button>
          </div>
        </div>
      </Modal>

      {/* 4. Local File Upload Modal */}
      <Modal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        title="上传自定义扩展安装包"
        subtitle="支持 Chrome/Chromium 格式的 .crx 安装包或 .zip 解压包"
      >
        <div className="space-y-4">
          <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#cbd5e1] bg-[#f8fafc] p-6 text-center hover:border-[#1664ff] transition">
            <FolderArchive className="h-10 w-10 text-[#94a3b8]" />
            <div className="mt-3 text-xs text-[#334155] font-medium">
              点击选择或拖拽扩展包到此处
            </div>
            <p className="mt-1 text-[11px] text-[#94a3b8]">支持 .crx 与包含 manifest.json 的 .zip</p>

            <input
              type="file"
              accept=".crx,.zip"
              onChange={(e) => setFileToUpload(e.target.files?.[0] || null)}
              className="mt-3 block text-xs text-[#475569] file:mr-3 file:rounded-md file:border-0 file:bg-[#1664ff] file:px-3 file:py-1 file:text-xs file:font-semibold file:text-white hover:file:bg-[#0e52db] cursor-pointer"
            />
          </div>

          {fileToUpload && (
            <div className="rounded-lg bg-[#f0fdf4] border border-[#bbf7d0] p-3 text-xs text-[#166534] flex items-center justify-between">
              <span>已选择: {fileToUpload.name} ({(fileToUpload.size / 1024).toFixed(1)} KB)</span>
              <Check className="h-4 w-4 text-[#16a34a]" />
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2 border-t border-[#f1f5f9]">
            <button
              type="button"
              onClick={() => setUploadOpen(false)}
              className="rounded-lg border border-[#e2e8f0] px-4 py-2 text-xs font-medium text-[#475569] hover:bg-[#f8fafc] cursor-pointer"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleUploadSubmit}
              disabled={uploading || !fileToUpload}
              className="flex items-center gap-1.5 rounded-lg bg-[#1664ff] px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#0e52db] disabled:opacity-50 cursor-pointer"
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              开始上传安装
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
