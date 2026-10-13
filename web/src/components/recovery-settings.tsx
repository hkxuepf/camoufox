'use client'

import { useCallback, useEffect, useState } from 'react'
import { Archive, Download, ExternalLink, LoaderCircle, RotateCcw } from 'lucide-react'
import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { useI18n } from '@/lib/i18n'
import { recoveryAPI, systemAPI, type AppUpdate, type BackupInfo } from '@/lib/api'

function message(error: unknown): string { return error instanceof Error ? error.message : String(error) }

/** The download is exposed only after the server has completed its backup. */
export function UpdateSettings() {
  const { isZh } = useI18n()
  const [update, setUpdate] = useState<AppUpdate | null>(null)
  const [checking, setChecking] = useState(false)
  const [preparing, setPreparing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [prepared, setPrepared] = useState<{ url: string; count: number; message: string } | null>(null)

  async function check() {
    setChecking(true); setError(null); setPrepared(null)
    try {
      const result = await systemAPI.updates()
      setUpdate(result)
      if (result.error) setError(result.error)
    } catch (err) { setError(message(err)) }
    finally { setChecking(false) }
  }
  async function prepare() {
    setPreparing(true); setError(null)
    try {
      const result = await systemAPI.prepareUpdate()
      if (!isReleaseLink(result.release_url)) throw new Error(isZh ? '服务器返回了未经校验的发布链接。请重新检查更新。' : 'The server returned an unverified release link. Check for updates again.')
      setPrepared({ url: result.release_url, count: result.backup_count, message: result.message })
      window.dispatchEvent(new Event('camoufox-backups-changed'))
    } catch (err) { setError(message(err)) }
    finally { setPreparing(false) }
  }

  return <section aria-labelledby="updates-title">
    <h2 id="updates-title" className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">{isZh ? '应用更新' : 'App updates'}</h2>
    <div className="panel p-4">
      <p className="font-medium">{isZh ? '检测桌面客户端新版本' : 'Check for a new desktop release'}</p>
      <p className="mt-1 text-ink-dim">{isZh ? '更新前请先关闭所有运行中的环境。我们会在提供新版本下载前自动为每个环境创建数据备份。下载后安装新版本即可完成升级。' : 'Close all running profiles before updating. We create a backup of every profile before making the release download available. Install the downloaded release to update the app.'}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button className="btn btn-default" disabled={checking || preparing} onClick={check}>{checking && <LoaderCircle size={13} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />}{checking ? (isZh ? '检查中…' : 'Checking…') : (isZh ? '检查更新' : 'Check for updates')}</button>
        {update?.available && !prepared && !error && <button className="btn btn-primary" disabled={preparing || checking} onClick={prepare}><Archive size={13} aria-hidden="true" />{preparing ? (isZh ? '正在创建备份…' : 'Creating backups…') : (isZh ? '备份并准备更新' : 'Back up and prepare update')}</button>}
      </div>
      {update && !error && <p className="mt-3 text-ink-dim" role="status">{update.available ? (isZh ? `发现新版本 ${update.latest_version}（当前安装版本：${update.current_version}）。` : `Version ${update.latest_version} is available. You have ${update.current_version}.`) : (isZh ? `当前已是最新版本 (${update.current_version})。` : `You are up to date (${update.current_version}).`)}</p>}
      {error && <p className="mt-3 text-danger" role="alert">{error}</p>}
      {prepared && <div className="mt-3 rounded-md border border-line bg-raised p-3">
        <p role="status">{prepared.message || (isZh ? `已完成 ${prepared.count} 个环境的备份。新版本安装包已就绪。` : `${prepared.count} profile backups created. Your release is ready to download.`)}</p>
        <a className="btn btn-primary mt-3" href={prepared.url} target="_blank" rel="noopener noreferrer"><Download size={13} aria-hidden="true" />{isZh ? '打开发布下载页面' : 'Open release downloads'}<ExternalLink size={12} aria-hidden="true" /></a>
        <p className="mt-2 text-ink-dim">{isZh ? '下载对应您操作系统的安装包。更新完成后备份依然保留在系统设置中。' : 'Download the asset for your operating system. Backups remain in Settings after the update.'}</p>
      </div>}
    </div>
  </section>
}

/** The server verifies the repository; the UI also rejects non-release and unsafe links. */
function isReleaseLink(url: string): boolean {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' && parsed.hostname === 'github.com' && /^\/polyackiy\/camoufox-profile-manager\/releases\/tag\/[^/]+\/?$/.test(parsed.pathname) && !parsed.username && !parsed.password
  } catch { return false }
}

