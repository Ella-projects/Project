/**
 * HardNudge — Synchronous modal that intercepts Submit.
 *
 * Requires explicit clinician confirmation before the record can be finalized.
 * Displays the decision-rule evidence and allows the clinician to:
 *   (a) change their triage decision, or
 *   (b) confirm the original decision with acknowledgement.
 */

import { useState } from 'react';
import { useAdaptiveStore } from '@/store/adaptiveStore';
import { acknowledgeNudge } from '@/services/apiService';
import type { HardNudgePayload, TriageDecision } from '@/types';

interface Props {
  nudge: HardNudgePayload;
  sessionId: number;
  originalDecision: TriageDecision;
  onConfirm: (finalDecision: TriageDecision) => void;
}

const DECISION_OPTIONS: TriageDecision[] = ['high', 'moderate', 'low', 'stable'];

export function HardNudge({ nudge, sessionId, originalDecision, onConfirm }: Props) {
  const [selectedDecision, setSelectedDecision] = useState<TriageDecision>(originalDecision);
  const [submitting, setSubmitting] = useState(false);
  const dismissHardNudge = useAdaptiveStore((s) => s.dismissHardNudge);

  const handleConfirm = async () => {
    setSubmitting(true);
    await acknowledgeNudge({
      window_id: nudge.window_id,
      session_id: sessionId,
      original_decision: originalDecision,
      final_decision: selectedDecision,
      confirmed_at: new Date().toISOString(),
    });
    dismissHardNudge();
    onConfirm(selectedDecision);
    setSubmitting(false);
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal} role="alertdialog" aria-modal="true" aria-labelledby="nudge-title">
        <header style={styles.header}>
          <h2 id="nudge-title" style={styles.title}>
            Decision Review Required
          </h2>
          <span style={styles.riskBadge}>
            Risk: {(nudge.risk_score * 100).toFixed(0)}%
          </span>
        </header>

        <section style={styles.evidence}>
          <p style={styles.evidenceIntro}>
            The system has detected kinematic indicators of cognitive load or implicit bias.
            Please review the following evidence before finalising your triage decision.
          </p>
          <ul style={styles.evidenceList}>
            {nudge.evidence.map((item, i) => (
              <li key={i} style={styles.evidenceItem}>
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section style={styles.decisionSection}>
          <p style={styles.decisionPrompt}>Confirm or revise your triage decision:</p>
          <div style={styles.decisionOptions}>
            {DECISION_OPTIONS.map((opt) => (
              <label key={opt} style={styles.decisionLabel}>
                <input
                  type="radio"
                  name="decision"
                  value={opt}
                  checked={selectedDecision === opt}
                  onChange={() => setSelectedDecision(opt)}
                />
                <span style={opt === originalDecision ? styles.originalMarker : undefined}>
                  {opt.charAt(0).toUpperCase() + opt.slice(1)}
                  {opt === originalDecision ? ' (original)' : ''}
                </span>
              </label>
            ))}
          </div>
        </section>

        <footer style={styles.footer}>
          <button
            style={styles.confirmButton}
            onClick={handleConfirm}
            disabled={submitting}
          >
            {submitting ? 'Saving…' : 'Confirm & Continue'}
          </button>
        </footer>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed', inset: 0,
    background: 'rgba(0,0,0,0.6)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    background: '#fff', borderRadius: 8,
    maxWidth: 560, width: '90%',
    padding: 32, boxShadow: '0 8px 32px rgba(0,0,0,0.24)',
  },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  title: { margin: 0, fontSize: 20, fontWeight: 700, color: '#b91c1c' },
  riskBadge: { background: '#fef2f2', color: '#b91c1c', borderRadius: 4, padding: '4px 10px', fontWeight: 600, fontSize: 14 },
  evidence: { marginBottom: 24 },
  evidenceIntro: { fontSize: 14, color: '#374151', marginBottom: 12 },
  evidenceList: { paddingLeft: 20, margin: 0 },
  evidenceItem: { fontSize: 13, color: '#4b5563', marginBottom: 6, lineHeight: 1.5 },
  decisionSection: { marginBottom: 24 },
  decisionPrompt: { fontSize: 14, fontWeight: 600, marginBottom: 12 },
  decisionOptions: { display: 'flex', flexDirection: 'column', gap: 8 },
  decisionLabel: { display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, cursor: 'pointer' },
  originalMarker: { fontWeight: 600 },
  footer: { display: 'flex', justifyContent: 'flex-end' },
  confirmButton: {
    background: '#1d4ed8', color: '#fff', border: 'none',
    borderRadius: 6, padding: '10px 24px', fontSize: 14, fontWeight: 600,
    cursor: 'pointer',
  },
};
