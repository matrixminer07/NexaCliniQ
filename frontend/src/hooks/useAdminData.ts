import { useCallback, useEffect, useState } from 'react'
import { ZodSchema } from 'zod'
import { safeGet } from '@/lib/safeApi'

export function useAdminData<T>(endpoint: string, schema: ZodSchema<T>, refreshInterval?: number) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    try {
      const res = await safeGet(endpoint, schema)
      setData(res)
      setError(null)
    } catch {
      setError('Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [endpoint, schema])

  useEffect(() => {
    setLoading(true)
    void fetch()
    if (!refreshInterval) {
      return
    }
    const id = window.setInterval(() => {
      void fetch()
    }, refreshInterval)
    return () => window.clearInterval(id)
  }, [fetch, refreshInterval])

  return { data, loading, error, refetch: fetch }
}
