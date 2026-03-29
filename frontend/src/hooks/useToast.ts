import { useCallback } from 'react'

export type ToastTone = 'success' | 'error' | 'warning'

export type ToastItem = {
  id: string
  message: string
  tone: ToastTone
}

export function useToast(setToasts: React.Dispatch<React.SetStateAction<ToastItem[]>>) {
  const push = useCallback(
    (tone: ToastTone, message: string) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      setToasts((prev) => [...prev, { id, message, tone }])
      window.setTimeout(() => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id))
      }, 4000)
    },
    [setToasts]
  )

  return {
    success: (msg: string) => push('success', msg),
    error: (msg: string) => push('error', msg),
    warning: (msg: string) => push('warning', msg),
  }
}
