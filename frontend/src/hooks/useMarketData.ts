import { useEffect, useMemo, useState } from 'react'
import { api } from '@/services/api'
import type { MarketSizingResponse } from '@/types'

export function useMarketData() {
  const [data, setData] = useState<MarketSizingResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await api.marketSizing()
      setData(res)
    } catch {
      setError('Market data is currently unavailable.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const run = async () => {
      await fetchData()
    }

    run()
  }, [])

  const chartData = useMemo(() => {
    if (!data?.market) return []
    return [
      { name: 'TAM', value: Number(data.market.tam_busd || 0) },
      { name: 'SAM', value: Number(data.market.sam_busd || 0) },
      { name: 'SOM', value: Number(data.market.som_busd || 0) },
    ]
  }, [data])

  return { data, chartData, loading, error, refetch: fetchData }
}
