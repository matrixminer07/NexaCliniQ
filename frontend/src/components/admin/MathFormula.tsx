type MathFormulaProps = {
  title: string
  formula: string
  value?: string
}

export function MathFormula({ title, formula, value }: MathFormulaProps) {
  return (
    <div className="rounded-md border p-3" style={{ borderColor: 'var(--color-border-tertiary)', background: 'var(--color-background-primary)' }}>
      <p className="text-xs uppercase tracking-[0.08em]" style={{ color: 'var(--color-text-secondary)' }}>
        {title}
      </p>
      <p className="mt-1 text-sm" style={{ color: 'var(--color-text-primary)' }} dangerouslySetInnerHTML={{ __html: formula }} />
      {value ? (
        <p className="mt-2 text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
          {value}
        </p>
      ) : null}
    </div>
  )
}
