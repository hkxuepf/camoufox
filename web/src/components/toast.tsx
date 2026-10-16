'use client'

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Check, Info, TriangleAlert, X } from 'lucide-react'

type ToastKind = 'ok' | 'error' | 'info'

interface Toast {
  id: number
  kind: ToastKind
  title: string
  detail?: string
}

const ToastContext = createContext<{
  toast: (kind: ToastKind, title: string, detail?: string) => void
}>({ toast: () => {} })

/** Replaces window.alert: non-blocking, stacked, self-dismissing. */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback((kind: ToastKind, title: string, detail?: string) => {
    const id = Date.now() + Math.random()
    // 永远只保留最新的这 1 个通知：新通知直接顶替并清除所有历史老通知
    setToasts([{ id, kind, title, detail }])
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        className="pointer-events-none fixed top-4 right-4 z-[9999] flex w-[360px] flex-col gap-2"
        role="status"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <ToastRow key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function ToastRow({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  useEffect(() => {
    // 2.5 秒后自动消失，避免长时间遮盖界面
    const timer = setTimeout(onDismiss, toast.kind === 'error' ? 5000 : 2500)
    return () => clearTimeout(timer)
  }, [onDismiss, toast.kind])

  const Icon = toast.kind === 'ok' ? Check : toast.kind === 'error' ? TriangleAlert : Info
  const tone =
    toast.kind === 'ok' ? 'text-ok' : toast.kind === 'error' ? 'text-danger' : 'text-ink-dim'

  return (
    <div className="dialog-in pointer-events-auto flex gap-2.5 rounded-lg border border-line bg-raised p-3 shadow-lg shadow-black/40">
      <Icon size={15} strokeWidth={2} className={`mt-px shrink-0 ${tone}`} />
      <div className="flex-1">
        <div className="font-medium">{toast.title}</div>
        {toast.detail && (
          <div className="mt-0.5 whitespace-pre-wrap break-words text-ink-dim">{toast.detail}</div>
        )}
      </div>
      <button onClick={onDismiss} aria-label="Dismiss" className="h-fit text-ink-faint hover:text-ink">
        <X size={14} strokeWidth={2} />
      </button>
    </div>
  )
}

export function useToast() {
  return useContext(ToastContext).toast
}
