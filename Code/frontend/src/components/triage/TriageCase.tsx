/**
 * TriageCase
 *
 * Primary clinical decision interface.
 * Renders case data and a submit-intercepted triage decision form.
 *
 * Submit is gated: if a Hard Nudge is pending, the modal fires before
 * the decision is finalized. If no nudge is pending, submit proceeds directly.
 */

import { useState } from 'react';
import { HardNudge } from '@/components/nudges/HardNudge';
import { SoftNudge } from '@/components/nudges/SoftNudge';
import { ExperimentalStimulus } from './ExperimentalStimulus';
import { useNudge } from '@/hooks/useNudge';
import type { TriageCase as TriageCaseType, TriageDecision } from '@/types';

interface Props {
  triageCase: TriageCaseType;
  sessionId: number;
  onDecisionSubmit: (
    decision: TriageDecision,
    nudgeFired: boolean,
    preNudgeDecision?: TriageDecision,
  ) => void;
}

const DECISION_OPTIONS: TriageDecision[] = ['high', 'moderate', 'low', 'stable'];

// Subtle per-phase theming — not labelled, just perceptibly different.
function phaseTheme(nudgeActive: boolean) {
  return nudgeActive
    ? { sectionBorder: '#fde68a', submitBg: '#92400e', progressDot: '#b45309' }
    : { sectionBorder: '#e5e7eb', submitBg: '#1d4ed8', progressDot: '#9ca3af' };
}

export function TriageCase({ triageCase, sessionId, onDecisionSubmit }: Props) {
  const theme = phaseTheme(triageCase.nudgeActive);
  const [selectedDecision, setSelectedDecision] = useState<TriageDecision>('moderate');
  // Stores the decision selected when Submit was first attempted (before any nudge)
  const [preNudgeDecision, setPreNudgeDecision] = useState<TriageDecision | null>(null);
  const { pendingHardNudge, activeSoftNudge, hasHardNudge, hasSoftNudge } = useNudge();

  const handleSubmitAttempt = () => {
    if (hasHardNudge) {
      // Record the pre-nudge intent, modal will intercept
      setPreNudgeDecision(selectedDecision);
    } else {
      onDecisionSubmit(selectedDecision, false);
    }
  };

  const handleNudgeConfirm = (finalDecision: TriageDecision) => {
    const pre = preNudgeDecision;
    setPreNudgeDecision(null);
    onDecisionSubmit(finalDecision, true, pre ?? undefined);
  };

  return (
    <ExperimentalStimulus triageCase={triageCase}>
      <div style={styles.container}>
        {/* Case header */}
        <header style={styles.caseHeader}>
          <h2 style={styles.caseTitle}>{triageCase.chiefComplaint}</h2>
          <span style={styles.patientLabel}>{triageCase.patientLabel}</span>
        </header>

        {/* Vitals — Soft Nudge target */}
        <section id="objective-data-panel" style={{ ...styles.section, borderColor: theme.sectionBorder }}>
          <h3 style={styles.sectionTitle}>Objective Findings</h3>
          <div style={styles.vitalsGrid}>
            {Object.entries(triageCase.vitals).map(([key, val]) => (
              <div key={key} style={styles.vitalItem}>
                <span style={styles.vitalKey}>{key}</span>
                <span style={styles.vitalVal}>{val}</span>
              </div>
            ))}
          </div>
          <ul style={styles.findingsList}>
            {triageCase.objectiveFindings.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </section>

        {/* Decision */}
        <section style={{ ...styles.section, borderColor: theme.sectionBorder }}>
          <h3 style={styles.sectionTitle}>Triage Decision</h3>
          <div style={styles.decisionRow}>
            {DECISION_OPTIONS.map((opt) => (
              <label key={opt} style={styles.decisionOption}>
                <input
                  type="radio"
                  name="triage-decision"
                  value={opt}
                  checked={selectedDecision === opt}
                  onChange={() => setSelectedDecision(opt)}
                />
                {opt.charAt(0).toUpperCase() + opt.slice(1)}
              </label>
            ))}
          </div>
          <button
            style={{ ...styles.submitBtn, background: theme.submitBg }}
            onClick={handleSubmitAttempt}
          >
            Submit Decision
          </button>
        </section>

        {/* Soft Nudge (ambient — no interruption) */}
        {hasSoftNudge && activeSoftNudge && <SoftNudge nudge={activeSoftNudge} />}

        {/* Hard Nudge (modal — blocks submit; only shown after submit attempt) */}
        {hasHardNudge && pendingHardNudge && preNudgeDecision !== null && (
          <HardNudge
            nudge={pendingHardNudge}
            sessionId={sessionId}
            originalDecision={preNudgeDecision}
            onConfirm={handleNudgeConfirm}
          />
        )}
      </div>
    </ExperimentalStimulus>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { maxWidth: 720, margin: '0 auto', padding: 32 },
  caseHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 24 },
  caseTitle: { fontSize: 22, fontWeight: 700, margin: 0 },
  patientLabel: { fontSize: 13, color: '#6b7280', background: '#f3f4f6', borderRadius: 4, padding: '2px 8px' },
  section: { marginBottom: 28, padding: 20, border: '1px solid #e5e7eb', borderRadius: 8 },
  sectionTitle: { fontSize: 14, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5, color: '#6b7280', marginTop: 0, marginBottom: 16 },
  vitalsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 12, marginBottom: 16 },
  vitalItem: { display: 'flex', flexDirection: 'column' },
  vitalKey: { fontSize: 11, color: '#9ca3af', fontWeight: 600, textTransform: 'uppercase' },
  vitalVal: { fontSize: 18, fontWeight: 700, color: '#111827' },
  findingsList: { margin: 0, paddingLeft: 20, fontSize: 14, color: '#374151', lineHeight: 1.7 },
  decisionRow: { display: 'flex', gap: 20, marginBottom: 20 },
  decisionOption: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 15, cursor: 'pointer' },
  submitBtn: {
    padding: '10px 28px', background: '#1d4ed8', color: '#fff',
    border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 600, cursor: 'pointer',
  },
};
