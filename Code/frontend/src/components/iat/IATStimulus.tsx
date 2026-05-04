/**
 * IATStimulus
 *
 * Renders a single IAT trial stimulus and captures keyboard response (E / I).
 * Measures reaction time from stimulus onset to key press.
 * Displays an error flash on incorrect responses (correct key is revealed briefly).
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { IATStimulus as IATStimulusType } from '@/types';

interface Props {
  stimulus: IATStimulusType;
  leftLabel: string;
  rightLabel: string;
  onResponse: (responseKey: string, reactionTimeMs: number, isCorrect: boolean) => void;
}

export function IATStimulus({ stimulus, leftLabel, rightLabel, onResponse }: Props) {
  const onsetRef = useRef<number>(performance.now());
  const respondedRef = useRef(false);
  const [showError, setShowError] = useState(false);

  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      if (key !== 'e' && key !== 'i') return;
      if (respondedRef.current) return;

      respondedRef.current = true;
      const rt = Math.round(performance.now() - onsetRef.current);
      const correct = key === stimulus.correct_key.toLowerCase();

      if (!correct) {
        setShowError(true);
        setTimeout(() => {
          setShowError(false);
          respondedRef.current = false;
          // Re-trigger so user must respond correctly
          // (IAT standard: error must be corrected before advancing)
        }, 400);
        return;
      }

      onResponse(key, rt, correct);
    },
    [stimulus, onResponse],
  );

  useEffect(() => {
    onsetRef.current = performance.now();
    respondedRef.current = false;
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [handleKey]);

  return (
    <div style={styles.container}>
      {/* Key labels */}
      <div style={styles.labelRow}>
        <div style={styles.keyLabel}>
          <kbd style={styles.kbd}>E</kbd>
          <span>{leftLabel}</span>
        </div>
        <div style={{ ...styles.keyLabel, textAlign: 'right' }}>
          <span>{rightLabel}</span>
          <kbd style={styles.kbd}>I</kbd>
        </div>
      </div>

      {/* Stimulus word */}
      <div style={{ ...styles.word, color: showError ? '#dc2626' : '#111827' }}>
        {stimulus.word}
      </div>

      {showError && <p style={styles.errorMsg}>Press the correct key</p>}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', height: '100%', userSelect: 'none',
  },
  labelRow: {
    display: 'flex', justifyContent: 'space-between', width: '100%',
    maxWidth: 600, marginBottom: 48, fontSize: 15, fontWeight: 600, color: '#374151',
  },
  keyLabel: { display: 'flex', alignItems: 'center', gap: 8 },
  kbd: {
    display: 'inline-block', padding: '4px 10px',
    border: '1px solid #d1d5db', borderRadius: 4,
    background: '#f9fafb', fontSize: 13, fontFamily: 'monospace',
  },
  word: {
    fontSize: 36, fontWeight: 700, letterSpacing: 1, transition: 'color 0.15s',
  },
  errorMsg: { marginTop: 16, fontSize: 14, color: '#dc2626', fontWeight: 600 },
};
