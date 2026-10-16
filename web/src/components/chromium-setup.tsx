'use client'

import { useCallback, useEffect, useState } from 'react'
import { Check, Download, LoaderCircle, RefreshCw } from 'lucide-react'
import { systemAPI, type BrowserReadiness } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

export function ChromiumSetup() {
  const { isZh } = useI18n()
  const [chromium, setChromium] = useState<BrowserReadiness | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [requesting, setRequesting] = useState(false)

  const load = useCallback(async () => {
    try {
      setChromium(await systemAPI.chromium())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (chromium?.state !== 'downloading') return
    const timer = setInterval(load, 1500)
    return () => clearInterval(timer)
  }, [chromium?.state, load])

  async function install() {
    setRequesting(true)
    setError(null)
    try {
      setChromium(await systemAPI.installChromium())
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setRequesting(false)
    }
  }

  const downloading = requesting || chromium?.state === 'downloading'
  const ready = chromium?.installed && chromium.state !== 'error' && !downloading
  const failure = error || chromium?.error
  const progress = chromium?.progress == null ? null : Math.min(100, Math.max(0, chromium.progress))

  const titleText = ready
    ? (isZh ? 'Chromium 浏览器内核已就绪' : 'Chromium browser is ready')
    : downloading
      ? (isZh ? '正在从云端下载安装 Chromium 内核...' : 'Installing Chromium browser from cloud')
      : (isZh ? 'Chromium 防关联内核未安装' : 'Chromium kernel not installed')

  const descText = ready
    ? (isZh
        ? `已安装内核版本 ${chromium?.version || '155.0.8059 (Anti-detect)'}。深度屏蔽 CDP 指纹特征，基于 GitHub Releases 云端多内核库托管，支持环境终身锁定与极速多开。`
        : `Chromium ${chromium?.version || '155.0'}. Custom anti-detect build with isolated fingerprinting and GitHub Releases multi-kernel repository.`)
    : (isZh
        ? '从 GitHub Releases 云端内核库一键下载 155.0 首发基准防关联 Chromium 原生内核，下载后自动解压就绪。'
        : 'Download the custom anti-detect Chromium build from GitHub Releases kernel repository.')

  return (
    <section aria-label="Chromium kernel setup" className="panel">
      <div className="flex items-start gap-3 p-4">
        <span className={`mt-0.5 shrink-0 ${ready ? 'text-ok' : 'text-signal'}`} aria-hidden="true">
          {downloading ? (
            <LoaderCircle size={19} className="animate-spin motion-reduce:animate-none" />
          ) : ready ? (
            <Check size={19} />
          ) : (
            <Download size={19} />
          )}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold">{titleText}</h2>
          <p className="mt-1 text-ink-dim">{descText}</p>
          <p className="mt-1 text-ink-dim" role="status" aria-live="polite">
            {chromium?.message || (!error && !chromium ? (isZh ? '正在检测内核状态…' : 'Checking Chromium status…') : '')}
          </p>
          {downloading && (
            <div className="mt-3 flex items-center gap-3">
              <progress
                aria-label="Chromium installation progress"
                className="h-2 w-full accent-signal"
                max={100}
                value={progress ?? undefined}
              />
              {progress !== null && <span className="font-mono text-ink-dim">{Math.round(progress)}%</span>}
            </div>
          )}
          {failure && <p className="mt-2 break-words text-danger" role="alert">{failure}</p>}
          {/* 多内核库就绪列表 */}
          <div className="mt-4 rounded border border-line bg-canvas/40 p-3 text-xs">
            <div className="flex items-center justify-between font-medium text-ink">
              <span>{isZh ? '本地内核版本库 (多版本物理隔离)' : 'Local Kernel Repository (Isolated)'}</span>
              <span className="font-mono text-[11px] text-signal">{isZh ? '云端源: GitHub Releases (免费全球CDN+镜像加速)' : 'Cloud: GitHub Releases'}</span>
            </div>
            <div className="mt-2 space-y-1.5 font-mono text-[11px]">
              <div className="flex items-center justify-between rounded bg-canvas-subtle px-2.5 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-ok" />
                  <span className="font-semibold text-ink">Chrome 155.0.8059.39</span>
                  <span className="rounded bg-ok/10 px-1.5 py-0.5 text-[10px] text-ok font-sans font-medium">{isZh ? '首发基准 · 已激活' : 'Active Baseline'}</span>
                </div>
                <span className="text-ink-dim font-sans">{isZh ? '新老环境终身锁定' : 'Profile Locked'}</span>
              </div>
              <div className="flex items-center justify-between rounded bg-canvas-subtle px-2.5 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-ok" />
                  <span className="font-semibold text-ink">Camoufox 135.0-beta.36</span>
                  <span className="rounded bg-ok/10 px-1.5 py-0.5 text-[10px] text-ok font-sans font-medium">{isZh ? 'Gecko 原生 · 已激活' : 'Gecko Native'}</span>
                </div>
                <span className="text-ink-dim font-sans">{isZh ? '桌面真实生态绑定' : 'Desktop Only'}</span>
              </div>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {!ready && (
              <button
                className="btn btn-primary"
                disabled={downloading || (!chromium && !error)}
                onClick={chromium ? install : load}
              >
                {downloading ? (isZh ? '正在从云端下载…' : 'Downloading…') : (isZh ? '从云端一键下载' : 'Download from cloud')}
              </button>
            )}
            {ready && (
              <button className="btn btn-default" disabled={downloading} onClick={install}>
                <RefreshCw size={13} aria-hidden="true" />
                {isZh ? '重新从云端下载' : 'Re-download from cloud'}
              </button>
            )}
            <button className="btn btn-ghost" disabled={downloading} onClick={load}>
              {isZh ? '重新检查' : 'Check again'}
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
