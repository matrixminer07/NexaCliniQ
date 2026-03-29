import { ToastItem } from '@/hooks/useToast'

type ToastContainerProps = {
  toasts: ToastItem[]
  onDismiss: (id: string) => void
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  return (
    <div className="fixed top-4 right-4 z-[70] space-y-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="min-w-[280px] max-w-[360px] rounded-md border px-3 py-2 text-sm shadow-sm transition-transform duration-300 ease-out"
          style={{
            transform: 'translateX(0)',
            borderColor: 'var(--color-border-tertiary)',
            background: 'var(--color-background-primary)',
            color:
              toast.tone === 'success'
                ? 'var(--color-text-success)'
                : toast.tone === 'error'
                  ? 'var(--color-text-danger)'
                  : 'var(--color-text-warning)',
          }}
        >
          <div className="flex items-start justify-between gap-2">
            <span>{toast.message}</span>
            <button type="button" onClick={() => onDismiss(toast.id)} className="opacity-70 hover:opacity-100">
              x
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
