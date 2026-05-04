/**
 * TelemetryCapture
 *
 * Invisible wrapper component that activates mouse telemetry collection
 * for all children. Attaches useTelemetry to the wrapping div.
 *
 * Usage:
 *   <TelemetryCapture client={wsClient}>
 *     <TriageCase ... />
 *   </TelemetryCapture>
 */

import { useRef } from 'react';
import { useTelemetry } from '@/hooks/useTelemetry';
import type { TelemetryClient } from '@/services/telemetryService';

interface Props {
  client: TelemetryClient | null;
  children: React.ReactNode;
}

export function TelemetryCapture({ client, children }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  useTelemetry(client, containerRef.current);

  return (
    <div ref={containerRef} style={{ height: '100%' }}>
      {children}
    </div>
  );
}
