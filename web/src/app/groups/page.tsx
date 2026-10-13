'use client'

import { useCallback, useEffect, useState } from 'react'
import { Layers, Pencil, Plus, Trash2 } from 'lucide-react'

import { EmptyState } from '@/components/empty-state'
import { ConfirmDialog, Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { groupsAPI, type Group } from '@/lib/api'

import { useI18n } from '@/lib/i18n'

export default function GroupsPage() {
  const { t, isZh } = useI18n()
  const [groups, setGroups] = useState<Group[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Group | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState<Group | null>(null)

  const toast = useToast()

  const load = useCallback(async () => {
    try {
      setError(null)
      const response = await groupsAPI.list()
      setGroups(response.groups)
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
    setName('')
    setDescription('')
    setFormOpen(true)
  }

  function openEdit(group: Group) {
    setEditing(group)
    setName(group.name)
    setDescription(group.description ?? '')
    setFormOpen(true)
  }

  async function save(event: React.FormEvent) {
    event.preventDefault()
    if (!name.trim()) {
      toast('error', isZh ? '分组名称不能为空' : 'Name is required')
      return
    }
    setSaving(true)
    try {
      if (editing) {
        await groupsAPI.update(editing.id, { name: name.trim(), description: description.trim() })
        toast('ok', isZh ? '分组已更新' : 'Group updated', name.trim())
      } else {
        await groupsAPI.create({ name: name.trim(), description: description.trim() })
        toast('ok', isZh ? '分组创建成功' : 'Group created', name.trim())
      }
      setFormOpen(false)
      load()
    } catch (err) {
      toast('error', editing ? (isZh ? '无法更新分组' : 'Could not update group') : (isZh ? '无法创建分组' : 'Could not create group'), String(err))
    } finally {
      setSaving(false)
    }
  }

  async function remove() {
    if (!deleting) return
    const group = deleting
    setDeleting(null)
    try {
      await groupsAPI.remove(group.id)
      toast('ok', isZh ? '分组已删除' : 'Group deleted', group.name)
      load()
    } catch (err) {
      toast('error', isZh ? '无法删除分组' : 'Could not delete group', String(err))
    }
  }

  return (
    <>
      <header className="sticky top-0 z-20 flex h-[52px] items-center gap-3 border-b border-line bg-canvas/85 px-5 backdrop-blur">
        <h1 className="text-[14px] font-semibold">{t('nav.groups', 'Groups')}</h1>
        <span className="font-mono text-ink-faint">{groups.length}</span>
        <button className="btn btn-primary ml-auto" onClick={openCreate}>
          <Plus size={14} strokeWidth={2.5} />
          {isZh ? '新建分组' : 'New group'}
        </button>
      </header>

      {error ? (
        <EmptyState
          icon={<Layers size={18} />}
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
      ) : groups.length === 0 ? (
        <EmptyState
          icon={<Layers size={18} />}
          title={isZh ? '暂无分组' : 'No groups yet'}
          body={isZh ? '分组可用于按业务、客户或用途归类管理环境。创建或编辑环境时可将其分配至特定分组。' : 'Groups organise profiles by purpose or client. Assign a profile to a group when you create or edit it.'}
          action={
            <button className="btn btn-primary" onClick={openCreate}>
              <Plus size={14} strokeWidth={2.5} />
              {isZh ? '创建分组' : 'Create a group'}
            </button>
          }
        />
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-line text-left text-[11px] uppercase tracking-[0.05em] text-ink-faint">
              <th className="py-2 pl-5 pr-4 font-medium">{isZh ? '分组名称' : 'Name'}</th>
              <th className="py-2 pr-4 font-medium">ID</th>
              <th className="py-2 pr-4 font-medium">{isZh ? '描述' : 'Description'}</th>
              <th className="py-2 pr-4 font-medium">{isZh ? '环境数量' : 'Profiles'}</th>
              <th className="w-[88px] py-2 pr-5" />
            </tr>
          </thead>
          <tbody>
            {groups.map((group, index) => (
              <tr
                key={group.id}
                className="row-in border-b border-line/60 hover:bg-surface"
                style={{ animationDelay: `${Math.min(index, 12) * 12}ms` }}
              >
                <td className="py-2.5 pl-5 pr-4 font-medium">{group.name}</td>
                <td className="py-2.5 pr-4 font-mono text-ink-faint">{group.id}</td>
                <td className="py-2.5 pr-4 text-ink-dim">{group.description || '—'}</td>
                <td className="py-2.5 pr-4 font-mono text-ink-dim">{group.profile_count}</td>
                <td className="py-2.5 pr-5">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      className="btn btn-ghost h-7 w-7 p-0"
                      aria-label={`Edit ${group.name}`}
                      onClick={() => openEdit(group)}
                    >
                      <Pencil size={13} />
                    </button>
                    <button
                      className="btn btn-ghost h-7 w-7 p-0 hover:text-danger"
                      aria-label={`Delete ${group.name}`}
                      onClick={() => setDeleting(group)}
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
        title={editing ? (isZh ? '编辑分组' : 'Edit group') : (isZh ? '新建分组' : 'New group')}
        onClose={() => setFormOpen(false)}
        width={440}
        footer={
          <>
            <button className="btn btn-default" onClick={() => setFormOpen(false)}>
              {isZh ? '取消' : 'Cancel'}
            </button>
            <button type="submit" form="group-form" className="btn btn-primary" disabled={saving}>
              {editing ? (isZh ? '保存更改' : 'Save changes') : (isZh ? '创建分组' : 'Create group')}
            </button>
          </>
        }
      >
        <form id="group-form" onSubmit={save} className="flex flex-col gap-3">
          <div>
            <label className="field-label" htmlFor="group-name">
              {isZh ? '分组名称' : 'Name'}
            </label>
            <input
              id="group-name"
              className="field"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={isZh ? '例如：客户A / 亚马逊运营' : 'Client A'}
              autoFocus
              required
            />
          </div>
          <div>
            <label className="field-label" htmlFor="group-desc">
              {isZh ? '描述' : 'Description'}
            </label>
            <textarea
              id="group-desc"
              className="field resize-y"
              rows={2}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleting !== null}
        title={isZh ? '删除分组' : 'Delete group'}
        body={
          deleting
            ? (isZh
                ? `确认删除分组 "${deleting.name}" 吗？其包含的 ${deleting.profile_count} 个环境将被保留并恢复为未分组状态。`
                : `"${deleting.name}" will be removed. Its ${deleting.profile_count} profile(s) are kept and become ungrouped.`)
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
