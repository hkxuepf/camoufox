'use client'

import { useEffect, useState } from 'react'
import {
  Layers,
  Globe,
  Keyboard,
  ArrowDown,
  ArrowUp,
  RotateCw,
  MousePointer,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Monitor,
  Sparkles,
} from 'lucide-react'
import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { windowManagerAPI } from '@/lib/api'

interface SynchronizerModalProps {
  open: boolean
  onClose: () => void
}

interface ActiveSession {
  profile_id: string
  profile_name: string
  browser_type: string
  cdp_port?: number
  pid?: number
  started_at?: string
}

export function SynchronizerModal({ open, onClose }: SynchronizerModalProps) {
  const [sessions, setSessions] = useState<ActiveSession[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [broadcasting, setBroadcasting] = useState(false)

  // Actions state
  const [navUrl, setNavUrl] = useState('https://browserleaks.com/ip')
  const [inputText, setInputText] = useState('')
  const [inputSelector, setInputSelector] = useState('')
  const [clickSelector, setClickSelector] = useState('')
  const [tileCols, setTileCols] = useState<number>(0)
  const [logs, setLogs] = useState<Array<{ time: string; action: string; msg: string; type: 'info' | 'success' | 'error' }>>([])

  const toast = useToast()

  const loadActiveWindows = async () => {
    try {
      setLoading(true)
      const res = await windowManagerAPI.active()
      const list = res.sessions || []
      setSessions(list)
      // Auto-select all by default if not set
      setSelectedIds(list.map((s: ActiveSession) => s.profile_id))
    } catch (err: any) {
      toast('error', '获取活跃窗口失败', err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) {
      loadActiveWindows()
    }
  }, [open])

  const addLog = (action: string, msg: string, type: 'info' | 'success' | 'error' = 'info') => {
    const time = new Date().toLocaleTimeString()
    setLogs((prev) => [{ time, action, msg, type }, ...prev.slice(0, 49)])
  }

  const toggleSelectAll = () => {
    if (selectedIds.length === sessions.length) {
      setSelectedIds([])
    } else {
      setSelectedIds(sessions.map((s) => s.profile_id))
    }
  }

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    )
  }

  // Action: Tile
  const handleTile = async () => {
    try {
      addLog('平铺', `开始平铺排列窗口 (列数: ${tileCols || '自动'})...`, 'info')
      const res = await windowManagerAPI.tile({ cols: tileCols > 0 ? tileCols : undefined })
      if (res.success && res.windows_count > 0) {
        toast('ok', `已平铺排列 ${res.windows_count} 个浏览器窗口`)
        addLog('平铺', `成功平铺 ${res.windows_count} 个窗口`, 'success')
      } else {
        toast('info', res.message || '未检测到可平铺的浏览器窗口')
        addLog('平铺', res.message || '未检测到窗口', 'error')
      }
    } catch (err: any) {
      toast('error', '平铺窗口失败', err.message)
      addLog('平铺', `失败: ${err.message}`, 'error')
    }
  }

  // Action: Broadcast
  const handleBroadcast = async (action: string, payload: Record<string, any> = {}) => {
    if (selectedIds.length === 0) {
      toast('error', '请先选择需要同步的目标窗口')
      return
    }

    try {
      setBroadcasting(true)
      addLog(action, `广播指令到 ${selectedIds.length} 个窗口...`, 'info')
      const res = await windowManagerAPI.broadcast(action, payload, selectedIds)
      
      const successCount = res.results.filter((r: any) => !r.status.includes('error') && r.status !== 'skipped').length
      addLog(
        action,
        `执行完成: 成功 ${successCount}/${selectedIds.length}`,
        successCount === selectedIds.length ? 'success' : 'error'
      )
      toast('ok', `群控同步指令已发送 (${successCount}/${selectedIds.length})`)
    } catch (err: any) {
      toast('error', '广播指令失败', err.message)
      addLog(action, `执行失败: ${err.message}`, 'error')
    } finally {
      setBroadcasting(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="窗口群控同步器 (Synchronizer)"
      width={760}
    >
      <div className="space-y-4 text-xs text-[#334155]">
        {/* Top summary & reload */}
        <div className="flex items-center justify-between border-b border-[#eaedf1] pb-3">
          <div className="flex items-center gap-2">
            <Monitor size={16} className="text-[#1664ff]" />
            <span className="font-semibold text-sm text-[#1e293b]">活跃浏览器窗口</span>
            <span className="rounded-full bg-[#e8f3ff] px-2 py-0.5 text-xs font-medium text-[#1664ff]">
              {sessions.length} 个运行中
            </span>
            <span className="rounded-full bg-[#f1f5f9] px-2 py-0.5 text-xs text-[#64748b]">
              已勾选 {selectedIds.length} 个
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadActiveWindows}
              disabled={loading}
              className="flex items-center gap-1 rounded border border-[#eaedf1] bg-white px-2.5 py-1 text-xs text-[#475569] hover:bg-[#f8fafc] disabled:opacity-50"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
              刷新列表
            </button>
          </div>
        </div>

        {/* Two-column layout: Left session selector, Right Action Panel */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
          {/* Left: Window select list */}
          <div className="md:col-span-5 border border-[#eaedf1] rounded-lg p-3 bg-[#fafbfc] flex flex-col h-[400px]">
            <div className="flex items-center justify-between pb-2 border-b border-[#eaedf1]">
              <label className="flex items-center gap-2 cursor-pointer font-medium text-[#334155]">
                <input
                  type="checkbox"
                  checked={sessions.length > 0 && selectedIds.length === sessions.length}
                  onChange={toggleSelectAll}
                  className="rounded border-[#cbd5e1] text-[#1664ff] focus:ring-0"
                />
                全选窗口
              </label>
              <span className="text-[11px] text-[#94a3b8]">CDP 调试端口同步</span>
            </div>

            <div className="flex-1 overflow-y-auto mt-2 space-y-1.5 pr-1">
              {sessions.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center py-8 text-[#94a3b8]">
                  <Monitor size={32} className="mb-2 opacity-40" />
                  <p className="text-xs">当前没有运行中的浏览器窗口</p>
                  <p className="text-[11px] text-[#cbd5e1] mt-1">请先在主列表启动环境</p>
                </div>
              ) : (
                sessions.map((s) => {
                  const isChecked = selectedIds.includes(s.profile_id)
                  return (
                    <div
                      key={s.profile_id}
                      onClick={() => toggleSelect(s.profile_id)}
                      className={`flex items-center justify-between p-2 rounded border cursor-pointer transition-all ${
                        isChecked
                          ? 'border-[#1664ff] bg-[#f0f7ff]'
                          : 'border-[#eaedf1] bg-white hover:border-[#cbd5e1]'
                      }`}
                    >
                      <div className="flex items-center gap-2 overflow-hidden">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}} // handled by parent div
                          className="rounded border-[#cbd5e1] text-[#1664ff] focus:ring-0"
                        />
                        <div className="truncate">
                          <div className="font-medium text-[#1e293b] truncate text-xs">
                            {s.profile_name}
                          </div>
                          <div className="text-[10px] text-[#64748b] flex items-center gap-1.5">
                            <span className="capitalize">{s.browser_type || 'Chromium'}</span>
                            {s.cdp_port && <span>• 端口 {s.cdp_port}</span>}
                          </div>
                        </div>
                      </div>
                      <span className="flex h-2 w-2 rounded-full bg-emerald-500" />
                    </div>
                  )
                })
              )}
            </div>
          </div>

          {/* Right: Actions & Tools */}
          <div className="md:col-span-7 flex flex-col h-[400px] space-y-3 overflow-y-auto pr-1">
            {/* Tile Section */}
            <div className="rounded-lg border border-[#eaedf1] p-3 bg-white space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium text-[#1e293b] flex items-center gap-1.5">
                  <Layers size={14} className="text-[#1664ff]" />
                  一键九宫格平铺 (Tile Windows)
                </span>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-[#64748b]">排列布局:</span>
                  <select
                    value={tileCols}
                    onChange={(e) => setTileCols(Number(e.target.value))}
                    className="rounded border border-[#eaedf1] px-2 py-0.5 text-xs bg-white"
                  >
                    <option value={0}>智能自适应</option>
                    <option value={2}>2 列并排</option>
                    <option value={3}>3 列网格</option>
                    <option value={4}>4 列宽屏</option>
                  </select>
                </div>
              </div>
              <button
                onClick={handleTile}
                className="w-full flex items-center justify-center gap-1.5 rounded bg-[#f0f7ff] text-[#1664ff] border border-[#bae0ff] py-1.5 font-medium hover:bg-[#e1effe] transition-colors"
              >
                <Layers size={13} />
                排列所有运行窗口到桌面
              </button>
            </div>

            {/* Broadcast URL Section */}
            <div className="rounded-lg border border-[#eaedf1] p-3 bg-white space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium text-[#1e293b] flex items-center gap-1.5">
                  <Globe size={14} className="text-emerald-600" />
                  统一网址导航 (Broadcast URL)
                </span>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={navUrl}
                  onChange={(e) => setNavUrl(e.target.value)}
                  placeholder="https://..."
                  className="flex-1 rounded border border-[#eaedf1] px-2.5 py-1 text-xs focus:border-[#1664ff] focus:outline-none"
                />
                <button
                  onClick={() => handleBroadcast('navigate', { url: navUrl })}
                  disabled={broadcasting || !navUrl.trim()}
                  className="rounded bg-[#1664ff] px-3 py-1 font-medium text-white hover:bg-[#0e50d7] disabled:opacity-50 transition-colors whitespace-nowrap"
                >
                  全开跳转
                </button>
              </div>
              {/* Quick links */}
              <div className="flex flex-wrap gap-1.5 pt-0.5">
                {[
                  { name: 'BrowserLeaks IP', url: 'https://browserleaks.com/ip' },
                  { name: 'CreepJS 指纹', url: 'https://abrahamjuliot.github.io/creepjs/' },
                  { name: 'Google', url: 'https://www.google.com' },
                  { name: 'X / Twitter', url: 'https://x.com' },
                ].map((item) => (
                  <button
                    key={item.name}
                    onClick={() => {
                      setNavUrl(item.url)
                      handleBroadcast('navigate', { url: item.url })
                    }}
                    className="rounded bg-[#f1f5f9] px-2 py-0.5 text-[11px] text-[#475569] hover:bg-[#e2e8f0]"
                  >
                    {item.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Humanized Input Section */}
            <div className="rounded-lg border border-[#eaedf1] p-3 bg-white space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium text-[#1e293b] flex items-center gap-1.5">
                  <Keyboard size={14} className="text-[#7928ca]" />
                  统一拟人化输入 (Humanized Typing)
                </span>
                <span className="text-[10px] text-[#94a3b8] flex items-center gap-1">
                  <Sparkles size={11} className="text-amber-500" />
                  随机输入时延防风控
                </span>
              </div>
              <div className="space-y-1.5">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="需要输入的文本内容..."
                  className="w-full rounded border border-[#eaedf1] px-2.5 py-1 text-xs focus:border-[#1664ff] focus:outline-none"
                />
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputSelector}
                    onChange={(e) => setInputSelector(e.target.value)}
                    placeholder="目标 CSS 选择器 (留空则输入到当前焦点元素)"
                    className="flex-1 rounded border border-[#eaedf1] px-2 py-0.5 text-[11px] focus:border-[#1664ff] focus:outline-none"
                  />
                  <button
                    onClick={() => handleBroadcast('input', { text: inputText, selector: inputSelector })}
                    disabled={broadcasting || !inputText}
                    className="rounded bg-[#7928ca] px-3 py-1 font-medium text-white hover:bg-[#631bb5] disabled:opacity-50 transition-colors whitespace-nowrap"
                  >
                    同步输入
                  </button>
                </div>
              </div>
            </div>

            {/* Quick Actions: Scroll, Reload, Click */}
            <div className="rounded-lg border border-[#eaedf1] p-3 bg-white space-y-2">
              <span className="font-medium text-[#1e293b] block">快速动作指令</span>
              <div className="grid grid-cols-4 gap-2">
                <button
                  onClick={() => handleBroadcast('scroll', { delta_y: 400 })}
                  disabled={broadcasting}
                  className="flex items-center justify-center gap-1 rounded border border-[#eaedf1] bg-[#f8fafc] py-1 text-xs text-[#334155] hover:bg-[#f1f5f9]"
                >
                  <ArrowDown size={12} />
                  向下翻屏
                </button>
                <button
                  onClick={() => handleBroadcast('scroll', { delta_y: -400 })}
                  disabled={broadcasting}
                  className="flex items-center justify-center gap-1 rounded border border-[#eaedf1] bg-[#f8fafc] py-1 text-xs text-[#334155] hover:bg-[#f1f5f9]"
                >
                  <ArrowUp size={12} />
                  向上翻屏
                </button>
                <button
                  onClick={() => handleBroadcast('reload')}
                  disabled={broadcasting}
                  className="flex items-center justify-center gap-1 rounded border border-[#eaedf1] bg-[#f8fafc] py-1 text-xs text-[#334155] hover:bg-[#f1f5f9]"
                >
                  <RotateCw size={12} />
                  全部刷新
                </button>
                <button
                  onClick={() => {
                    const sel = prompt('请输入要点击的元素 CSS 选择器:', 'button[type="submit"]')
                    if (sel) handleBroadcast('click', { selector: sel })
                  }}
                  disabled={broadcasting}
                  className="flex items-center justify-center gap-1 rounded border border-[#eaedf1] bg-[#f8fafc] py-1 text-xs text-[#334155] hover:bg-[#f1f5f9]"
                >
                  <MousePointer size={12} />
                  模拟点击
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Execution Logs */}
        <div className="rounded-lg border border-[#eaedf1] bg-[#1e293b] text-[#f8fafc] p-2.5 max-h-32 overflow-y-auto font-mono text-[11px] space-y-1">
          <div className="flex items-center justify-between text-[#94a3b8] text-[10px] pb-1 border-b border-[#334155]">
            <span>同步器操作记录</span>
            <span>{logs.length} 条</span>
          </div>
          {logs.length === 0 ? (
            <div className="text-[#64748b] py-1">等待操作指令...</div>
          ) : (
            logs.map((log, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="text-[#64748b]">{log.time}</span>
                <span
                  className={`px-1 rounded text-[10px] ${
                    log.type === 'success'
                      ? 'bg-emerald-950 text-emerald-400'
                      : log.type === 'error'
                      ? 'bg-rose-950 text-rose-400'
                      : 'bg-blue-950 text-blue-400'
                  }`}
                >
                  [{log.action}]
                </span>
                <span className="text-[#cbd5e1] truncate">{log.msg}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </Modal>
  )
}
