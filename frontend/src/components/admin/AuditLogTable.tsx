import { Fragment, useState } from 'react'
import { TableSkeleton } from '@/components/skeletons/TableSkeleton'

type AuditRow = {
  id: string
  timestamp: string
  user?: string
  path: string
  method: string
  status: number
  response_ms?: number
  request_body?: unknown
}

type AuditLogTableProps = {
  rows: AuditRow[]
  loading: boolean
  error: string | null
}

export function AuditLogTable({ rows, loading, error }: AuditLogTableProps) {
  const [expanded, setExpanded] = useState<string | null>(null)

  if (loading) return <TableSkeleton rows={6} />
  if (error) return <div className="rounded-md border p-3 text-sm" style={{ borderColor: 'var(--color-border-tertiary)' }}>{error}</div>

  return (
    <div className="rounded-xl border" style={{ background: 'var(--color-background-primary)', borderColor: 'var(--color-border-tertiary)' }}>
      <div className="flex items-center justify-between px-4 py-3">
        <h3 className="text-base font-medium">Audit log explorer</h3>
        <button type="button" className="btn-ghost">Export</button>
      </div>
      <table className="w-full text-sm">
        <thead style={{ background: 'var(--color-background-secondary)' }}>
          <tr className="h-9 text-xs uppercase" style={{ letterSpacing: '0.05em', color: 'var(--color-text-secondary)' }}>
            <th className="px-3 text-left">Timestamp</th>
            <th className="px-3 text-left">Endpoint</th>
            <th className="px-3 text-left">Method</th>
            <th className="px-3 text-left">Status</th>
            <th className="px-3 text-left">Response</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <Fragment key={row.id}>
              <tr
                className="h-11 cursor-pointer border-b"
                style={{ borderColor: 'var(--color-border-tertiary)' }}
                onClick={() => setExpanded((prev) => (prev === row.id ? null : row.id))}
              >
                <td className="px-3">{new Date(row.timestamp).toLocaleString('en-IN')}</td>
                <td className="px-3">{row.path}</td>
                <td className="px-3">{row.method}</td>
                <td className="px-3">{row.status}</td>
                <td className="px-3">{row.response_ms ? `${row.response_ms}ms` : '-'}</td>
              </tr>
              {expanded === row.id ? (
                <tr>
                  <td colSpan={5} className="px-3 pb-3">
                    <pre className="rounded-md p-3 text-xs" style={{ background: 'var(--color-background-secondary)' }}>
                      {JSON.stringify(row.request_body ?? {}, null, 2)}
                    </pre>
                  </td>
                </tr>
              ) : null}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}
