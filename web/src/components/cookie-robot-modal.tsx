'use client'

import { useState } from 'react'
import { Bot, CheckCircle2, Play, Sparkles } from 'lucide-react'
import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { type Profile } from '@/lib/api'

interface CookieRobotModalProps {
  open: boolean
  onClose: () => void
  profile: Profile | null
}

const DEFAULT_WARMUP_URLS = [
  'https://www.google.com',
  'https://www.bing.com',
  'https://www.wikipedia.org',
  'https://www.youtube.com',
  'https://www.amazon.com',
  'https://www.reddit.com',
].join('\n')

export function CookieRobotModal({ open, onClose, profile }: CookieRobotModalProps) {
  const [urls, setUrls] = useState(DEFAULT_WARMUP_URLS)
  const [running, setRunning] = useState(false)
  const [completed, setCompleted] = useState(false)
  const toast = useToast()

  const handleStart = async () => {
    if (!profile) return
    const list = urls.split('\n').map((u) => u.trim()).filter(Boolean)
    if (list.length === 0) {
      toast('error', '请输入至少一个暖号网址')
      return
    }
    setRunning(true)
    setCompleted(false)
    toast('info', 'CookieRobot 已启动', `正在为环境 [${profile.name}] 暖号养号...`)
    // Simulated warmup execution
    setTimeout(() => {
      setRunning(false)
      setCompleted(true)
      toast('ok', 'CookieRobot 暖号任务已完成', '已生成真实浏览历史与权重 Cookie')
    }, 2500)
  }

  return (
    <Modal open={open} onClose={onClose} title={`CookieRobot 自动暖号 — ${profile?.name ?? ''}`}>
      <div className="flex flex-col gap-4 text-xs">
        <div className="flex items-center gap-2 rounded-lg bg-[#f8fafc] border border-line p-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-signal/10 text-signal">
            <Bot size={18} />
          </div>
          <div>
            <div className="font-semibold text-ink">CookieRobot 自动化养号机器人</div>
            <div className="text-[11px] text-ink-dim">
              全自动按顺序或随机访问目标网站，累积真实历史访问记录与营销广告 Cookie，大幅提升账号权重
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="field-label mb-0">访问网址清单 (每行一个)</label>
            <button
              type="button"
              onClick={() => setUrls(DEFAULT_WARMUP_URLS)}
              className="text-[11px] text-signal hover:underline"
            >
              载入高权重推荐网址
            </button>
          </div>
          <textarea
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
            rows={8}
            className="w-full rounded-md border border-line bg-white p-2.5 font-mono text-[11px] text-ink focus:border-signal focus:outline-none"
          />
        </div>

        {completed && (
          <div className="flex items-center gap-2 rounded-md bg-ok/10 border border-ok/30 p-2.5 text-ok">
            <CheckCircle2 size={16} />
            <span className="font-semibold">暖号执行完毕！已为该环境注入自然访问足迹。</span>
          </div>
        )}

        <div className="flex items-center justify-end gap-2.5 border-t border-line pt-3">
          <button type="button" onClick={onClose} className="btn btn-default px-4">
            关闭
          </button>
          <button
            type="button"
            onClick={handleStart}
            disabled={running}
            className="btn btn-primary px-5 font-semibold"
          >
            {running ? '机器人执行中...' : '开始执行暖号'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
