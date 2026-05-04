/**
 * Dashboard
 *
 * Phase routing:
 *   iat         → IATAdministrator (3 × 7-block IATs: age → gender → race)
 *   calibration → Calibration (30s motor baseline collection)
 *   orientation → TriageOrientation (task instructions before cases start)
 *   triage      → TriageCase (TelemetryCapture active, nudges live)
 *   complete    → Session complete screen
 */

import { useCallback, useState } from 'react';
import { IATAdministrator } from '@/components/iat/IATAdministrator';
import { Calibration } from '@/components/layout/Calibration';
import { TriageOrientation } from '@/components/layout/TriageOrientation';
import { TriageCase } from '@/components/triage/TriageCase';
import { TelemetryCapture } from '@/components/telemetry/TelemetryCapture';
import { useAdaptiveStore } from '@/store/adaptiveStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { endSession, fetchNextCase, submitCaseDecision } from '@/services/apiService';
import type { TriageCase as TriageCaseType, TriageDecision } from '@/types';

type AppPhase = 'iat' | 'calibration' | 'orientation' | 'triage' | 'complete';

export function Dashboard() {
  const { session, user } = useAdaptiveStore((s) => ({
    session: s.session,
    user: s.user,
  }));

  const [phase, setPhase] = useState<AppPhase>('iat');
  const [currentCase, setCurrentCase] = useState<TriageCaseType | null>(null);
  const [caseError, setCaseError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{ correct: boolean; correctDecision: string } | null>(null);

  const wsClient = useWebSocket(phase === 'triage' ? session?.id ?? null : null);

  const loadNextCase = useCallback(async () => {
    if (!session) return;
    setCaseError(null);
    setLastResult(null);
    try {
      const next = await fetchNextCase(session.id);
      setCurrentCase(next);
    } catch {
      setCaseError('No more cases — session complete.');
      setPhase('complete');
      if (session) {
        endSession(session.id).catch(() => {/* best-effort */});
      }
    }
  }, [session]);

  const handleIATComplete = () => setPhase('calibration');

  const handleCalibrationComplete = () => setPhase('orientation');

  const handleOrientationReady = () => {
    setPhase('triage');
    loadNextCase();
  };

  const handleDecisionSubmit = async (
    decision: TriageDecision,
    nudgeFired: boolean,
    preNudgeDecision?: TriageDecision,
  ) => {
    if (!session || !currentCase) return;
    const result = await submitCaseDecision(
      session.id,
      currentCase.id,
      decision,
      undefined,
      nudgeFired,
      preNudgeDecision,
    );
    setLastResult({ correct: result.is_correct, correctDecision: result.correct_decision });
    // Brief feedback then load next
    setTimeout(loadNextCase, 1800);
  };

  return (
    <div style={styles.shell}>
      <nav style={styles.nav}>
        <span style={styles.brand}>AdaptiveUI</span>
        <div style={styles.navRight}>
          {user && <span style={styles.userLabel}>{user.username}</span>}
          {session && (
            <span style={{ ...styles.phaseTag, background: '#f3f4f6', color: '#374151' }}>
              {session.nudge_order === 'control_first' ? 'A→B' : 'B→A'}
            </span>
          )}
          <span style={styles.phaseTag}>{phase}</span>
        </div>
      </nav>

      <main style={styles.main}>

        {phase === 'iat' && session && user && (
          <IATAdministrator
            sessionId={session.id}
            userId={user.id}
            onComplete={handleIATComplete}
          />
        )}

        {phase === 'calibration' && user && (
          <Calibration userId={user.id} onComplete={handleCalibrationComplete} />
        )}

        {phase === 'orientation' && (
          <TriageOrientation onReady={handleOrientationReady} />
        )}

        {phase === 'triage' && session && (
          <>
            {/* Decision feedback overlay */}
            {lastResult && (
              <div style={{ ...styles.feedbackBanner, background: lastResult.correct ? '#dcfce7' : '#fee2e2' }}>
                {lastResult.correct
                  ? 'Correct decision'
                  : `Incorrect — correct answer was: ${lastResult.correctDecision}`}
              </div>
            )}

            {currentCase ? (
              <TelemetryCapture client={wsClient}>
                <TriageCase
                  triageCase={currentCase}
                  sessionId={session.id}
                  onDecisionSubmit={handleDecisionSubmit}
                />
              </TelemetryCapture>
            ) : (
              <div style={styles.center}>
                {caseError ?? <p>Loading case…</p>}
              </div>
            )}
          </>
        )}

        {phase === 'complete' && (
          <div style={styles.center}>
            <h2>Session Complete</h2>
            <p style={{ color: '#6b7280' }}>
              All triage cases have been reviewed. Thank you.
            </p>
          </div>
        )}

      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  shell: { display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'system-ui, sans-serif' },
  nav: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '12px 24px', borderBottom: '1px solid #e5e7eb', background: '#fff', flexShrink: 0,
  },
  navRight: { display: 'flex', alignItems: 'center', gap: 12 },
  brand: { fontWeight: 700, fontSize: 16, color: '#1d4ed8' },
  userLabel: { fontSize: 13, color: '#6b7280' },
  phaseTag: {
    fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5,
    background: '#eff6ff', color: '#1d4ed8', borderRadius: 4, padding: '2px 8px',
  },
  main: { flex: 1, overflow: 'auto', background: '#f9fafb', position: 'relative' },
  feedbackBanner: {
    position: 'sticky', top: 0, zIndex: 100,
    padding: '10px 24px', fontSize: 14, fontWeight: 600, textAlign: 'center',
  },
  center: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', height: '100%', gap: 12,
  },
};
