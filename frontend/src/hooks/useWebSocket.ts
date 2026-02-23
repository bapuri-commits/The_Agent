import { useEffect, useRef, useCallback, useState } from "react"

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/chat"
const RECONNECT_DELAY_MS = 3000
const MAX_RECONNECT_ATTEMPTS = 5

type WsStatus = "connecting" | "connected" | "disconnected"

interface UseWebSocketOptions {
  onMessage?: (data: Record<string, unknown>) => void
  autoConnect?: boolean
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { onMessage, autoConnect = true } = options
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectCount = useRef(0)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()
  const [status, setStatus] = useState<WsStatus>("disconnected")

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setStatus("connecting")
    const ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      setStatus("connected")
      reconnectCount.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage?.(data)
      } catch {
        // non-JSON message
      }
    }

    ws.onclose = () => {
      setStatus("disconnected")
      wsRef.current = null

      if (reconnectCount.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectCount.current++
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    ws.onerror = () => {
      ws.close()
    }

    wsRef.current = ws
  }, [onMessage])

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current)
    reconnectCount.current = MAX_RECONNECT_ATTEMPTS
    wsRef.current?.close()
    wsRef.current = null
    setStatus("disconnected")
  }, [])

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  useEffect(() => {
    if (autoConnect) connect()
    return () => disconnect()
  }, [autoConnect, connect, disconnect])

  return { status, send, connect, disconnect }
}
