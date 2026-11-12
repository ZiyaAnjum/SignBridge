/**
 * WebSocket client hook for SignBridge /ws/landmarks live inference stream.
 * 
 * Rules:
 * - Fixed 15 FPS landmark coordinate streaming.
 * - Never logs landmark arrays or payloads (privacy policy in rules.md).
 * - Automatic exponential backoff reconnection.
 * - Sends {"action":"reset"} on connect/reconnect.
 * - Full cleanup on unmount (closes socket with 1000).
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { PredictionResult } from '../types';

export type WebSocketStatus = 'connecting' | 'connected' | 'connection_lost' | 'error';

interface UseSignBridgeWebSocketOptions {
  url?: string;
  enabled?: boolean;
  onPrediction?: (result: PredictionResult) => void;
}

export interface UseSignBridgeWebSocketReturn {
  status: WebSocketStatus;
  lastPrediction: PredictionResult | null;
  serverLatencyMs: number;
  isEmergency: boolean;
  modelLoaded: boolean;
  reconnectAttempts: number;
  sendLandmarks: (landmarks: Float32Array) => void;
  resetSession: () => void;
}

const DEFAULT_WS_URL = 'ws://127.0.0.1:8000/ws/landmarks';
const INITIAL_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 10000;

export function useSignBridgeWebSocket(
  options: UseSignBridgeWebSocketOptions = {}
): UseSignBridgeWebSocketReturn {
  const { url = DEFAULT_WS_URL, enabled = true, onPrediction } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const backoffDelayRef = useRef(INITIAL_BACKOFF_MS);
  const isUnmountedRef = useRef(false);

  const onPredictionRef = useRef(onPrediction);
  onPredictionRef.current = onPrediction;

  const [status, setStatus] = useState<WebSocketStatus>('connecting');
  const [lastPrediction, setLastPrediction] = useState<PredictionResult | null>(null);
  const [serverLatencyMs, setServerLatencyMs] = useState(0);
  const [isEmergency, setIsEmergency] = useState(false);
  const [modelLoaded, setModelLoaded] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const cleanupSocket = useCallback(() => {
    if (reconnectTimeoutRef.current !== null) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      if (
        wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING
      ) {
        wsRef.current.close(1000, 'Page unmounted or disabled');
      }
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (isUnmountedRef.current || !enabled) return;

    cleanupSocket();
    setStatus('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (isUnmountedRef.current) {
          ws.close(1000);
          return;
        }
        setStatus('connected');
        backoffDelayRef.current = INITIAL_BACKOFF_MS;
        setReconnectAttempts(0);

        // Always send reset action on connection / reconnection
        try {
          ws.send(JSON.stringify({ action: 'reset' }));
        } catch {
          // Socket might have closed immediately
        }
      };

      ws.onmessage = (event: MessageEvent) => {
        if (isUnmountedRef.current) return;
        try {
          const data = JSON.parse(event.data);

          // Handle system control responses
          if (data.status === 'cleared' || data.pong) {
            return;
          }

          if (data.error) {
            console.warn('[SignBridge WS] Server message:', data.error, data.detail);
            return;
          }

          // PredictionResult payload
          const result: PredictionResult = {
            label: data.label ?? null,
            english: data.english ?? null,
            hindi: data.hindi ?? null,
            kannada: data.kannada ?? null,
            confidence: Number(data.confidence ?? 0.0),
            is_emergency: Boolean(data.is_emergency),
            top_guesses: Array.isArray(data.top_guesses) ? data.top_guesses : [],
            model_loaded: Boolean(data.model_loaded),
            state: data.state ?? null,
            inference_latency_ms: Number(data.inference_latency_ms ?? 0.0),
            reason: data.reason ?? null,
            timestamp: data.timestamp ?? Date.now(),
          };

          setLastPrediction(result);
          setServerLatencyMs(result.inference_latency_ms);
          setIsEmergency(result.is_emergency);
          setModelLoaded(result.model_loaded);

          if (onPredictionRef.current) {
            onPredictionRef.current(result);
          }
        } catch (parseErr) {
          console.error('[SignBridge WS] Failed to parse message:', parseErr);
        }
      };

      ws.onerror = () => {
        if (isUnmountedRef.current) return;
        setStatus('error');
      };

      ws.onclose = (event: CloseEvent) => {
        if (isUnmountedRef.current) return;

        // Code 1000 is clean closure (e.g. navigation or intentional close)
        if (event.code !== 1000) {
          setStatus('connection_lost');
          setReconnectAttempts((prev) => prev + 1);

          // Exponential backoff
          const delay = backoffDelayRef.current;
          backoffDelayRef.current = Math.min(delay * 2, MAX_BACKOFF_MS);

          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, delay);
        } else {
          setStatus('connection_lost');
        }
      };
    } catch {
      setStatus('error');
    }
  }, [cleanupSocket, enabled, url]);

  useEffect(() => {
    isUnmountedRef.current = false;
    if (enabled) {
      connect();
    } else {
      cleanupSocket();
    }

    return () => {
      isUnmountedRef.current = true;
      cleanupSocket();
    };
  }, [cleanupSocket, connect, enabled]);

  // Send single 225-float landmark frame (rule: NEVER log landmark coordinates)
  const sendLandmarks = useCallback((landmarks: Float32Array) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        const payload = JSON.stringify({
          landmarks: Array.from(landmarks),
        });
        ws.send(payload);
      } catch (err) {
        console.warn('[SignBridge WS] Failed to send frame');
      }
    }
  }, []);

  const resetSession = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ action: 'reset' }));
      } catch {
        // Ignored
      }
    }
    setLastPrediction(null);
    setIsEmergency(false);
  }, []);

  return {
    status,
    lastPrediction,
    serverLatencyMs,
    isEmergency,
    modelLoaded,
    reconnectAttempts,
    sendLandmarks,
    resetSession,
  };
}
