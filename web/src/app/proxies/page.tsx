'use client'

import { useEffect, useState, useMemo } from 'react'
import {
  Activity,
  CheckCircle2,
  Copy,
  Download,
  Filter,
  Globe,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Server,
  Trash2,
  Upload,
  Wifi,
  WifiOff,
  XCircle,
} from 'lucide-react'

import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { proxiesAPI, type ProxyItem } from '@/lib/api'

export default function ProxiesPage() {
  const [proxies, setProxies] = useState<ProxyItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'failed' | 'uncheck'>('all')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  // Import Modal
  const [importOpen, setImportOpen] = useState(false)
  const [importContent, setImportContent] = useState('')
  const [defaultType, setDefaultType] = useState('socks5')
  const [importing, setImporting] = useState(false)

  // Checking state
  const [checkingIds, setCheckingIds] = useState<Set<string>>(new Set())
  const [batchChecking, setBatchChecking] = useState(false)

  const toast = useToast()

  const loadData = async () => {
    try {
      setLoading(true)
      const res = await proxiesAPI.list()
      setProxies(res.proxies || [])
    } catch (err: any) {
      toast('error', '加载代理列表失败', err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Stats
  const stats = useMemo(() => {
    const total = proxies.length
    const active = proxies.filter((p) => p.status === 'active').length
    const failed = proxies.filter((p) => p.status === 'failed').length
    const uncheck = proxies.filter((p) => !p.status || p.status === 'uncheck').length

    const validLatencies = proxies
      .filter((p) => p.status === 'active' && p.latency_ms && p.latency_ms > 0)
      .map((p) => p.latency_ms!)

    const avgLatency =
      validLatencies.length > 0
        ? Math.round(validLatencies.reduce((a, b) => a + b, 0) / validLatencies.length)
        : null

    return { total, active, failed, uncheck, avgLatency }
  }, [proxies])

  // Filtered proxies
  const filtered = useMemo(() => {
    return proxies.filter((p) => {
      if (statusFilter !== 'all' && p.status !== statusFilter) return false
      if (!search.trim()) return true
      const q = search.toLowerCase()
      return (
        (p.name && p.name.toLowerCase().includes(q)) ||
        p.server.toLowerCase().includes(q) ||
        (p.ip && p.ip.toLowerCase().includes(q)) ||
        (p.country && p.country.toLowerCase().includes(q))
      )
    })
  }, [proxies, statusFilter, search])

  // Check single
  const handleCheckSingle = async (p: ProxyItem) => {
    setCheckingIds((prev) => new Set(prev).add(p.id))
    try {
      const res = await proxiesAPI.check(p.id)
      setProxies((prev) =>
        prev.map((item) => (item.id === p.id ? { ...item, ...res } : item))
      )
      if (res.status === 'active') {
        toast('ok', `代理可用 [${res.latency_ms}ms]`, `出口 IP: ${res.ip || p.server}`)
      } else {
        toast('error', '代理不可用', '无法连通目标服务器')
      }
    } catch (err: any) {
      toast('error', '检测失败', err.message)
    } finally {
      setCheckingIds((prev) => {
        const next = new Set(prev)
        next.delete(p.id)
        return next
      })
    }
  }

  // Batch Check
  const handleBatchCheck = async () => {
    const ids = selectedIds.size > 0 ? Array.from(selectedIds) : undefined
    setBatchChecking(true)
    try {
      const res = await proxiesAPI.batchCheck(ids)
      toast('ok', `完成批量检测: ${res.checked} 个代理已更新`)
      loadData()
    } catch (err: any) {
      toast('error', '批量检测失败', err.message)
    } finally {
      setBatchChecking(false)
    }
  }

  // Batch Import
  const handleBatchImport = async () => {
    if (!importContent.trim()) {
      toast('error', '请输入代理配置内容')
      return
    }
    setImporting(true)
    try {
      const res = await proxiesAPI.batchImport({
        content: importContent,
        default_type: defaultType,
      })
      toast('ok', `成功导入 ${res.imported} 个代理`)
      setImportOpen(false)
      setImportContent('')
      loadData()
    } catch (err: any) {
      toast('error', '导入失败', err.message)
    } finally {
      setImporting(false)
    }
  }

  // Delete single
  const handleDelete = async (id: string) => {
    if (!confirm('确定删除该代理配置吗？')) return
    try {
      await proxiesAPI.delete(id)
      toast('ok', '已删除代理')
      setProxies((prev) => prev.filter((p) => p.id !== id))
      setSelectedIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    } catch (err: any) {
      toast('error', '删除失败', err.message)
    }
  }

  // Batch Delete
  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`确定删除选中的 ${selectedIds.size} 个代理吗？`)) return
    try {
      const res = await proxiesAPI.batchDelete(Array.from(selectedIds))
      toast('ok', `成功删除 ${res.deleted} 个代理`)
      setSelectedIds(new Set())
      loadData()
    } catch (err: any) {
      toast('error', '删除失败', err.message)
    }
  }

  // Clean Failed
  const handleCleanFailed = async () => {
    const failedIds = proxies.filter((p) => p.status === 'failed').map((p) => p.id)
    if (failedIds.length === 0) {
      toast('info', '暂无失效代理')
      return
    }
    if (!confirm(`确定清除全部 ${failedIds.length} 个失效代理吗？`)) return
    try {
      const res = await proxiesAPI.batchDelete(failedIds)
      toast('ok', `已清理 ${res.deleted} 个失效代理`)
      loadData()
    } catch (err: any) {
      toast('error', '清理失败', err.message)
    }
  }

  // Export
  const handleExport = () => {
    const lines = filtered.map((p) => {
      const auth = p.username ? `${p.username}:${p.password || ''}@` : ''
      return `${p.type}://${auth}${p.server}:${p.port || 80}`
    })
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `proxies_export_${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
    URL.revokeObjectURL(url)
    toast('ok', `已导出 ${lines.length} 条代理`)
  }

  // Select all toggle
  const toggleSelectAll = () => {
    if (selectedIds.size === filtered.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filtered.map((p) => p.id)))
    }
  }

  const toggleSelectOne = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="flex h-full flex-col bg-[#f8fafc] text-[#1e293b] overflow-hidden">
      {/* 1. Header & Stats Bar */}
      <div className="shrink-0 border-b border-[#e2e8f0] bg-white px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[#0f172a] flex items-center gap-2">
              <Globe className="h-5 w-5 text-[#1664ff]" />
              代理池管理
            </h1>
            <p className="mt-0.5 text-xs text-[#64748b]">
              统一管理商业级代理节点，支持批量导入、智能测速、自动分配与出口 IP 校验
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setImportOpen(true)}
              className="flex items-center gap-1.5 rounded-lg bg-[#1664ff] px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#0e52db] transition cursor-pointer"
            >
              <Plus className="h-4 w-4" />
              批量导入代理
            </button>
            <button
              onClick={handleBatchCheck}
              disabled={batchChecking || proxies.length === 0}
              className="flex items-center gap-1.5 rounded-lg border border-[#e2e8f0] bg-white px-3 py-2 text-xs font-medium text-[#334155] shadow-2xs hover:bg-[#f1f5f9] transition disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`h-3.5 w-3.5 text-[#1664ff] ${batchChecking ? 'animate-spin' : ''}`} />
              {batchChecking ? '测速中...' : selectedIds.size > 0 ? `测试选中 (${selectedIds.size})` : '全部测速'}
            </button>
            <button
              onClick={handleCleanFailed}
              className="flex items-center gap-1.5 rounded-lg border border-[#fed7d7] bg-[#fff5f5] px-3 py-2 text-xs font-medium text-[#c53030] hover:bg-[#fed7d7] transition cursor-pointer"
              title="清理失效节点"
            >
              <Trash2 className="h-3.5 w-3.5" />
              清理失效
            </button>
            <button
              onClick={handleExport}
              disabled={filtered.length === 0}
              className="flex items-center gap-1.5 rounded-lg border border-[#e2e8f0] bg-white px-3 py-2 text-xs font-medium text-[#334155] hover:bg-[#f1f5f9] transition disabled:opacity-50 cursor-pointer"
            >
              <Download className="h-3.5 w-3.5" />
              导出
            </button>
          </div>
        </div>

        {/* 4 Cards Stats Bar */}
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="flex items-center gap-3 rounded-lg border border-[#e2e8f0] bg-[#f8fafc] p-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#e8f3ff] text-[#1664ff]">
              <Server className="h-4 w-4" />
            </div>
            <div>
              <div className="text-[11px] text-[#64748b]">代理总数</div>
              <div className="text-base font-bold text-[#0f172a]">{stats.total}</div>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-lg border border-[#e2e8f0] bg-[#f8fafc] p-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#e6fffa] text-[#059669]">
              <Wifi className="h-4 w-4" />
            </div>
            <div>
              <div className="text-[11px] text-[#64748b]">正常可用</div>
              <div className="text-base font-bold text-[#059669]">{stats.active}</div>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-lg border border-[#e2e8f0] bg-[#f8fafc] p-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#fff1f0] text-[#e11d48]">
              <WifiOff className="h-4 w-4" />
            </div>
            <div>
              <div className="text-[11px] text-[#64748b]">连接失败</div>
              <div className="text-base font-bold text-[#e11d48]">{stats.failed}</div>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-lg border border-[#e2e8f0] bg-[#f8fafc] p-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#f3e8ff] text-[#7928ca]">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <div className="text-[11px] text-[#64748b]">平均延迟</div>
              <div className="text-base font-bold text-[#7928ca]">
                {stats.avgLatency !== null ? `${stats.avgLatency} ms` : '-'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Filter & Toolbar */}
      <div className="flex shrink-0 items-center justify-between border-b border-[#eaedf1] bg-white px-6 py-2.5">
        <div className="flex items-center gap-3">
          {/* Status Tabs */}
          <div className="flex rounded-lg bg-[#f1f5f9] p-0.5 text-xs font-medium text-[#64748b]">
            <button
              onClick={() => setStatusFilter('all')}
              className={`rounded-md px-3 py-1 cursor-pointer transition ${
                statusFilter === 'all' ? 'bg-white text-[#0f172a] shadow-xs font-semibold' : 'hover:text-[#0f172a]'
              }`}
            >
              全部 ({stats.total})
            </button>
            <button
              onClick={() => setStatusFilter('active')}
              className={`rounded-md px-3 py-1 cursor-pointer transition ${
                statusFilter === 'active' ? 'bg-white text-[#059669] shadow-xs font-semibold' : 'hover:text-[#0f172a]'
              }`}
            >
              可用 ({stats.active})
            </button>
            <button
              onClick={() => setStatusFilter('failed')}
              className={`rounded-md px-3 py-1 cursor-pointer transition ${
                statusFilter === 'failed' ? 'bg-white text-[#e11d48] shadow-xs font-semibold' : 'hover:text-[#0f172a]'
              }`}
            >
              失效 ({stats.failed})
            </button>
            <button
              onClick={() => setStatusFilter('uncheck')}
              className={`rounded-md px-3 py-1 cursor-pointer transition ${
                statusFilter === 'uncheck' ? 'bg-white text-[#64748b] shadow-xs font-semibold' : 'hover:text-[#0f172a]'
              }`}
            >
              未测 ({stats.uncheck})
            </button>
          </div>

          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2 pl-2 text-xs text-[#64748b] border-l border-[#e2e8f0]">
              <span>已选择 {selectedIds.size} 项</span>
              <button
                onClick={handleBatchDelete}
                className="text-[#e11d48] hover:underline cursor-pointer font-medium"
              >
                批量删除
              </button>
            </div>
          )}
        </div>

        {/* Search Input */}
        <div className="relative w-64">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[#94a3b8]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索 IP、端口、别名或国家..."
            className="w-full rounded-md border border-[#e2e8f0] bg-[#f8fafc] py-1.5 pl-8 pr-3 text-xs text-[#0f172a] placeholder-[#94a3b8] focus:border-[#1664ff] focus:bg-white focus:outline-none"
          />
        </div>
      </div>

      {/* 3. Proxy Table */}
      <div className="flex-1 overflow-auto p-6">
        <div className="overflow-hidden rounded-xl border border-[#eaedf1] bg-white shadow-2xs">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-[#eaedf1] bg-[#f8fafc] text-[11px] font-semibold text-[#64748b]">
                <th className="w-10 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={filtered.length > 0 && selectedIds.size === filtered.length}
                    onChange={toggleSelectAll}
                    className="rounded border-[#cbd5e1] text-[#1664ff] focus:ring-0 cursor-pointer"
                  />
                </th>
                <th className="px-4 py-3">协议与节点别名</th>
                <th className="px-4 py-3">代理主机与端口</th>
                <th className="px-4 py-3">账号认证</th>
                <th className="px-4 py-3">连通状态</th>
                <th className="px-4 py-3">延迟 (ms)</th>
                <th className="px-4 py-3">实际出口 IP / 归属地</th>
                <th className="px-4 py-3">最后检测</th>
                <th className="px-4 py-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f1f5f9]">
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-[#94a3b8]">
                    <Loader2 className="mx-auto h-6 w-6 animate-spin text-[#1664ff]" />
                    <span className="mt-2 block text-xs">加载代理池中...</span>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-16 text-center text-[#94a3b8]">
                    <Globe className="mx-auto h-8 w-8 text-[#cbd5e1]" />
                    <p className="mt-2 text-sm font-medium text-[#475569]">暂无符合条件的代理</p>
                    <p className="mt-0.5 text-xs text-[#94a3b8]">
                      点击上方 “批量导入代理” 快速添加代理节点
                    </p>
                  </td>
                </tr>
              ) : (
                filtered.map((p) => {
                  const isChecking = checkingIds.has(p.id)
                  const isSelected = selectedIds.has(p.id)

                  return (
                    <tr
                      key={p.id}
                      className={`transition-colors hover:bg-[#f8fafc] ${isSelected ? 'bg-[#f0f7ff]' : ''}`}
                    >
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelectOne(p.id)}
                          className="rounded border-[#cbd5e1] text-[#1664ff] focus:ring-0 cursor-pointer"
                        />
                      </td>

                      {/* Protocol & Name */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                              p.type === 'socks5'
                                ? 'bg-[#e0e7ff] text-[#4338ca]'
                                : p.type === 'https'
                                ? 'bg-[#dcfce7] text-[#15803d]'
                                : 'bg-[#e2e8f0] text-[#334155]'
                            }`}
                          >
                            {p.type}
                          </span>
                          <span className="font-medium text-[#0f172a]">{p.name || '未命名节点'}</span>
                        </div>
                      </td>

                      {/* Server & Port */}
                      <td className="px-4 py-3 font-mono font-medium text-[#334155]">
                        {p.server}:{p.port || 80}
                      </td>

                      {/* Auth */}
                      <td className="px-4 py-3 text-[#64748b]">
                        {p.username ? (
                          <span className="font-mono text-[11px] bg-[#f1f5f9] px-1.5 py-0.5 rounded border border-[#e2e8f0]">
                            {p.username}
                          </span>
                        ) : (
                          <span className="text-[#94a3b8]">无密码</span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3">
                        {p.status === 'active' ? (
                          <div className="flex items-center gap-1.5 text-[#059669]">
                            <span className="h-2 w-2 rounded-full bg-[#10b981] animate-pulse" />
                            <span className="font-medium">在线可用</span>
                          </div>
                        ) : p.status === 'failed' ? (
                          <div className="flex items-center gap-1.5 text-[#e11d48]">
                            <span className="h-2 w-2 rounded-full bg-[#f43f5e]" />
                            <span className="font-medium">连接失败</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 text-[#94a3b8]">
                            <span className="h-2 w-2 rounded-full bg-[#cbd5e1]" />
                            <span>未检测</span>
                          </div>
                        )}
                      </td>

                      {/* Latency */}
                      <td className="px-4 py-3">
                        {p.latency_ms ? (
                          <span
                            className={`font-mono font-bold ${
                              p.latency_ms < 250
                                ? 'text-[#059669]'
                                : p.latency_ms < 600
                                ? 'text-[#d97706]'
                                : 'text-[#e11d48]'
                            }`}
                          >
                            {p.latency_ms} ms
                          </span>
                        ) : (
                          <span className="text-[#cbd5e1]">-</span>
                        )}
                      </td>

                      {/* Exit IP & Country */}
                      <td className="px-4 py-3">
                        {p.ip ? (
                          <div className="flex items-center gap-1.5 font-mono">
                            <span className="text-[#0f172a]">{p.ip}</span>
                            {p.country && (
                              <span className="rounded bg-[#f1f5f9] px-1 text-[10px] text-[#64748b] border border-[#e2e8f0]">
                                {p.country}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-[#94a3b8] text-[11px]">-</span>
                        )}
                      </td>

                      {/* Last checked */}
                      <td className="px-4 py-3 text-[11px] text-[#94a3b8]">
                        {p.last_checked_at
                          ? new Date(p.last_checked_at).toLocaleTimeString()
                          : '从未'}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleCheckSingle(p)}
                            disabled={isChecking}
                            className="flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium text-[#1664ff] hover:bg-[#e8f3ff] transition disabled:opacity-50 cursor-pointer"
                            title="测速"
                          >
                            <RefreshCw className={`h-3 w-3 ${isChecking ? 'animate-spin' : ''}`} />
                            测速
                          </button>
                          <button
                            onClick={() => handleDelete(p.id)}
                            className="rounded p-1 text-[#94a3b8] hover:bg-[#fee2e2] hover:text-[#ef4444] transition cursor-pointer"
                            title="删除"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Batch Import Modal */}
      <Modal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="批量导入代理服务器"
        subtitle="支持多行粘贴，系统将智能提取 IP、端口及账号密码"
      >
        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-[#334155] block mb-1.5">
              默认协议
            </label>
            <div className="flex gap-2">
              {['socks5', 'http', 'https'].map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setDefaultType(t)}
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold uppercase cursor-pointer transition ${
                    defaultType === t
                      ? 'bg-[#1664ff] text-white shadow-xs'
                      : 'bg-[#f1f5f9] text-[#475569] hover:bg-[#e2e8f0]'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-[#334155] block mb-1.5">
              代理列表 (每行一条)
            </label>
            <textarea
              rows={8}
              value={importContent}
              onChange={(e) => setImportContent(e.target.value)}
              placeholder={`支持以下常用格式：\n127.0.0.1:1080\n192.168.1.100:8080:username:password\nsocks5://admin:pass@45.76.12.3:1080\nhttp://123.45.67.89:3128`}
              className="w-full font-mono text-xs rounded-lg border border-[#cbd5e1] p-3 text-[#0f172a] placeholder-[#94a3b8] focus:border-[#1664ff] focus:outline-none focus:ring-1 focus:ring-[#1664ff]"
            />
            <p className="mt-1.5 text-[11px] text-[#64748b]">
              已输入行数：{importContent.split('\n').filter((l) => l.trim()).length}
            </p>
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
              onClick={handleBatchImport}
              disabled={importing || !importContent.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-[#1664ff] px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#0e52db] disabled:opacity-50 cursor-pointer"
            >
              {importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              开始解析并导入
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
