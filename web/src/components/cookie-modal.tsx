'use client'

import { useEffect, useState } from 'react'
import { Check, Cookie, Copy, Download, Trash2, Upload, FileCode } from 'lucide-react'
import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { profilesAPI, type Profile } from '@/lib/api'

interface CookieModalProps {
  open: boolean
  onClose: () => void
  profile: Profile | null
  onSaved?: () => void
}

export function CookieModal({ open, onClose, profile, onSaved }: CookieModalProps) {
  const [cookieText, setCookieText] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [parsedCount, setParsedCount] = useState<number | null>(null)
  const toast = useToast()

  useEffect(() => {
    if (open && profile) {
      setLoading(true)
      profilesAPI
        .getCookies(profile.id)
        .then((res) => {
          const val = res.cookies || profile.cookies || ''
          setCookieText(val)
          calcCount(val)
        })
        .catch(() => {
          setCookieText(profile.cookies || '')
          calcCount(profile.cookies || '')
        })
        .finally(() => setLoading(false))
    } else {
      setCookieText('')
      setParsedCount(null)
    }
  }, [open, profile])

  const calcCount = (text: string) => {
    if (!text.trim()) {
      setParsedCount(0)
      return
    }
    try {
      const parsed = JSON.parse(text)
      if (Array.isArray(parsed)) {
        setParsedCount(parsed.length)
        return
      }
    } catch {
      // Netscape or line-delimited or semicolon-separated
      const lines = text.split('\n').filter((l) => l.trim() && !l.trim().startsWith('#'))
      if (lines.length > 1) {
        setParsedCount(lines.length)
        return
      }
      const pairs = text.split(';').filter((p) => p.trim())
      setParsedCount(pairs.length)
    }
  }

  const handleChange = (val: string) => {
    setCookieText(val)
    calcCount(val)
  }

  const handleFormatJson = () => {
    try {
      const parsed = JSON.parse(cookieText)
      setCookieText(JSON.stringify(parsed, null, 2))
      toast('ok', 'JSON 已格式化')
    } catch {
      toast('error', '当前内容非标准 JSON 格式')
    }
  }

  const handleCopy = async () => {
    if (!cookieText) {
      toast('error', 'Cookie 为空')
      return
    }
    try {
      await navigator.clipboard.writeText(cookieText)
      toast('ok', '已复制 Cookie 到剪贴板')
    } catch {
      toast('error', '复制失败，请手动选择复制')
    }
  }

  const handleDownload = () => {
    if (!cookieText) {
      toast('error', '没有可导出的 Cookie')
      return
    }
    const blob = new Blob([cookieText], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `cookies_${profile?.name || 'profile'}_${profile?.id}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast('ok', '已导出 Cookie 文件')
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (evt) => {
      const content = evt.target?.result as string
      if (content) {
        setCookieText(content)
        calcCount(content)
        toast('ok', `已载入 ${file.name}`)
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const handleSave = async () => {
    if (!profile) return
    setSaving(true)
    try {
      await profilesAPI.updateCookies(profile.id, cookieText)
      toast('ok', 'Cookie 已更新并保存')
      if (onSaved) onSaved()
      onClose()
    } catch (err) {
      toast('error', '保存失败', String(err))
    } finally {
      setSaving(false)
    }
  }

  const handleClear = async () => {
    if (!profile) return
    if (confirm('确认清空此环境的所有 Cookie 吗？')) {
      try {
        await profilesAPI.clearCookies(profile.id)
        setCookieText('')
        setParsedCount(0)
        toast('ok', 'Cookie 已清空')
        if (onSaved) onSaved()
      } catch (err) {
        toast('error', '清空失败', String(err))
      }
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={`编辑 Cookie — ${profile?.name ?? ''}`}>
      <div className="flex flex-col gap-4 text-xs">
        <div className="flex items-center justify-between rounded-lg bg-[#f8fafc] border border-line p-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-signal/10 text-signal">
              <Cookie size={18} />
            </div>
            <div>
              <div className="font-semibold text-ink">Cookie 数据管理与注入</div>
              <div className="text-[11px] text-ink-dim">
                支持标准 JSON 数组、Netscape 或 Key=Value 格式，环境启动时将自动注入
              </div>
            </div>
          </div>
          {parsedCount !== null && (
            <div className="flex items-center gap-1.5 rounded-full bg-signal/10 px-3 py-1 font-mono text-[11px] font-semibold text-signal">
              <span>{parsedCount} 条 Cookie</span>
            </div>
          )}
        </div>

        {/* Toolbar */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <label className="btn btn-default text-xs h-7 px-2.5 cursor-pointer">
              <Upload size={13} />
              <span>导入文件</span>
              <input type="file" accept=".json,.txt" className="hidden" onChange={handleFileUpload} />
            </label>
            <button type="button" onClick={handleCopy} className="btn btn-default text-xs h-7 px-2.5">
              <Copy size={13} />
              <span>复制</span>
            </button>
            <button type="button" onClick={handleDownload} className="btn btn-default text-xs h-7 px-2.5">
              <Download size={13} />
              <span>导出 JSON</span>
            </button>
            <button type="button" onClick={handleFormatJson} className="btn btn-default text-xs h-7 px-2.5">
              <FileCode size={13} />
              <span>格式化</span>
            </button>
          </div>
          <button
            type="button"
            onClick={handleClear}
            className="btn text-danger hover:bg-danger/10 text-xs h-7 px-2"
            title="清空当前 Cookie"
          >
            <Trash2 size={13} />
            <span>清空</span>
          </button>
        </div>

        {/* Text Area */}
        <div className="relative">
          <textarea
            value={cookieText}
            onChange={(e) => handleChange(e.target.value)}
            placeholder={`在此粘贴 Cookie 数据...\n例如 JSON 格式:\n[\n  {\n    "name": "session_id",\n    "value": "xyz123",\n    "domain": ".example.com",\n    "path": "/"\n  }\n]\n或 Netscape / name=value 键值对`}
            rows={13}
            disabled={loading}
            className="w-full rounded-md border border-line bg-white p-3 font-mono text-[11px] text-ink placeholder:text-ink-faint focus:border-signal focus:outline-none focus:ring-1 focus:ring-signal"
          />
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/70 backdrop-blur-xs">
              <span className="text-xs text-ink-dim">正在加载 Cookie 数据...</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2.5 border-t border-line pt-3">
          <button type="button" onClick={onClose} className="btn btn-default px-4">
            取消
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || loading}
            className="btn btn-primary px-5 font-semibold"
          >
            {saving ? '保存中...' : '保存并同步'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
