'use client'

import { useEffect, useState } from 'react'
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  ExternalLink,
  Loader2,
  QrCode,
  ShieldCheck,
  Sparkles,
  Wallet,
  X,
} from 'lucide-react'

import { billingAPI, type Order, type Plan } from '@/lib/api'
import { useAuth } from '@/components/login-gate'
import { useI18n } from '@/lib/i18n'

interface BillingModalProps {
  open: boolean
  onClose: () => void
}

export function BillingModal({ open, onClose }: BillingModalProps) {
  const { t, language } = useI18n()
  const { planId, refresh } = useAuth()
  const [plans, setPlans] = useState<Plan[]>([])
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null)
  const [loadingPlans, setLoadingPlans] = useState(false)
  const [creatingOrder, setCreatingOrder] = useState(false)
  const [activeOrder, setActiveOrder] = useState<Order | null>(null)
  const [txHash, setTxHash] = useState('')
  const [submittingTx, setSubmittingTx] = useState(false)
  const [txSubmitted, setTxSubmitted] = useState(false)
  const [copied, setCopied] = useState(false)

  // Load plans when modal opens
  useEffect(() => {
    if (!open) {
      setActiveOrder(null)
      setSelectedPlan(null)
      setTxHash('')
      setTxSubmitted(false)
      return
    }
    setLoadingPlans(true)
    billingAPI
      .getPlans()
      .then((data) => {
        setPlans(data)
        const currentOrNext = data.find((p) => p.id !== 'free' && p.id !== planId) || data[1] || data[0]
        setSelectedPlan(currentOrNext)
      })
      .catch(() => {})
      .finally(() => setLoadingPlans(false))
  }, [open, planId])

  // Poll order status when an order is pending
  useEffect(() => {
    if (!activeOrder || activeOrder.status === 'paid') return

    const interval = setInterval(async () => {
      try {
        const order = await billingAPI.getOrder(activeOrder.order_no)
        if (order.status === 'paid') {
          setActiveOrder(order)
          await refresh()
        }
      } catch {
        // ignore polling error
      }
    }, 4000)

    return () => clearInterval(interval)
  }, [activeOrder, refresh])

  if (!open) return null

  const handleCreateOrder = async () => {
    if (!selectedPlan) return
    setCreatingOrder(true)
    try {
      const order = await billingAPI.createOrder(selectedPlan.id)
      setActiveOrder(order)
      setTxSubmitted(false)
      setTxHash('')
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err))
    } finally {
      setCreatingOrder(false)
    }
  }

  const handleSubmitTx = async () => {
    if (!activeOrder || !txHash.trim()) return
    setSubmittingTx(true)
    try {
      await billingAPI.submitTx(activeOrder.order_no, txHash.trim())
      setTxSubmitted(true)
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmittingTx(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="relative flex max-h-[90vh] w-full max-w-2xl flex-col rounded-xl border border-line bg-surface shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-signal/15 text-signal">
              <Sparkles size={18} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-ink">
                {language === 'zh' ? '升级套餐 / 充值订阅' : 'Subscription & Upgrade'}
              </h2>
              <p className="text-xs text-ink-dim">
                {language === 'zh'
                  ? '支持 USDT (TRC20) 安全充值，即刻解锁多开与环境上限'
                  : 'Fast & Secure USDT (TRC20) payments. Instant activation.'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-ink-dim transition-colors hover:bg-raised hover:text-ink"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeOrder ? (
            /* Order Payment Step */
            <div className="flex flex-col gap-5">
              {activeOrder.status === 'paid' ? (
                <div className="flex flex-col items-center justify-center gap-3 py-8 text-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-400">
                    <CheckCircle2 size={36} />
                  </div>
                  <h3 className="text-lg font-bold text-ink">
                    {language === 'zh' ? '支付成功，套餐已生效！' : 'Payment Confirmed!'}
                  </h3>
                  <p className="max-w-md text-sm text-ink-dim">
                    {language === 'zh'
                      ? `恭喜您成功开通【${activeOrder.plan_name}】，环境配额与有效期已同步更新。`
                      : `Your subscription to ${activeOrder.plan_name} is now active. Enjoy!`}
                  </p>
                  <button
                    onClick={onClose}
                    className="btn btn-primary mt-3 px-6 py-2"
                  >
                    {language === 'zh' ? '完成并返回' : 'Done & Close'}
                  </button>
                </div>
              ) : (
                <>
                  <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-4 text-xs text-amber-300">
                    <div className="flex items-center gap-2 font-medium">
                      <Clock size={15} />
                      {language === 'zh'
                        ? '请使用波场 TRC20 钱包向下方地址转入精确数量的 USDT'
                        : 'Please transfer the exact USDT amount via TRC20 network to the address below'}
                    </div>
                  </div>

                  {/* Order summary card */}
                  <div className="grid grid-cols-2 gap-3 rounded-lg border border-line bg-raised/40 p-4 text-sm">
                    <div>
                      <span className="text-xs text-ink-dim">
                        {language === 'zh' ? '订单编号' : 'Order No.'}
                      </span>
                      <p className="font-mono font-semibold text-ink">{activeOrder.order_no}</p>
                    </div>
                    <div>
                      <span className="text-xs text-ink-dim">
                        {language === 'zh' ? '订阅套餐' : 'Plan'}
                      </span>
                      <p className="font-semibold text-ink">{activeOrder.plan_name}</p>
                    </div>
                    <div>
                      <span className="text-xs text-ink-dim">
                        {language === 'zh' ? '应付金额' : 'Amount Due'}
                      </span>
                      <p className="text-base font-bold text-signal">
                        {activeOrder.amount_usdt} USDT
                      </p>
                    </div>
                    <div>
                      <span className="text-xs text-ink-dim">
                        {language === 'zh' ? '转账网络' : 'Network'}
                      </span>
                      <p className="font-medium text-emerald-400">
                        {activeOrder.pay_network || 'TRC20'}
                      </p>
                    </div>
                  </div>

                  {/* Payment address card */}
                  <div className="flex flex-col gap-2 rounded-lg border border-line bg-raised/60 p-4">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-xs font-medium text-ink-dim">
                        <Wallet size={14} />
                        {language === 'zh' ? 'USDT (TRC20) 收款地址' : 'USDT TRC20 Receiving Address'}
                      </span>
                      <button
                        onClick={() => copyToClipboard(activeOrder.pay_address)}
                        className="flex items-center gap-1 text-xs text-signal hover:underline"
                      >
                        {copied ? (
                          <>
                            <Check size={12} /> {language === 'zh' ? '已复制' : 'Copied'}
                          </>
                        ) : (
                          <>
                            <Copy size={12} /> {language === 'zh' ? '点击复制' : 'Copy Address'}
                          </>
                        )}
                      </button>
                    </div>
                    <div className="select-all break-all rounded bg-canvas p-2.5 font-mono text-xs text-ink">
                      {activeOrder.pay_address || 'TYDnyQfxxxxxxxSAMPLEWALLETaddress'}
                    </div>
                  </div>

                  {/* TxHash submission */}
                  <div className="flex flex-col gap-2">
                    <label className="text-xs text-ink-dim">
                      {language === 'zh'
                        ? '完成转账后，请在此粘贴区块链交易哈希 (TxHash / TxID) 以加快到账：'
                        : 'Submit your transaction hash (TxID) to speed up confirmation:'}
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="e.g. 7f8a9b..."
                        value={txHash}
                        onChange={(e) => setTxHash(e.target.value)}
                        className="field flex-1 font-mono text-xs"
                        disabled={txSubmitted}
                      />
                      <button
                        onClick={handleSubmitTx}
                        disabled={!txHash.trim() || submittingTx || txSubmitted}
                        className="btn btn-secondary text-xs"
                      >
                        {submittingTx ? (
                          <Loader2 size={13} className="animate-spin" />
                        ) : txSubmitted ? (
                          <>
                            <Check size={13} className="text-emerald-400" />
                            {language === 'zh' ? '已提交审核' : 'Submitted'}
                          </>
                        ) : (
                          language === 'zh' ? '提交' : 'Submit'
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Polling indicator */}
                  <div className="flex items-center justify-between border-t border-line pt-3 text-xs text-ink-faint">
                    <span className="flex items-center gap-1.5">
                      <Loader2 size={13} className="animate-spin text-signal" />
                      {language === 'zh'
                        ? '正在自动监听区块链到账中 (每 4 秒刷新)...'
                        : 'Awaiting blockchain confirmation (polling every 4s)...'}
                    </span>
                    <button
                      onClick={() => setActiveOrder(null)}
                      className="text-ink-dim hover:text-ink"
                    >
                      {language === 'zh' ? '更换套餐' : 'Change Plan'}
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            /* Plan Selection Step */
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {plans
                  .filter((p) => p.id !== 'free')
                  .map((plan) => {
                    const isSelected = selectedPlan?.id === plan.id
                    const isCurrent = planId === plan.id
                    return (
                      <div
                        key={plan.id}
                        onClick={() => setSelectedPlan(plan)}
                        className={`relative flex cursor-pointer flex-col justify-between rounded-xl border p-4 transition-all ${
                          isSelected
                            ? 'border-signal bg-signal/5 shadow-md shadow-signal/10 ring-1 ring-signal'
                            : 'border-line bg-raised/40 hover:border-line-dim hover:bg-raised/70'
                        }`}
                      >
                        {plan.id === 'pro' && (
                          <span className="absolute -top-2.5 right-3 rounded-full bg-signal px-2 py-0.5 text-[10px] font-semibold text-black">
                            POPULAR
                          </span>
                        )}
                        <div>
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-bold text-ink">{plan.name}</span>
                            {isCurrent && (
                              <span className="rounded bg-raised px-1.5 py-0.5 text-[10px] text-ink-dim">
                                {language === 'zh' ? '当前使用' : 'Current'}
                              </span>
                            )}
                          </div>
                          <div className="mt-2 flex items-baseline gap-1">
                            <span className="text-2xl font-black tracking-tight text-ink">
                              {plan.price_usdt}
                            </span>
                            <span className="text-xs font-semibold text-ink-dim">
                              USDT / {plan.duration_days} {language === 'zh' ? '天' : 'days'}
                            </span>
                          </div>
                          <p className="mt-2 text-xs text-ink-dim line-clamp-2">
                            {plan.description}
                          </p>
                        </div>

                        <div className="mt-4 flex flex-col gap-1.5 border-t border-line/60 pt-3 text-xs text-ink-dim">
                          <div className="flex items-center justify-between">
                            <span>{language === 'zh' ? '独立环境配额' : 'Profiles Limit'}</span>
                            <span className="font-semibold text-ink">{plan.max_profiles}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>{language === 'zh' ? '同时多开窗口' : 'Max Concurrent'}</span>
                            <span className="font-semibold text-ink">{plan.max_concurrent}</span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
              </div>

              {/* Action buttons */}
              <div className="mt-4 flex items-center justify-between border-t border-line pt-4">
                <div className="text-xs text-ink-dim">
                  {selectedPlan && (
                    <span>
                      {language === 'zh' ? '应付款项：' : 'Total due: '}
                      <strong className="text-signal text-sm">{selectedPlan.price_usdt} USDT</strong>
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <button onClick={onClose} className="btn btn-secondary text-xs">
                    {language === 'zh' ? '取消' : 'Cancel'}
                  </button>
                  <button
                    onClick={handleCreateOrder}
                    disabled={!selectedPlan || creatingOrder}
                    className="btn btn-primary flex items-center gap-1.5 text-xs font-medium"
                  >
                    {creatingOrder ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <>
                        <Wallet size={14} />
                        {language === 'zh' ? '立即通过 USDT 支付' : 'Pay with USDT'}
                        <ArrowRight size={13} />
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
