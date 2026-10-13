'use client'

import { useEffect, useState } from 'react'
import { KeyRound, Mail, ShieldCheck, User } from 'lucide-react'
import { Modal } from '@/components/modal'
import { useToast } from '@/components/toast'
import { profilesAPI, type Profile } from '@/lib/api'

interface AccountModalProps {
  open: boolean
  onClose: () => void
  profile: Profile | null
  onSaved?: () => void
}

export function AccountModal({ open, onClose, profile, onSaved }: AccountModalProps) {
  const [platform, setPlatform] = useState('custom')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [twoFactor, setTwoFactor] = useState('')
  const [saving, setSaving] = useState(false)
  const toast = useToast()

  useEffect(() => {
    if (open && profile) {
      const raw = profile.account || ''
      if (raw.startsWith('{')) {
        try {
          const parsed = JSON.parse(raw)
          setPlatform(parsed.platform || 'custom')
          setUsername(parsed.username || '')
          setPassword(parsed.password || '')
          setTwoFactor(parsed.twoFactor || '')
          return
        } catch {}
      }
      setUsername(raw)
      setPassword('')
      setTwoFactor('')
    } else {
      setUsername('')
      setPassword('')
      setTwoFactor('')
    }
  }, [open, profile])

  const handleSave = async () => {
    if (!profile) return
    setSaving(true)
    try {
      const payload = JSON.stringify({
        platform,
        username,
        password,
        twoFactor,
      })
      await profilesAPI.updateAccount(profile.id, username ? payload : '')
      toast('ok', '账号信息已保存')
      if (onSaved) onSaved()
      onClose()
    } catch (err) {
      toast('error', '保存失败', String(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={`编辑账号 — ${profile?.name ?? ''}`}>
      <div className="flex flex-col gap-4 text-xs">
        <div className="flex items-center gap-2 rounded-lg bg-[#f8fafc] border border-line p-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-signal/10 text-signal">
            <User size={18} />
          </div>
          <div>
            <div className="font-semibold text-ink">绑定业务平台账号</div>
            <div className="text-[11px] text-ink-dim">
              管理此环境对应的登录账号、密码及 2FA 凭据，方便团队协作与自动登录
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div>
            <label className="field-label">业务平台</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="field"
            >
              <option value="custom">通用 / 自定义平台</option>
              <option value="google">Google / Gmail</option>
              <option value="facebook">Facebook / Meta</option>
              <option value="tiktok">TikTok / 抖音海外版</option>
              <option value="amazon">Amazon 亚马逊</option>
              <option value="twitter">X / Twitter</option>
              <option value="instagram">Instagram</option>
              <option value="shopee">Shopee / 虾皮</option>
            </select>
          </div>

          <div>
            <label className="field-label">账号 / 登录邮箱</label>
            <div className="relative">
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="例如: user@gmail.com 或 601111818305"
                className="field pl-8 font-mono"
              />
              <Mail size={14} className="absolute left-2.5 top-2.5 text-ink-faint" />
            </div>
          </div>

          <div>
            <label className="field-label">登录密码</label>
            <div className="relative">
              <input
                type="text"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入或粘贴密码"
                className="field pl-8 font-mono"
              />
              <KeyRound size={14} className="absolute left-2.5 top-2.5 text-ink-faint" />
            </div>
          </div>

          <div>
            <label className="field-label">2FA 密钥 (双重验证 Secret Key)</label>
            <div className="relative">
              <input
                type="text"
                value={twoFactor}
                onChange={(e) => setTwoFactor(e.target.value)}
                placeholder="例如: JBSWY3DPEHPK3PXP"
                className="field pl-8 font-mono uppercase"
              />
              <ShieldCheck size={14} className="absolute left-2.5 top-2.5 text-ink-faint" />
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2.5 border-t border-line pt-3">
          <button type="button" onClick={onClose} className="btn btn-default px-4">
            取消
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="btn btn-primary px-5 font-semibold"
          >
            {saving ? '保存中...' : '确定保存'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
