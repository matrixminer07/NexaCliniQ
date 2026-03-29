import React, { useState, useRef, useEffect } from 'react'
import { GLOSSARY } from '@/data/glossary'
import './GlossaryTooltip.css'

export interface GlossaryTooltipProps {
  term: keyof typeof GLOSSARY
  children?: React.ReactNode
  className?: string
}

/**
 * GlossaryTooltip — renders glossary term with tooltip on hover/click.
 * Accessible via keyboard (Tab, Enter/Space to open, Escape to close).
 */
export const GlossaryTooltip: React.FC<GlossaryTooltipProps> = ({
  term,
  children,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState<'above' | 'below'>('above')
  const triggerRef = useRef<HTMLSpanElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  const glossaryEntry = GLOSSARY[term]

  // Calculate tooltip position based on available space
  const updatePosition = () => {
    if (!triggerRef.current || !tooltipRef.current) return

    const triggerRect = triggerRef.current.getBoundingClientRect()
    const tooltipRect = tooltipRef.current.getBoundingClientRect()

    // Check if there's enough space above
    const spaceAbove = triggerRect.top
    const spaceBelow = window.innerHeight - triggerRect.bottom

    if (spaceAbove >= tooltipRect.height + 10 && spaceAbove > spaceBelow) {
      setPosition('above')
    } else {
      setPosition('below')
    }
  }

  useEffect(() => {
    if (isOpen && glossaryEntry) {
      updatePosition()
      // Recheck on resize
      window.addEventListener('resize', updatePosition)
      return () => window.removeEventListener('resize', updatePosition)
    }
  }, [isOpen, glossaryEntry])

  if (!glossaryEntry) {
    return <span className={className}>{children || term}</span>
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      setIsOpen(!isOpen)
    } else if (e.key === 'Escape' && isOpen) {
      setIsOpen(false)
    }
  }

  return (
    <span className={`glossary-tooltip-wrapper ${className}`}>
      <span
        ref={triggerRef}
        className="glossary-tooltip-trigger"
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="button"
        aria-label={`Learn about ${glossaryEntry.term}`}
        aria-expanded={isOpen}
        aria-describedby={isOpen ? `tooltip-${term}` : undefined}
      >
        {children || glossaryEntry.term}
        <span className="glossary-info-icon" aria-hidden="true">
          ⓘ
        </span>
      </span>

      {isOpen && (
        <div
          ref={tooltipRef}
          id={`tooltip-${term}`}
          className={`glossary-tooltip glossary-tooltip-${position}`}
          role="tooltip"
        >
          <div className="glossary-tooltip-header">
            <strong>{glossaryEntry.term}</strong>
          </div>
          <div className="glossary-tooltip-body">{glossaryEntry.definition}</div>
          {glossaryEntry.learnMore && (
            <div className="glossary-tooltip-footer">
              <a
                href={glossaryEntry.learnMore}
                target="_blank"
                rel="noopener noreferrer"
                className="glossary-learn-more"
              >
                Learn more →
              </a>
            </div>
          )}
        </div>
      )}
    </span>
  )
}

export default GlossaryTooltip
