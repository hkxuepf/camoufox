'use client'

import { useCallback, useEffect, useState } from 'react'
import { LoaderCircle, RotateCcw, Trash2 } from 'lucide-react'
import { EmptyState } from '@/components/empty-state'
import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { useI18n } from '@/lib/i18n'
import { recoveryAPI, type Profile } from '@/lib/api'

type TrashedProfile = Profile & { deleted_at: string }

export default function TrashPage() {
  const { t, isZh } = useI18n()
  const [profiles, setProfiles] = useState<TrashedProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<TrashedProfile | null>(null)
  const [confirmation, setConfirmation] = useState('')
  const toast = useToast()
  const load = useCallback(async () => {
    try {
      setProfiles(await recoveryAPI.trash())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => {
    // The initial API request resolves asynchronously.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load()
  }, [load])

  async function restore(profile: TrashedProfile) {
    setBusy(profile.id)
    try {
      await recoveryAPI.restoreProfile(profile.id)
      toast('ok', isZh ? '环境已恢复' : 'Profile restored', isZh ? `"${profile.name}" 已恢复至环境列表。` : `${profile.name} is available in Profiles.`)
      await load()
    } catch (err) {
      toast('error', isZh ? '无法恢复环境' : 'Could not restore profile', err instanceof Error ? err.message : String(err))
    } finally { setBusy(null) }
  }

  async function remove() {
    if (!deleting || confirmation !== deleting.name || busy) return
    setBusy(deleting.id)
    try {
      await recoveryAPI.permanentlyDelete(deleting.id)
      toast('ok', isZh ? '环境已彻底删除' : 'Profile permanently deleted', deleting.name)
      setDeleting(null)
      setConfirmation('')
      await load()
    } catch (err) {
      toast('error', isZh ? '无法删除环境' : 'Could not delete profile', err instanceof Error ? err.message : String(err))
    } finally { setBusy(null) }
  }

  return <>
    <header className="sticky top-0 z-20 flex h-[52px] items-center gap-3 border-b border-line bg-canvas/85 px-5 backdrop-blur">
      <h1 className="text-[14px] font-semibold">{t('nav.trash', 'Trash')}</h1><span className="font-mono text-ink-faint">{profiles.length}</span>
      <button className="btn btn-default ml-auto" onClick={load} disabled={loading || !!busy}>{isZh ? '刷新' : 'Refresh'}</button>
    </header>
    <p className="px-5 py-4 text-ink-dim">{isZh ? '移入回收站的环境将保留其 Cookie、本地存储和指纹数据。您可以随时将其恢复至环境列表，或永久删除其全部数据。' : 'Profiles in Trash keep their cookies, storage and fingerprint. Restore a profile to use it again, or permanently delete its data.'}</p>
    {error ? <EmptyState icon={<Trash2 size={18} />} title={isZh ? '无法加载回收站' : 'Cannot load Trash'} body={error} action={<button className="btn btn-default" onClick={load}>{isZh ? '重试' : 'Retry'}</button>} /> : loading ? <p className="px-5 py-8 text-ink-dim" role="status">{isZh ? '正在加载…' : 'Loading…'}</p> : profiles.length === 0 ? <EmptyState icon={<Trash2 size={18} />} title={isZh ? '回收站为空' : 'Trash is empty'} body={isZh ? '您移除的环境将显示在此处，以便后续恢复或彻底清理。' : 'Profiles you remove will appear here so you can recover them.'} /> :
      <div className="mx-5 mb-6 overflow-x-auto rounded-lg border border-line"><table className="w-full min-w-[520px] text-left">
        <thead className="bg-surface text-ink-dim"><tr><th className="px-4 py-3 font-medium">{isZh ? '环境信息' : 'Profile'}</th><th className="px-4 py-3 font-medium">{isZh ? '移入回收站时间' : 'Moved to Trash'}</th><th className="px-4 py-3 text-right font-medium">{isZh ? '操作' : 'Actions'}</th></tr></thead>
        <tbody className="divide-y divide-line">{profiles.map(profile => <tr key={profile.id}>
          <td className="px-4 py-3"><p className="font-medium">{profile.name}</p><p className="font-mono text-[11px] text-ink-dim">{profile.id}</p></td>
          <td className="px-4 py-3 text-ink-dim">{new Date(profile.deleted_at).toLocaleString()}</td>
          <td className="px-4 py-3"><div className="flex justify-end gap-2">
            <button className="btn btn-default" disabled={!!busy} onClick={() => restore(profile)}>{busy === profile.id ? <LoaderCircle size={13} aria-hidden="true" className="animate-spin motion-reduce:animate-none" /> : <RotateCcw size={13} aria-hidden="true" />}{isZh ? '恢复' : 'Restore'}</button>
            <button className="btn btn-danger" disabled={!!busy} onClick={() => { setConfirmation(''); setDeleting(profile) }} aria-label={`Permanently delete ${profile.name}`}>{isZh ? '彻底删除' : 'Delete permanently'}</button>
          </div></td>
        </tr>)}</tbody>
      </table></div>}
    <Modal open={!!deleting} title={isZh ? '彻底永久删除环境' : 'Permanently delete profile'} onClose={() => { if (!busy) setDeleting(null) }} width={460} footer={<>
      <button className="btn btn-default" disabled={!!busy} onClick={() => setDeleting(null)}>{isZh ? '取消' : 'Cancel'}</button>
      <button className="btn btn-danger" disabled={!!busy || confirmation !== deleting?.name} onClick={remove}>{busy ? (isZh ? '正在删除…' : 'Deleting…') : (isZh ? '确认彻底删除' : 'Delete permanently')}</button>
    </>}>
      <p className="text-ink-dim">{isZh ? `此操作将从本实例中彻底清除环境 "${deleting?.name}" 及其全部浏览器本地缓存和数据。此操作不可撤销。现有单独创建的备份文件不受影响。` : `This permanently removes ${deleting?.name} and its browser data from this instance. This action cannot be undone. Existing backups are kept separately.`}</p>
      <label htmlFor="delete-name" className="mb-1 mt-4 block">{isZh ? <>请输入环境名称 <strong className="break-all">{deleting?.name}</strong> 进行确认</> : <>Type <strong className="break-all">{deleting?.name}</strong> to confirm</>}</label>
      <input id="delete-name" className="field" value={confirmation} onChange={event => setConfirmation(event.target.value)} autoComplete="off" autoFocus />
    </Modal>
  </>
}
