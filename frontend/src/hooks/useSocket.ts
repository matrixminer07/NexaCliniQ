// src/hooks/useSocket.ts
import { useEffect, useRef, useCallback } from "react";
import { io, Socket } from "socket.io-client";

const SOCKET_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace('localhost', '127.0.0.1') ?? "http://127.0.0.1:5000";

export function useSocket() {
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    socketRef.current = io(SOCKET_URL, {
      transports: ["polling"],
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 8000,   // exponential backoff cap
    });
    return () => { socketRef.current?.disconnect(); };
  }, []);

  const emit = useCallback((event: string, data: unknown) => {
    socketRef.current?.emit(event, data);
  }, []);

  const on = useCallback((event: string, cb: (data: unknown) => void) => {
    socketRef.current?.on(event, cb);
    return () => socketRef.current?.off(event, cb);
  }, []);

  return { emit, on };
}
