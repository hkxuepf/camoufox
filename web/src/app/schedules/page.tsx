'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  CalendarClock,
  Pause,
  Pencil,
  Play,
  Plus,
  // lucide 1.0 renamed History to RotateCcwClock. The old name is the one that
  // means anything next to a History button, so keep it locally.
  RotateCcwClock as History,
  Trash2,
} from 'lucide-react'

import { EmptyState } from '@/components/empty-state'
import { ConfirmDialog, Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { useI18n } from '@/lib/i18n'
import {
  formatLastUsed,
  profilesAPI,
  schedulesAPI,
  type Profile,
  type Schedule,
  type ScheduleAction,
  type ScheduleKind,
  type ScheduleRun,
  type ScheduleRunOutcome,
} from '@/lib/api'

const DAY_LABELS_EN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const DAY_LABELS_ZH = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const ACTION_LABELS_EN: Record<ScheduleAction, string> = {
  launch: 'Open browser',
  refresh_browser: 'Refresh browser version',
}

const ACTION_LABELS_ZH: Record<ScheduleAction, string> = {
  launch: '启动环境浏览器',
  refresh_browser: '同步浏览器版本',
}

const OUTCOME_STYLES: Record<ScheduleRunOutcome, string> = {
  ok: 'text-ok',
  skipped: 'text-ink-dim',
  error: 'text-danger',
  missed: 'text-warn',
}

function describeWhen(schedule: Schedule, isZh: boolean): string {
  const dayLabels = isZh ? DAY_LABELS_ZH : DAY_LABELS_EN
  if (schedule.kind === 'interval') {
    const minutes = schedule.interval_minutes ?? 0
    if (minutes % 1440 === 0) return isZh ? `每 ${minutes / 1440} 天` : `every ${minutes / 1440}d`
    if (minutes % 60 === 0) return isZh ? `每 ${minutes / 60} 小时` : `every ${minutes / 60}h`
    return isZh ? `每 ${minutes} 分钟` : `every ${minutes}m`
  }
  const days =
    schedule.days && schedule.days.length > 0
      ? ` · ${schedule.days.map((day) => dayLabels[day]).join(' ')}`
      : ''
  return isZh ? `每天 ${schedule.at_time}${days}` : `daily at ${schedule.at_time}${days}`
}

function formatNextRun(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function SchedulesPage() {
  const { t, isZh } = useI18n()
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Schedule | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState<Schedule | null>(null)
  const [historyFor, setHistoryFor] = useState<Schedule | null>(null)
  const [historyRuns, setHistoryRuns] = useState<ScheduleRun[]>([])

  // Form fields
  const [profileId, setProfileId] = useState('')
  const [action, setAction] = useState<ScheduleAction>('launch')
  const [kind, setKind] = useState<ScheduleKind>('daily')
  const [intervalMinutes, setIntervalMinutes] = useState('60')
  const [atTime, setAtTime] = useState('09:00')
  const [days, setDays] = useState<number[]>([])
  const [runMinutes, setRunMinutes] = useState('')

  const toast = useToast()

  const load = useCallback(async () => {
    try {
      setError(null)
      const [scheduleList, profileList] = await Promise.all([
        schedulesAPI.list(),
        profilesAPI.getProfiles({ per_page: 100 }),
      ])
      setSchedules(scheduleList.schedules)
      setProfiles(profileList.profiles)
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // Clears the previous error synchronously before awaiting; see the note
    // on the profiles page.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load()
  }, [load])

  function openCreate() {
    setEditing(null)
    setProfileId(profiles[0]?.id ?? '')
    setAction('launch')
    setKind('daily')
    setIntervalMinutes('60')
    setAtTime('09:00')
    setDays([])
    setRunMinutes('')
    setFormOpen(true)
  }

  function openEdit(schedule: Schedule) {
    setEditing(schedule)
    setProfileId(schedule.profile_id)
    setAction(schedule.action)
    setKind(schedule.kind)
    setIntervalMinutes(String(schedule.interval_minutes ?? 60))
    setAtTime(schedule.at_time ?? '09:00')
    setDays(schedule.days ?? [])
    setRunMinutes(schedule.run_minutes ? String(schedule.run_minutes) : '')
    setFormOpen(true)
  }

  async function save(event: React.FormEvent) {
    event.preventDefault()
    if (!profileId) {
      toast('error', isZh ? '请选择目标环境' : 'Choose a profile')
      return
    }
    const payload = {
      action,
      kind,
      interval_minutes: kind === 'interval' ? Number(intervalMinutes) || 60 : null,
      at_time: kind === 'daily' ? atTime : null,
      days: kind === 'daily' && days.length > 0 ? days : null,
      run_minutes: action === 'launch' && runMinutes ? Number(runMinutes) : null,
    }
    setSaving(true)
    try {
      if (editing) {
        await schedulesAPI.update(editing.id, payload)
        toast('ok', isZh ? '任务已更新' : 'Schedule updated')
      } else {
        await schedulesAPI.create({ ...payload, profile_id: profileId })
        toast('ok', isZh ? '任务已创建' : 'Schedule created')
      }
      setFormOpen(false)
      load()
    } catch (err) {
      toast('error', editing ? (isZh ? '无法更新任务' : 'Could not update schedule') : (isZh ? '无法创建任务' : 'Could not create schedule'), String(err))
    } finally {
      setSaving(false)
    }
  }

  async function toggle(schedule: Schedule) {
    try {
      await schedulesAPI.update(schedule.id, { enabled: !schedule.enabled })
      toast('ok', schedule.enabled ? (isZh ? '任务已暂停' : 'Schedule paused') : (isZh ? '任务已恢复' : 'Schedule resumed'))
      load()
    } catch (err) {
      toast('error', isZh ? '无法更新任务状态' : 'Could not update schedule', String(err))
    }
  }

  async function runNow(schedule: Schedule) {
    try {
      const run = await schedulesAPI.runNow(schedule.id)
      if (run.outcome === 'ok') toast('ok', isZh ? '任务已触发' : 'Task ran', run.message ?? undefined)
      else if (run.outcome === 'skipped') toast('ok', isZh ? '任务已跳过' : 'Task skipped', run.message ?? undefined)
      else toast('error', isZh ? '任务执行失败' : 'Task failed', run.message ?? undefined)
      load()
    } catch (err) {
      toast('error', isZh ? '无法执行任务' : 'Could not run the task', String(err))
    }
  }

  async function remove() {
    if (!deleting) return
    const schedule = deleting
    setDeleting(null)
    try {
      await schedulesAPI.remove(schedule.id)
      toast('ok', isZh ? '任务已删除' : 'Schedule deleted')
      load()
    } catch (err) {
      toast('error', isZh ? '无法删除任务' : 'Could not delete schedule', String(err))
    }
  }

  async function openHistory(schedule: Schedule) {
    setHistoryFor(schedule)
    setHistoryRuns([])
    try {
      const response = await schedulesAPI.runs(schedule.id)
      setHistoryRuns(response.runs)
    } catch (err) {
      toast('error', isZh ? '无法加载执行历史' : 'Could not load the history', String(err))
    }
  }

  return (
    <>
      <header className="sticky top-0 z-20 flex h-[52px] items-center gap-3 border-b border-line bg-canvas/85 px-5 backdrop-blur">
        <h1 className="text-[14px] font-semibold">{t('nav.schedules', 'Schedules')}</h1>
        <span className="font-mono text-ink-faint">{schedules.length}</span>
        <button className="btn btn-primary ml-auto" onClick={openCreate}>
          <Plus size={14} strokeWidth={2.5} />
          {isZh ? '新建任务' : 'New schedule'}
        </button>
      </header>

      {error ? (
        <EmptyState
          icon={<CalendarClock size={18} />}
          title={isZh ? '无法连接到后端服务' : 'Cannot reach the API'}
          body={error}
          action={
            <button className="btn btn-default" onClick={load}>
              {isZh ? '重试' : 'Retry'}
            </button>
          }
        />
      ) : loading ? (
        <p className="px-5 py-8 text-ink-faint">{isZh ? '正在加载…' : 'Loading…'}</p>
      ) : schedules.length === 0 ? (
        <EmptyState
          icon={<CalendarClock size={18} />}
          title={isZh ? '暂无自动化任务' : 'Nothing scheduled'}
          body={isZh ? '可按计划定时自动启动环境浏览器进行账号预热，或保持浏览器版本与最新内核同步。应用关闭期间错过的任务会自动跳过。' : "Open a profile's browser on a schedule, or keep its pinned browser version current. Runs missed while the app is closed are skipped, not replayed."}
          action={
            <button className="btn btn-primary" onClick={openCreate}>
              <Plus size={14} strokeWidth={2.5} />
              {isZh ? '创建任务计划' : 'Create a schedule'}
            </button>
          }
        />
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-line text-left text-[11px] uppercase tracking-[0.05em] text-ink-faint">
              <th className="py-2 pl-5 pr-4 font-medium">{isZh ? '目标环境' : 'Profile'}</th>
              <th className="py-2 pr-4 font-medium">{isZh ? '任务类型' : 'Task'}</th>
              <th className="py-2 pr-4 font-medium">{isZh ? '触发周期' : 'When'}</th>
              <th className="py-2 pr-4 font-medium">{isZh ? '下次运行' : 'Next run'}</th>
              <th className="py-2 pr-4 font-medium">{isZh ? '上次运行' : 'Last run'}</th>
              <th className="w-[168px] py-2 pr-5" />
            </tr>
          </thead>
          <tbody>
            {schedules.map((schedule, index) => (
              <tr
                key={schedule.id}
                className={`row-in border-b border-line/60 hover:bg-surface ${
                  schedule.enabled ? '' : 'opacity-50'
                }`}
                style={{ animationDelay: `${Math.min(index, 12) * 12}ms` }}
              >
                <td className="py-2.5 pl-5 pr-4 font-medium">
                  {schedule.profile_name ?? <span className="text-ink-faint">{isZh ? '已删除' : 'deleted'}</span>}
                </td>
                <td className="py-2.5 pr-4 text-ink-dim">
                  {isZh ? ACTION_LABELS_ZH[schedule.action] : ACTION_LABELS_EN[schedule.action]}
                  {schedule.run_minutes ? (
                    <span className="text-ink-faint"> · {schedule.run_minutes}{isZh ? '分钟会话' : 'm session'}</span>
                  ) : null}
                </td>
                <td className="py-2.5 pr-4 font-mono text-ink-dim">{describeWhen(schedule, isZh)}</td>
                <td className="py-2.5 pr-4 font-mono text-ink-dim">
                  {schedule.enabled ? formatNextRun(schedule.next_run_at) : (isZh ? '已暂停' : 'paused')}
                </td>
                <td className="py-2.5 pr-4">
                  {schedule.last_run ? (
                    <button
                      className={`font-mono ${OUTCOME_STYLES[schedule.last_run.outcome]} hover:underline`}
                      title={schedule.last_run.message ?? undefined}
                      onClick={() => openHistory(schedule)}
                    >
                      {schedule.last_run.outcome} · {formatLastUsed(schedule.last_run.started_at)}
                    </button>
                  ) : (
                    <span className="text-ink-faint">—</span>
                  )}
                </td>
                <td className="py-2.5 pr-5">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      className="btn btn-ghost h-7 w-7 p-0"
                      aria-label={`Run ${schedule.profile_name ?? schedule.id} now`}
                      title={isZh ? '立即执行' : 'Run now'}
                      onClick={() => runNow(schedule)}
                    >
                      <Play size={13} />
                    </button>
                    <button
                      className="btn btn-ghost h-7 w-7 p-0"
                      aria-label={schedule.enabled ? 'Pause schedule' : 'Resume schedule'}
                      title={schedule.enabled ? (isZh ? '暂停任务' : 'Pause') : (isZh ? '恢复任务' : 'Resume')}
                      onClick={() => toggle(schedule)}
                    >
                      {schedule.enabled ? <Pause size={13} /> : <Play size={13} className="text-signal" />}
                    </button>
                    <button
                      className="btn btn-ghost h-7 w-7 p-0"
                      aria-label="Run history"
                      title={isZh ? '执行记录' : 'History'}
                      onClick={() => openHistory(schedule)}
                    >
                      <History size={13} />
                    </button>
                    <button
                      className="btn btn-ghost h-7 w-7 p-0"
                      aria-label="Edit schedule"
                      title={isZh ? '编辑' : 'Edit'}
                      onClick={() => openEdit(schedule)}
                    >
                      <Pencil size={13} />
                    </button>
                    <button
                      className="btn btn-ghost h-7 w-7 p-0 hover:text-danger"
                      aria-label="Delete schedule"
                      title={isZh ? '删除' : 'Delete'}
                      onClick={() => setDeleting(schedule)}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Modal
        open={formOpen}
        title={editing ? (isZh ? '编辑任务计划' : 'Edit schedule') : (isZh ? '新建任务计划' : 'New schedule')}
        subtitle={isZh ? '执行时间以服务端时钟为准（运行 camoufox-pm 实例的主机时间）。' : "Times are read on the server's clock — the machine running camoufox-pm."}
        onClose={() => setFormOpen(false)}
        width={480}
        footer={
          <>
            <button className="btn btn-default" onClick={() => setFormOpen(false)}>
              {isZh ? '取消' : 'Cancel'}
            </button>
            <button type="submit" form="schedule-form" className="btn btn-primary" disabled={saving}>
              {editing ? (isZh ? '保存更改' : 'Save changes') : (isZh ? '创建任务' : 'Create schedule')}
            </button>
          </>
        }
      >
        <form id="schedule-form" onSubmit={save} className="flex flex-col gap-3">
          <div>
            <label className="field-label" htmlFor="schedule-profile">
              {isZh ? '目标环境' : 'Profile'}
            </label>
            <select
              id="schedule-profile"
              className="field"
              value={profileId}
              onChange={(event) => setProfileId(event.target.value)}
              disabled={editing !== null}
              required
            >
              <option value="" disabled>
                {isZh ? '选择环境' : 'Choose a profile'}
              </option>
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="field-label" htmlFor="schedule-action">
              {isZh ? '任务类型' : 'Task'}
            </label>
            <select
              id="schedule-action"
              className="field"
              value={action}
              onChange={(event) => setAction(event.target.value as ScheduleAction)}
            >
              <option value="launch">
                {isZh ? '启动环境浏览器 — 进行会话活跃预热' : 'Open browser — warm the profile with a session'}
              </option>
              <option value="refresh_browser">
                {isZh ? '同步内核版本 — 保持指纹特征更新' : "Refresh browser version — keep the pinned machine's browser current"}
              </option>
            </select>
            <p className="mt-1 text-ink-faint">
              {action === 'refresh_browser'
                ? (isZh
                    ? '仅将浏览器内核版本更新至最新已安装版本；屏幕、GPU、核心数及指纹种子保持不变。'
                    : 'Moves only the browser version onto the installed one; the screen, GPU, cores and seeds stay. Regenerating the hardware itself is deliberately not schedulable — it would make the profile a new machine on a timer.')
                : (isZh
                    ? '与通过启动按钮打开环境一致；如果该环境当前已处于运行中，则该次调度会自动跳过。'
                    : 'Launches through the same session manager as the Open button; if the browser is already running, the run is skipped.')}
            </p>
          </div>

          <div>
            <span className="field-label">{isZh ? '触发周期' : 'Repeats'}</span>
            <div className="flex gap-2">
              <button
                type="button"
                className={kind === 'daily' ? 'btn btn-default border-signal text-ink' : 'btn btn-default'}
                aria-pressed={kind === 'daily'}
                onClick={() => setKind('daily')}
              >
                {isZh ? '每日定时' : 'Daily at a time'}
              </button>
              <button
                type="button"
                className={kind === 'interval' ? 'btn btn-default border-signal text-ink' : 'btn btn-default'}
                aria-pressed={kind === 'interval'}
                onClick={() => setKind('interval')}
              >
                {isZh ? '循环间隔' : 'Every N minutes'}
              </button>
            </div>
          </div>

          {kind === 'interval' ? (
            <div>
              <label className="field-label" htmlFor="schedule-interval">
                {isZh ? '执行间隔 (分钟)' : 'Every (minutes)'}
              </label>
              <input
                id="schedule-interval"
                type="number"
                min={1}
                max={40320}
                className="field font-mono"
                value={intervalMinutes}
                onChange={(event) => setIntervalMinutes(event.target.value)}
                required
              />
            </div>
          ) : (
            <>
              <div>
                <label className="field-label" htmlFor="schedule-time">
                  {isZh ? '触发时间 (服务器时间)' : 'At (server time)'}
                </label>
                <input
                  id="schedule-time"
                  type="time"
                  className="field font-mono"
                  value={atTime}
                  onChange={(event) => setAtTime(event.target.value)}
                  required
                />
              </div>
              <div>
                <span className="field-label">{isZh ? '生效星期 (不选则代表每天)' : 'On days (none = every day)'}</span>
                <div className="flex gap-1">
                  {(isZh ? DAY_LABELS_ZH : DAY_LABELS_EN).map((label, day) => (
                    <button
                      key={label}
                      type="button"
                      aria-pressed={days.includes(day)}
                      className={`btn h-7 px-2 font-mono ${
                        days.includes(day) ? 'btn-default border-signal text-ink' : 'btn-ghost'
                      }`}
                      onClick={() =>
                        setDays((current) =>
                          current.includes(day)
                            ? current.filter((d) => d !== day)
                            : [...current, day].sort(),
                        )
                      }
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          {action === 'launch' && (
            <div>
              <label className="field-label" htmlFor="schedule-run-minutes">
                {isZh ? '自动关闭时长 (分钟，留空则保持打开)' : 'Close after (minutes, empty = leave open)'}
              </label>
              <input
                id="schedule-run-minutes"
                type="number"
                min={1}
                max={1440}
                className="field font-mono"
                value={runMinutes}
                onChange={(event) => setRunMinutes(event.target.value)}
                placeholder={isZh ? '保持浏览器开启' : 'Leave the browser open'}
              />
            </div>
          )}
        </form>
      </Modal>

      <Modal
        open={historyFor !== null}
        title={isZh ? '任务执行记录' : 'Run history'}
        subtitle={
          historyFor
            ? `${historyFor.profile_name ?? historyFor.profile_id} · ${
                isZh ? ACTION_LABELS_ZH[historyFor.action] : ACTION_LABELS_EN[historyFor.action]
              } · ${isZh ? '由新到旧排列，保留最近 20 条' : 'newest first, last 20 kept'}`
            : undefined
        }
        onClose={() => setHistoryFor(null)}
        width={520}
      >
        {historyRuns.length === 0 ? (
          <p className="text-ink-faint">{isZh ? '暂无执行记录。' : 'No runs recorded yet.'}</p>
        ) : (
          <ul className="flex flex-col divide-y divide-line">
            {historyRuns.map((run) => (
              <li key={run.id} className="flex items-baseline gap-3 py-2">
                <span className={`w-[64px] shrink-0 font-mono ${OUTCOME_STYLES[run.outcome]}`}>
                  {run.outcome}
                </span>
                <span className="w-[128px] shrink-0 font-mono text-ink-dim">
                  {formatNextRun(run.started_at)}
                </span>
                <span className="text-ink-dim">{run.message ?? '—'}</span>
              </li>
            ))}
          </ul>
        )}
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        title={isZh ? '删除任务计划' : 'Delete schedule'}
        body={
          deleting
            ? (isZh
                ? `确认删除针对环境 "${deleting.profile_name ?? deleting.profile_id}" 的定时任务及其执行历史吗？环境本身不受任何影响。`
                : `The ${(isZh ? ACTION_LABELS_ZH[deleting.action] : ACTION_LABELS_EN[deleting.action]).toLowerCase()} schedule for "${
                    deleting.profile_name ?? deleting.profile_id
                  }" and its run history will be removed. The profile itself is not touched.`)
            : ''
        }
        confirmLabel={isZh ? '确认删除' : 'Delete'}
        cancelLabel={isZh ? '取消' : 'Cancel'}
        destructive
        onConfirm={remove}
        onCancel={() => setDeleting(null)}
      />
    </>
  )
}
