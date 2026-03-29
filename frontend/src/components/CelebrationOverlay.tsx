import { useEffect } from 'react'
import confetti from 'canvas-confetti'

interface CelebrationOverlayProps {
  show: boolean
  onClose: () => void
}

export function CelebrationOverlay({ show, onClose }: CelebrationOverlayProps) {
  useEffect(() => {
    if (!show) return
    confetti({ particleCount: 90, spread: 60, origin: { y: 0.4 } })
    const timer = window.setTimeout(onClose, 3000)
    return () => window.clearTimeout(timer)
  }, [show, onClose])

  if (!show) return null
  return (
    <div className="fixed top-6 right-6 z-40 bg-[rgba(0,200,150,0.15)] border border-brand text-ink-primary rounded-xl p-3 animate-fade-in">
      Strong candidate! This profile matches approved drugs.
    </div>
  )
}
