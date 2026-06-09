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

const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_BASE_DELAY = 1000;
const RECONNECT_MAX_DELAY = 30000;

export function usePinboardSocket({ threadId, onNewMessage, enabled = true }: UsePinboardSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const tokenRef = useRef<string | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const mountedRef = useRef(true);
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(async () => {
    if (!threadId || !enabled) return;
    if (!mountedRef.current) return;

    try {
      const { data } = await api.get('/pinboard/ws-token');
      tokenRef.current = data.token;
    } catch (err) {
      console.error('[WS] Token fetch failed:', err);
      scheduleReconnect();
      return;
    }

    if (!mountedRef.current) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/api/v1/pinboard/ws/threads/${threadId}?token=${encodeURIComponent(tokenRef.current)}`;

    wsRef.current = new WebSocket(url);

    wsRef.current.onopen = () => {
      reconnectAttemptsRef.current = 0;
    };

    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message' && data.message && onNewMessage) {
          onNewMessage(pinboardMessageFromResponse(data.message));
        }
      } catch {}
    };

    wsRef.current.onclose = (event) => {
      if (event.code !== 1000) {
        console.warn(`[WS] Connection closed: code=${event.code} reason="${event.reason}"`);
      }
      if (mountedRef.current && enabled) {
        scheduleReconnect();
      }
    };

    wsRef.current.onerror = () => {
      wsRef.current?.close();
    };
  }, [threadId, onNewMessage, enabled]);

  function scheduleReconnect() {
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      console.error(`[WS] Max reconnect attempts (${MAX_RECONNECT_ATTEMPTS}) reached. Giving up.`);
      return;
    }

    const delay = Math.min(
      RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttemptsRef.current),
      RECONNECT_MAX_DELAY,
    );
    reconnectAttemptsRef.current += 1;
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`);

    reconnectTimeoutRef.current = setTimeout(connect, delay);
  }

  useEffect(() => {
    mountedRef.current = true;
    reconnectAttemptsRef.current = 0;
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
