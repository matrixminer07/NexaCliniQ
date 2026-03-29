import { TableSkeleton } from '@/components/skeletons/TableSkeleton'

type ModelVersion = {
  id?: string
  version?: string
  algorithm?: string
  training_dataset_size?: number
  val_auc?: number
  val_f1?: number
  val_brier?: number
  created_at?: string
  deployed?: boolean
}

type ModelVersionTableProps = {
  rows: ModelVersion[]
  loading: boolean
  error: string | null
  onRetrain: () => void
  onRollback: (version: string) => void
}

export function ModelVersionTable({ rows, loading, error, onRetrain, onRollback }: ModelVersionTableProps) {
  if (loading) return <TableSkeleton rows={5} />
  if (error) return <div className="rounded-md border p-3 text-sm" style={{ borderColor: 'var(--color-border-tertiary)' }}>{error}</div>

  return (
    <div className="rounded-xl border" style={{ background: 'var(--color-background-primary)', borderColor: 'var(--color-border-tertiary)' }}>
      <div className="flex items-center justify-between px-4 py-3">
        <h3 className="text-base font-medium">Model versions</h3>
        <button type="button" className="btn-ghost" onClick={onRetrain}>Trigger retrain</button>
      </div>
      <table className="w-full text-sm">
        <thead style={{ background: 'var(--color-background-secondary)' }}>
          <tr className="h-9 text-xs uppercase" style={{ letterSpacing: '0.05em', color: 'var(--color-text-secondary)' }}>
            <th className="px-3 text-left">Version</th>
            <th className="px-3 text-left">Algorithm</th>
            <th className="px-3 text-left">Dataset</th>
            <th className="px-3 text-left">Val AUC</th>
            <th className="px-3 text-left">Val F1</th>
            <th className="px-3 text-left">Brier</th>
            <th className="px-3 text-left">Status</th>
            <th className="px-3 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            const version = String(row.version ?? row.id ?? `v-${idx}`)
            return (
              <tr
                key={version}
                className="h-11 border-b"
                style={{
                  borderColor: 'var(--color-border-tertiary)',
                  background: row.deployed ? 'var(--color-background-success)' : 'transparent',
                }}
              >
                <td className="px-3">{version}</td>
                <td className="px-3">{row.algorithm ?? '-'}</td>
                <td className="px-3">{Number(row.training_dataset_size ?? 0).toLocaleString('en-IN')}</td>
                <td className="px-3">{Number(row.val_auc ?? 0).toFixed(4)}</td>
                <td className="px-3">{Number(row.val_f1 ?? 0).toFixed(4)}</td>
                <td className="px-3">{Number(row.val_brier ?? 0).toFixed(4)}</td>
                <td className="px-3">{row.deployed ? 'Deployed' : 'Staged'}</td>
                <td className="px-3">
                  <button type="button" className="btn-ghost h-7 px-2" disabled={Boolean(row.deployed)}>
                    Deploy
                  </button>
                  <button type="button" className="btn-ghost h-7 px-2" onClick={() => onRollback(version)}>
                    Rollback
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
