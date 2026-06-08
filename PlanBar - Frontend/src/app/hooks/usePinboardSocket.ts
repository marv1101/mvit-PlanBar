import { useEffect, useRef, useCallback } from 'react';
import api from '../lib/api';
import { PinboardMessage } from '../types';
import { pinboardMessageFromResponse } from '../lib/mappers';

type MessageHandler = (message: PinboardMessage) => void;

interface UsePinboardSocketOptions {
  threadId: string | null;
  onNewMessage?: MessageHandler;
  enabled?: boolean;
}

export function usePinboardSocket({ threadId, onNewMessage, enabled = true }: UsePinboardSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const tokenRef = useRef<string | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const mountedRef = useRef(true);

  const connect = useCallback(async () => {
    if (!threadId || !enabled) return;
    if (!mountedRef.current) return;

    try {
      const { data } = await api.get('/pinboard/ws-token');
      tokenRef.current = data.token;
    } catch {
      return;
    }

    if (!mountedRef.current) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/api/v1/pinboard/ws/threads/${threadId}?token=${encodeURIComponent(tokenRef.current)}`;

    wsRef.current = new WebSocket(url);

    wsRef.current.onopen = () => {};

    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message' && data.message && onNewMessage) {
          onNewMessage(pinboardMessageFromResponse(data.message));
        }
      } catch {}
    };

    wsRef.current.onclose = () => {
      if (mountedRef.current && enabled) {
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      }
    };

    wsRef.current.onerror = () => {
      wsRef.current?.close();
    };
  }, [threadId, onNewMessage, enabled]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);
}
