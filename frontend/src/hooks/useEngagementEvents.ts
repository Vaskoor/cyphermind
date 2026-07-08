'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { wsUrl } from '@/lib/api';
import type { EngagementEvent } from '@/lib/types';

interface UseEngagementEventsOptions {
  engagementId: string;
  enabled?: boolean;
  onEvent?: (event: EngagementEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

interface UseEngagementEventsResult {
  connected: boolean;
  lastEvent: EngagementEvent | null;
  events: EngagementEvent[];
  reconnect: () => void;
}

export function useEngagementEvents({
  engagementId,
  enabled = true,
  onEvent,
  onConnect,
  onDisconnect,
  onError,
}: UseEngagementEventsOptions): UseEngagementEventsResult {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<EngagementEvent | null>(null);
  const [events, setEvents] = useState<EngagementEvent[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const reconnectAttemptRef = useRef(0);

  const callbacksRef = useRef({ onEvent, onConnect, onDisconnect, onError });
  callbacksRef.current = { onEvent, onConnect, onDisconnect, onError };

  const connect = useCallback(() => {
    if (!engagementId || !enabled) return;

    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const token =
      typeof window !== 'undefined' ? localStorage.getItem('cyphermind_token') : null;
    const url = `${wsUrl(`/ws/engagements/${engagementId}`)}${token ? `?token=${token}` : ''}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectAttemptRef.current = 0;
        callbacksRef.current.onConnect?.();
      };

      ws.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data) as EngagementEvent;
          setLastEvent(event);
          setEvents((prev) => [event, ...prev].slice(0, 100));
          callbacksRef.current.onEvent?.(event);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        callbacksRef.current.onDisconnect?.();
        wsRef.current = null;

        if (enabled) {
          const delay = Math.min(1000 * 2 ** reconnectAttemptRef.current, 30000);
          reconnectAttemptRef.current += 1;
          reconnectTimerRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = (error) => {
        callbacksRef.current.onError?.(error);
      };
    } catch {
      setConnected(false);
    }
  }, [engagementId, enabled]);

  const reconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    reconnectAttemptRef.current = 0;
    connect();
  }, [connect]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      wsRef.current?.close();
      wsRef.current = null;
      setConnected(false);
    }

    return () => {
      clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect, enabled]);

  return { connected, lastEvent, events, reconnect };
}
