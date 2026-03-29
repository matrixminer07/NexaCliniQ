import { useRef, useCallback } from 'react'

const STALE_MS = 5 * 60 * 1000

export function useTabCache<T>() {
  const cache = useRef<Map<string, { data: T; ts: number }>>(new Map())
  const get = useCallback((key: string): T | null => {
    const e = cache.current.get(key)
    if (!e || Date.now() - e.ts > STALE_MS) {
      cache.current.delete(key)
      return null
    }
    return e.data
  }, [])
  const set = useCallback((key: string, data: T) => {
    cache.current.set(key, { data, ts: Date.now() })
  }, [])
  const invalidate = useCallback((key: string) => {
    cache.current.delete(key)
  }, [])
  return { get, set, invalidate }
}
