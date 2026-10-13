'use client'

import { useState } from 'react'
import { Modal } from '@/components/modal'
import { type Profile } from '@/lib/api'
import { useToast } from '@/components/toast'
import { ArrowRightLeft, ShieldCheck, UserCheck, KeyRound } from 'lucide-react'

export function TransferModal({
  open,
  profile,
  onClose,
}: {
  open: boolean
  profile: Profile | null
  onClose: () => void
}) {
  const [targetAccount, setTargetAccount] = useState('')
  const [keepCopy, setKeepCopy] = useState(false)
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  if (!profile) return null

  const handleTransfer = async () => {
    if (!targetAccount.trim()) {
      toast('error', '请输入目标接收账号或团队成员邮箱')
      return
    }
    setLoading(true)
    try {
      await new Promise((r) => setTimeout(r, 600))
      toast('ok', `已将环境 "${profile.name}" 转移至 ${targetAccount}`)
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`转移环境 — ${profile.name}`}
      width={460}
      footer={
        <>
          <button className="btn btn-default" onClick={onClose} disabled={loading}>
            取消
          </button>
          <button className="btn btn-primary" onClick={handleTransfer} disabled={loading}>
            {loading ? '转移中…' : '确认转移'}
          </button>
        </>
      }
    >
      <div className="space-y-4 text-xs text-[#334155]">
        <div className="rounded-lg bg-blue-50/70 p-3 text-blue-700 border border-blue-200/60 leading-relaxed">
          环境转移后，该环境的全部浏览器指纹特征、缓存以及 Cookie 将完整移交至目标团队成员账户。
        </div>

        <div>
          <label className="block font-medium text-[#0f172a] mb-1.5">目标接收账号 (邮箱或用户 ID)</label>
          <input
            className="field w-full h-8 text-xs"
            placeholder="例如: member@team.com 或 601111818305"
            value={targetAccount}
            onChange={(e) => setTargetAccount(e.target.value)}
          />
        </div>

        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            className="accent-[#1664ff]"
            checked={keepCopy}
            onChange={(e) => setKeepCopy(e.target.checked)}
          />
          <span className="text-[#475569]">在当前团队空间保留一份副本</span>
        </label>
      </div>
    </Modal>
  )
}

export function PasskeyModal({
  open,
  profile,
  onClose,
}: {
  open: boolean
  profile: Profile | null
  onClose: () => void
}) {
  if (!profile) return null

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Passkey 凭证管理 — ${profile.name}`}
      width={480}
      footer={
        <button className="btn btn-default" onClick={onClose}>
          关闭
        </button>
      }
    >
      <div className="space-y-4 text-xs text-[#334155]">
        <div className="flex items-center gap-2 rounded-lg bg-[#f8fafc] border border-[#eaedf1] p-3">
          <KeyRound size={20} className="text-[#1664ff]" />
          <div>
            <div className="font-medium text-[#0f172a]">WebAuthn / FIDO2 Passkey 硬件密钥</div>
            <div className="text-[#64748b] text-[11px]">环境内绑定的无密码登录凭证与硬件密钥证书</div>
          </div>
        </div>

        <div className="rounded-lg border border-[#eaedf1] p-6 text-center text-[#94a3b8]">
          当前环境暂未录入绑定的 Passkey 物理安全密钥或 WebAuthn 凭证
        </div>
      </div>
    </Modal>
  )
}

export function AuthorizeModal({
  open,
  profile,
  onClose,
}: {
  open: boolean
  profile: Profile | null
  onClose: () => void
}) {
  const toast = useToast()
  if (!profile) return null

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`授权成员 — ${profile.name}`}
      width={460}
      footer={
        <button
          className="btn btn-primary"
          onClick={() => {
            toast('ok', '授权配置已更新')
            onClose()
          }}
        >
          确定
        </button>
      }
    >
      <div className="space-y-4 text-xs text-[#334155]">
        <div className="text-[#64748b]">
          设置允许访问和打开此环境的子账号或团队成员角色：
        </div>
        <div className="space-y-2 border border-[#eaedf1] rounded-lg p-3">
          <label className="flex items-center justify-between py-1">
            <span className="font-medium text-[#0f172a]">所有团队管理员 (Admin)</span>
            <input type="checkbox" className="accent-[#1664ff]" defaultChecked disabled />
          </label>
          <label className="flex items-center justify-between py-1 border-t border-[#f1f5f9]">
            <span className="text-[#0f172a]">运营专员 (Operator)</span>
            <input type="checkbox" className="accent-[#1664ff]" defaultChecked />
          </label>
          <label className="flex items-center justify-between py-1 border-t border-[#f1f5f9]">
            <span className="text-[#0f172a]">访客成员 (Viewer)</span>
            <input type="checkbox" className="accent-[#1664ff]" />
          </label>
        </div>
      </div>
    </Modal>
  )
}
