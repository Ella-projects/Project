/**
 * useTelemetry
 *
 * Attaches mousemove listeners to a target element (or document),
 * batches points every 100ms, and forwards them to a TelemetryClient.
 *
 * Polling rate is limited by the browser's mousemove event frequency
 * (~250Hz on modern hardware). No artificial throttling is applied —
 * the backend handles variable-rate input.
 */

import { useEffect, useRef } from 'react';
import type { TelemetryClient } from '@/services/telemetryService';
import type { MousePoint } from '@/types';

const FLUSH_INTERVAL_MS = 100;

export function useTelemetry(
  client: TelemetryClient | null,
  target: HTMLElement | null = null,
): void {
  const bufferRef = useRef<MousePoint[]>([]);

  useEffect(() => {
    if (!client) return;

    const element = target ?? document;

    const onMove = (evt: Event) => {
      const e = evt as MouseEvent;
      bufferRef.current.push({ x: e.clientX, y: e.clientY, t: performance.now() + performance.timeOrigin });
    };

    element.addEventListener('mousemove', onMove, { passive: true });

    const interval = setInterval(() => {
      if (bufferRef.current.length > 0) {
        client.send(bufferRef.current);
        bufferRef.current = [];
      }
    }, FLUSH_INTERVAL_MS);

    return () => {
      element.removeEventListener('mousemove', onMove);
      clearInterval(interval);
    };
  }, [client, target]);
}
