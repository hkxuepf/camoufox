'use client'

import { useEffect, useState } from 'react'
import { History, RotateCcw, Trash2, CloudUpload, Clock, HardDrive, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react'
import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { profilesAPI, type Profile } from '@/lib/api'

interface SnapshotItem {
  id: string
  profile_id: string
  snapshot_name: string
  size_kb: number
  r2_key: string
  created_at: string
}

interface SnapshotModalProps {
  open: boolean
  onClose: () => void
  profile: Profile | null
  onRollbackSuccess?: () => void
}

export function SnapshotModal({ open, onClose, profile, onRollbackSuccess }: SnapshotModalProps) {
  const [snapshots, setSnapshots] = useState<SnapshotItem[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [rollingId, setRollingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const toast = useToast()

  const fetchSnapshots = async (profileId: string) => {
    setLoading(true)
    try {
      const res = await profilesAPI.listSnapshots(profileId)
      setSnapshots(res.snapshots || [])
    } catch (err: any) {
      toast('error', '获取快照历史失败', err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open && profile) {
      fetchSnapshots(profile.id)
    } else {
      setSnapshots([])
    }
  }, [open, profile])

  const handleCreateSnapshot = async () => {
    if (!profile) return
    setCreating(true)
    try {
      toast('info', '正在创建云漫游新快照...')
      const res = await profilesAPI.pushCloudSync(profile.id)
      if (res.success) {
        toast('ok', `快照创建成功 (${res.size_kb} KB)`)
        await fetchSnapshots(profile.id)
      } else {
        toast('error', '快照创建失败', (res as any).error)
      }
    } catch (err: any) {
      toast('error', '创建异常', err.message)
    } finally {
      setCreating(false)
    }
  }

  const handleRollback = async (snap: SnapshotItem) => {
    if (!profile) return
    if (!window.confirm(`确定要回滚到「${snap.snapshot_name}」吗？\n\n注意：当前本地未同步的数据将被该历史时刻的数据覆盖！`)) {
      return
    }

    setRollingId(snap.id)
    try {
      const res = await profilesAPI.rollbackSnapshot(profile.id, snap.id)
      if (res.success) {
        toast('ok', `已成功回滚到「${snap.snapshot_name}」`)
        onRollbackSuccess?.()
        onClose()
      } else {
        toast('error', '回滚失败', res.message)
      }
    } catch (err: any) {
      toast('error', '回滚异常', err.message)
    } finally {
      setRollingId(null)
    }
  }

  const handleDelete = async (snap: SnapshotItem) => {
    if (!profile) return
    if (!window.confirm(`确定删除历史快照记录「${snap.snapshot_name}」？`)) return

    setDeletingId(snap.id)
    try {
      const res = await profilesAPI.deleteSnapshot(profile.id, snap.id)
      if (res.success) {
        toast('ok', '快照已删除')
        setSnapshots((prev) => prev.filter((s) => s.id !== snap.id))
      }
    } catch (err: any) {
      toast('error', '删除失败', err.message)
    } finally {
      setDeletingId(null)
    }
  }

  const formatTime = (isoStr: string) => {
    try {
      const d = new Date(isoStr)
      return d.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    } catch {
      return isoStr
    }
  }

  if (!profile) return null

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`云漫游快照时光机 · ${profile.name}`}
      footer={
        <div className="flex items-center justify-between w-full">
          <button
            type="button"
            onClick={handleCreateSnapshot}
            disabled={creating || loading}
            className="inline-flex items-center gap-1.5 rounded-md border border-[#1664ff] bg-white px-3 py-1.5 text-xs font-medium text-[#1664ff] hover:bg-[#1664ff]/5 transition-colors disabled:opacity-50"
          >
            {creating ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <CloudUpload className="h-3.5 w-3.5" />
            )}
            <span>手动生成当前快照</span>
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-[#eaedf1] bg-white px-4 py-1.5 text-xs font-medium text-[#334155] hover:bg-[#f8fafc] transition-colors"
          >
            关闭
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Info card */}
        <div className="rounded-lg border border-sky-100 bg-sky-50/60 p-3 text-xs text-sky-800 leading-relaxed">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 text-sky-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-sky-900">自动历史追溯机制 (Rolling Snapshots)</p>
              <p className="mt-0.5 text-sky-700">
                每次浏览器退出时自动触发安全归档并滚动保留最近 5 个会话版本（Cookie、LocalStorage 与配置）。
                如遇风控或数据异常，可随时一键时光倒流。
              </p>
            </div>
          </div>
        </div>

        {/* Snapshot list */}
        <div className="min-h-[220px]">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 text-[#94a3b8]">
              <RefreshCw className="h-6 w-6 animate-spin text-[#1664ff] mb-2" />
              <span className="text-xs">加载历史快照中...</span>
            </div>
          ) : snapshots.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-[#94a3b8]">
              <Clock className="h-8 w-8 text-slate-300 mb-2" />
              <span className="text-xs text-slate-600 font-medium">暂无历史快照记录</span>
              <span className="text-[11px] text-slate-400 mt-1">
                打开并关闭该环境后，系统将自动产生静默漫游快照，亦可点击下方按钮手动生成。
              </span>
            </div>
          ) : (
            <div className="divide-y divide-[#eaedf1] rounded-md border border-[#eaedf1] overflow-hidden">
              {snapshots.map((snap, idx) => (
                <div
                  key={snap.id}
                  className="flex items-center justify-between p-3 text-xs hover:bg-[#f8fafc] transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-[#1664ff] shrink-0 mt-0.5">
                      <History className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-[#0f172a]">
                          {snap.snapshot_name || `快照版本 #${snapshots.length - idx}`}
                        </span>
                        {idx === 0 && (
                          <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 border border-emerald-200">
                            最新云端版本
                          </span>
                        )}
                      </div>
                      <div className="mt-1 flex items-center gap-3 text-[11px] text-[#64748b]">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatTime(snap.created_at)}
                        </span>
                        <span className="flex items-center gap-1">
                          <HardDrive className="h-3 w-3" />
                          {snap.size_kb} KB
                        </span>
                        <span className="text-slate-400 font-mono text-[10px]">
                          {snap.id}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={rollingId !== null}
                      onClick={() => handleRollback(snap)}
                      className="inline-flex items-center gap-1 rounded bg-[#1664ff] px-2.5 py-1 text-[11px] font-medium text-white hover:bg-[#1664ff]/90 transition-colors disabled:opacity-50"
                    >
                      {rollingId === snap.id ? (
                        <RefreshCw className="h-3 w-3 animate-spin" />
                      ) : (
                        <RotateCcw className="h-3 w-3" />
                      )}
                      <span>回滚</span>
                    </button>
                    <button
                      type="button"
                      disabled={deletingId !== null}
                      onClick={() => handleDelete(snap)}
                      title="删除快照记录"
                      className="flex h-6 w-6 items-center justify-center rounded text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition-colors"
                    >
                      {deletingId === snap.id ? (
                        <RefreshCw className="h-3 w-3 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Modal>
  )
}
