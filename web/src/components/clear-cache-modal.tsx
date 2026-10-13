'use client'

import { useState } from 'react'
import { AlertCircle, Eraser, Trash2 } from 'lucide-react'
import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { profilesAPI, type Profile } from '@/lib/api'

interface ClearCacheModalProps {
  open: boolean
  onClose: () => void
  profile: Profile | null
  onCleared?: () => void
}

export function ClearCacheModal({ open, onClose, profile, onCleared }: ClearCacheModalProps) {
  const [clearCache, setClearCache] = useState(true)
  const [clearCookies, setClearCookies] = useState(false)
  const [clearing, setClearing] = useState(false)
  const toast = useToast()

  const handleClear = async () => {
    if (!profile) return
    setClearing(true)
    try {
      const res = await profilesAPI.clearCache(profile.id, {
        clear_cache: clearCache,
        clear_cookies: clearCookies,
      })
      toast('ok', `缓存清理完成`, res.cleared_items.join(', ') || '已释放空间')
      if (onCleared) onCleared()
      onClose()
    } catch (err) {
      toast('error', '清理失败', String(err))
    } finally {
      setClearing(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={`清除缓存 — ${profile?.name ?? ''}`}>
      <div className="flex flex-col gap-4 text-xs">
        <div className="flex items-center gap-2 rounded-lg bg-[#f8fafc] border border-line p-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-warn/15 text-warn">
            <Eraser size={18} />
          </div>
          <div>
            <div className="font-semibold text-ink">环境磁盘与数据深度清理</div>
            <div className="text-[11px] text-ink-dim">
              清理网页缓存临时文件以释放磁盘空间并提升启动速度，保留指纹硬件与网络设置
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-2.5 rounded-lg border border-line p-3">
          <label className="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={clearCache}
              onChange={(e) => setClearCache(e.target.checked)}
              className="h-4 w-4 rounded border-line text-signal focus:ring-signal"
            />
            <div>
              <div className="font-semibold text-ink">清理浏览器网页缓存 (推荐)</div>
              <div className="text-[11px] text-ink-dim">
                删除磁盘 Cache、GPUCache、代码缓存，不影响登录状态
              </div>
            </div>
          </label>

          <label className="flex items-center gap-2.5 cursor-pointer border-t border-line/60 pt-2.5">
            <input
              type="checkbox"
              checked={clearCookies}
              onChange={(e) => setClearCookies(e.target.checked)}
              className="h-4 w-4 rounded border-line text-signal focus:ring-signal"
            />
            <div>
              <div className="font-semibold text-ink">清理 Cookie 与登录会话 (慎选)</div>
              <div className="text-[11px] text-ink-dim">
                将清除网站已登录的 Cookie，下次打开需重新登录
              </div>
            </div>
          </label>
        </div>

        <div className="flex items-center gap-1.5 text-[11px] text-ink-dim">
          <AlertCircle size={13} className="text-warn shrink-0" />
          <span>建议在环境已关闭时执行清理，清理后可有效防止网站缓存追踪。</span>
        </div>

        <div className="flex items-center justify-end gap-2.5 border-t border-line pt-3">
          <button type="button" onClick={onClose} className="btn btn-default px-4">
            取消
          </button>
          <button
            type="button"
            onClick={handleClear}
            disabled={clearing || (!clearCache && !clearCookies)}
            className="btn btn-primary px-5 font-semibold"
          >
            {clearing ? '清理中...' : '确认清理'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
