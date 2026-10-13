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
        ? `已安装内核版本 ${chromium?.version || '154.0 (Anti-detect)'}。深度屏蔽 CDP 指纹特征，支持极速多开与隔离。`
        : `Chromium ${chromium?.version || 'installed'}. Custom anti-detect build with isolated fingerprinting.`)
    : (isZh
        ? '从云端一键下载 154.0 定制版防关联 Chromium 内核 (约 167MB)，下载后自动解压就绪。'
        : 'Download the custom anti-detect Chromium build from cloud storage directly.')

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
