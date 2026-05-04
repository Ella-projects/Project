/**
 * useWebSocket
 *
 * Lifecycle-manages a TelemetryClient for the active session.
 * Dispatches inbound nudge messages to the Zustand store.
 */

import { useEffect, useRef } from 'react';
import { TelemetryClient } from '@/services/telemetryService';
import { useAdaptiveStore } from '@/store/adaptiveStore';
import type { WebSocketMessage } from '@/types';

export function useWebSocket(sessionId: number | null): TelemetryClient | null {
  const clientRef = useRef<TelemetryClient | null>(null);
  const enqueueHardNudge = useAdaptiveStore((s) => s.enqueueHardNudge);
  const setActiveSoftNudge = useAdaptiveStore((s) => s.setActiveSoftNudge);
  const updateRiskScore = useAdaptiveStore((s) => s.updateRiskScore);

  useEffect(() => {
    if (!sessionId) return;

    const client = new TelemetryClient(sessionId);
    clientRef.current = client;
    client.connect();

    const unsubscribe = client.onMessage((msg: WebSocketMessage) => {
      if (msg.type === 'hard_nudge') {
        enqueueHardNudge(msg.data);
      } else if (msg.type === 'soft_nudge') {
        setActiveSoftNudge(msg.data);
      } else if (msg.type === 'window_clear') {
        updateRiskScore(msg.risk_score);
      }
    });

    return () => {
      unsubscribe();
      client.disconnect();
      clientRef.current = null;
    };
  }, [sessionId, enqueueHardNudge, setActiveSoftNudge, updateRiskScore]);

  return clientRef.current;
}