export function BackupSettings() {
  const { isZh } = useI18n()
  const [backups, setBackups] = useState<BackupInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)
  const [restore, setRestore] = useState<BackupInfo | null>(null)
  const toast = useToast()
  const load = useCallback(async () => {
    try { setBackups(await recoveryAPI.backups()); setError(null) }
    catch (err) { setError(message(err)) }
    finally { setLoading(false) }
  }, [])
  useEffect(() => {
    // The request completes asynchronously; this effect starts the initial API read.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load()
    window.addEventListener('camoufox-backups-changed', load)
    return () => window.removeEventListener('camoufox-backups-changed', load)
  }, [load])
  async function create() {
    setBusy(true); setError(null); setResult(null)
    try {
      const response = await recoveryAPI.createBackup()
      await load()
      setResult(isZh ? `已成功创建 ${response.backups.length} 个环境备份。${response.skipped.length ? ` 跳过 ${response.skipped.length} 个环境: ${response.skipped.map(item => `${item.profile_id}: ${item.reason}`).join('; ')}` : ''}` : `${response.backups.length} backups created.${response.skipped.length ? ` ${response.skipped.length} profiles skipped: ${response.skipped.map(item => `${item.profile_id}: ${item.reason}`).join('; ')}` : ''}`)
    } catch (err) { setError(message(err)) }
    finally { setBusy(false) }
  }
  async function restoreBackup() {
    if (!restore || busy) return
    setBusy(true); setError(null)
    try {
      const profile = await recoveryAPI.restoreBackup(restore.id)
      toast('ok', isZh ? '备份已恢复为全新环境' : 'Backup restored as a new profile', isZh ? `"${profile.name}" 已添加至环境列表。` : `${profile.name} is available in Profiles.`)
      setRestore(null)
    } catch (err) { setError(message(err)); setRestore(null) }
    finally { setBusy(false) }
  }

  return <section aria-labelledby="backups-title">
    <h2 id="backups-title" className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-faint">{isZh ? '环境备份' : 'Profile backups'}</h2>
    <div className="panel overflow-hidden">
      <div className="p-4">
        <p className="text-ink-dim">{isZh ? '备份包含环境配置和全部浏览器本地缓存。备份前请先关闭运行中的环境；运行中的环境将被跳过。恢复备份时会生成一个全新 ID 的环境，并保留原有环境。' : 'Backups include profile settings and browser data. Close running profiles before backing up; running profiles are skipped. Restoring creates a new profile with a new ID and preserves the current profile.'}</p>
        <p className="mt-2 text-ink-dim">{isZh ? '备份数据未加密，可能包含已登录的会话 Cookie 和代理密码，请妥善保管备份文件。' : 'Backups are not encrypted. They can contain signed-in sessions and proxy passwords; keep them private.'}</p>
        <div className="mt-3 flex gap-2">
          <button className="btn btn-default" disabled={busy || loading} onClick={create}><Archive size={13} aria-hidden="true" />{busy ? (isZh ? '处理中…' : 'Working…') : (isZh ? '备份所有环境' : 'Back up profiles')}</button>
          <button className="btn btn-ghost" disabled={busy} onClick={load}>{isZh ? '刷新' : 'Refresh'}</button>
        </div>
        {result && <p className="mt-3 break-words text-ink-dim" role="status">{result}</p>}
        {error && <p className="mt-3 break-words text-danger" role="alert">{error}</p>}
      </div>
      {loading ? <p className="border-t border-line px-4 py-3 text-ink-dim" role="status">{isZh ? '正在加载备份…' : 'Loading backups…'}</p> : backups.length === 0 ? <p className="border-t border-line px-4 py-3 text-ink-dim">{isZh ? '暂无备份记录。' : 'No backups yet.'}</p> :
        <ul className="max-h-[360px] divide-y divide-line overflow-y-auto border-t border-line">{backups.map(backup => <li key={backup.id} className="flex items-center gap-3 px-4 py-3">
          <div className="min-w-0 flex-1"><p className="break-words font-medium">{backup.profile_name}</p><p className="text-ink-dim">{new Date(backup.created_at).toLocaleString()} · {Math.max(1, Math.round(backup.size_bytes / 1024))} KB · {backup.reason}</p></div>
          <button className="btn btn-default shrink-0" disabled={busy} onClick={() => setRestore(backup)} aria-label={`Restore backup of ${backup.profile_name} from ${new Date(backup.created_at).toLocaleString()}`}><RotateCcw size={13} aria-hidden="true" />{isZh ? '恢复' : 'Restore'}</button>
        </li>)}</ul>}
    </div>
    <Modal open={!!restore} title={isZh ? '将备份恢复为新环境' : 'Restore backup as a new profile'} onClose={() => { if (!busy) setRestore(null) }} width={460} footer={<>
      <button className="btn btn-default" disabled={busy} onClick={() => setRestore(null)}>{isZh ? '取消' : 'Cancel'}</button>
      <button className="btn btn-primary" disabled={busy} onClick={restoreBackup}>{busy ? (isZh ? '正在恢复…' : 'Restoring…') : (isZh ? '恢复为新环境' : 'Restore as new profile')}</button>
    </>}><p className="text-ink-dim">{isZh ? <>确认将 <strong className="text-ink">{restore?.profile_name}</strong>（备份时间：{restore && new Date(restore.created_at).toLocaleString()}）恢复吗？系统将创建一个独立的全新环境，导入其已保存的 Cookie、本地缓存与指纹特征。现有环境及本备份文件均会被完整保留。</> : <>Restore <strong className="text-ink">{restore?.profile_name}</strong> from {restore && new Date(restore.created_at).toLocaleString()}? A separate profile with its saved cookies, storage and fingerprint will be created. Your current profiles and this backup are preserved.</>}</p></Modal>
  </section>
}
