import { io, Socket } from 'socket.io-client'
import { useEffect } from 'react'
import { useAppStore } from '@/store'
import type { FeatureSet, PredictionResponse } from '@/types'

let socket: Socket | null = null

function getSocket(): Socket {
  if (!socket) {
    socket = io('/', { path: '/socket.io', transports: ['websocket'] })
  }
  return socket
}

export function useSocketPrediction(enabled: boolean): void {
  const setPrediction = useAppStore((s) => s.setPrediction)

  useEffect(() => {
    if (!enabled) return
    const ws = getSocket()
    const onResult = (payload: PredictionResponse) => setPrediction(payload)
    ws.on('prediction_result', onResult)
    return () => {
      ws.off('prediction_result', onResult)
    }
  }, [enabled, setPrediction])
}

export function emitRealtimePrediction(features: FeatureSet): void {
  getSocket().emit('predict_realtime', features)
}

export function useSocketLiveStats(): void {
  const setLiveMetrics = useAppStore((s) => s.setLiveMetrics)

  useEffect(() => {
    const ws = getSocket()
    const onStats = (payload: { total_predictions?: number; pass_rate?: number; years_saved?: number }) => {
      setLiveMetrics({
        totalAnalysed: payload.total_predictions ?? 847,
        passRate: payload.pass_rate ?? 31,
        yearsSaved: payload.years_saved ?? 3.4,
      })
    }
    ws.on('stats_update', onStats)
    return () => {
      ws.off('stats_update', onStats)
    }
  }, [setLiveMetrics])
}
