/**
 * IATAdministrator
 *
 * Orchestrates three sequential 7-block IATs (age → gender → race):
 *  1. Fetches block structure for the current bias dimension
 *  2. Steps through each stimulus using IATStimulus
 *  3. Posts each response with bias_type attached
 *  4. Calls /iat/complete (with bias_type) when all 7 blocks finish
 *  5. Shows a between-tests transition screen, then starts the next IAT
 *  6. Calls onComplete() after all three are done
 */

import { useEffect, useState } from 'react';
import { IATStimulus } from './IATStimulus';
import { fetchIATBlocks, postTrialResponse, completeIAT } from '@/services/apiService';
import { useAdaptiveStore } from '@/store/adaptiveStore';
import type { BiasType, IATBlock } from '@/types';

// ─── Bias type config ────────────────────────────────────────────────────────

const BIAS_TYPES: BiasType[] = ['age', 'gender', 'race'];

const BIAS_META: Record<BiasType, { title: string; description: string; pair: string }> = {
  age: {
    title: 'Age',
    description: 'measures unconscious associations between patient age groups (Elderly / Young) and clinical severity',
    pair: 'Elderly / Young',
  },
  gender: {
    title: 'Gender',
    description: 'measures unconscious associations between patient gender (Male / Female) and clinical severity',
    pair: 'Male / Female',
  },
  race: {
    title: 'Race',
    description: 'measures unconscious associations between patient race (White / Black) and clinical severity',
    pair: 'White / Black',
  },
};

// ─── Types ───────────────────────────────────────────────────────────────────

interface Props {
  sessionId: number;
  userId: number;
  onComplete: () => void;
}

type Phase = 'loading' | 'instructions' | 'running' | 'break' | 'between_tests' | 'error';

// ─── Component ───────────────────────────────────────────────────────────────

export function IATAdministrator({ sessionId, userId, onComplete }: Props) {
  const [phase, setPhase]           = useState<Phase>('loading');
  const [blocks, setBlocks]         = useState<IATBlock[]>([]);
  const [blockIdx, setBlockIdx]     = useState(0);
  const [trialIdx, setTrialIdx]     = useState(0);
  const [biasTypeIdx, setBiasTypeIdx] = useState(0);
  const [error, setError]           = useState<string | null>(null);

  const setIATPhase = useAdaptiveStore((s) => s.setIATPhase);

  const currentBiasType = BIAS_TYPES[biasTypeIdx];
  const currentMeta     = BIAS_META[currentBiasType];

  // ── Load blocks for the current bias type ──────────────────────────────────
  async function loadBlocks(biasType: BiasType) {
    setPhase('loading');
    setBlocks([]);
    setBlockIdx(0);
    setTrialIdx(0);
    try {
      const b = await fetchIATBlocks(sessionId, biasType);
      setBlocks(b);
      setPhase('instructions');
    } catch (e) {
      setError((e as Error).message);
      setPhase('error');
    }
  }

  // Load first IAT on mount
  useEffect(() => {
    setIATPhase('in_progress');
    loadBlocks('age');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Trial response handler ─────────────────────────────────────────────────
  const handleResponse = async (responseKey: string, rtMs: number, isCorrect: boolean) => {
    const block    = blocks[blockIdx];
    const stimulus = block.stimuli[trialIdx];

    await postTrialResponse({
      session_id:        sessionId,
      bias_type:         currentBiasType,
      block_number:      block.block_number,
      trial_number:      stimulus.trial_number,
      stimulus_word:     stimulus.word,
      stimulus_category: stimulus.category,
      correct_key:       stimulus.correct_key,
      response_key:      responseKey,
      reaction_time_ms:  rtMs,
      is_correct:        isCorrect,
      presented_at:      new Date(Date.now() - rtMs).toISOString(),
    }).catch(() => {/* best-effort */});

    const nextTrial = trialIdx + 1;
    if (nextTrial < block.stimuli.length) {
      setTrialIdx(nextTrial);
      return;
    }

    const nextBlock = blockIdx + 1;
    if (nextBlock < blocks.length) {
      setBlockIdx(nextBlock);
      setTrialIdx(0);
      setPhase('break');
      return;
    }

    // ── All 7 blocks of this IAT are done ──────────────────────────────────
    try {
      await completeIAT(sessionId, userId, currentBiasType);
    } catch {/* non-fatal */}

    const nextBiasIdx = biasTypeIdx + 1;
    if (nextBiasIdx < BIAS_TYPES.length) {
      setBiasTypeIdx(nextBiasIdx);
      setPhase('between_tests');
    } else {
      setIATPhase('complete');
      onComplete();
    }
  };

  // ── Derived ───────────────────────────────────────────────────────────────
  const block    = blocks[blockIdx];
  const stimulus = block?.stimuli[trialIdx];

  // ── Render ────────────────────────────────────────────────────────────────

  if (phase === 'loading') return <CenteredMessage>Loading IAT…</CenteredMessage>;
  if (phase === 'error')   return <CenteredMessage>Error: {error}</CenteredMessage>;

  if (phase === 'instructions') {
    const testNum = biasTypeIdx + 1;
    return (
      <div style={styles.card}>
        <div style={styles.stepBadge}>Test {testNum} of {BIAS_TYPES.length}</div>
        <h2 style={styles.heading}>
          {currentMeta.title} Implicit Association Test
        </h2>
        <p style={styles.body}>
          This task {currentMeta.description}. The demographic pair for this test
          is <strong>{currentMeta.pair}</strong>.
        </p>
        <p style={styles.body}>
          Words will appear one at a time in the centre of the screen.
          Press <kbd style={styles.kbd}>E</kbd> for the category on the left and{' '}
          <kbd style={styles.kbd}>I</kbd> for the category on the right.
          Respond as <strong>quickly and accurately</strong> as possible.
        </p>
        <p style={styles.body}>
          If you press the wrong key an error message will appear — correct it before moving on.
        </p>
        <p style={styles.footnote}>
          Your results personalise the system's sensitivity only. They are not a judgement
          of your clinical competence. This test takes approximately 5–7 minutes.
        </p>
        <button style={styles.primaryBtn} onClick={() => setPhase('running')}>
          Begin Test {testNum}
        </button>
      </div>
    );
  }

  if (phase === 'between_tests') {
    const completedType = BIAS_TYPES[biasTypeIdx - 1];
    const completedMeta = BIAS_META[completedType];
    const nextMeta      = BIAS_META[BIAS_TYPES[biasTypeIdx]];
    const testNum       = biasTypeIdx + 1;
    return (
      <div style={styles.card}>
        {/* Progress dots */}
        <div style={styles.progressRow}>
          {BIAS_TYPES.map((t, i) => (
            <div
              key={t}
              style={{
                ...styles.dot,
                background: i < biasTypeIdx ? '#16a34a' : i === biasTypeIdx ? '#1d4ed8' : '#d1d5db',
              }}
            />
          ))}
        </div>

        <div style={styles.checkRow}>
          <span style={styles.checkIcon}>✓</span>
          <span style={styles.checkText}>
            {completedMeta.title} IAT complete
          </span>
        </div>

        <h2 style={styles.heading}>
          Next: {nextMeta.title} IAT ({testNum} of {BIAS_TYPES.length})
        </h2>
        <p style={styles.body}>
          The next test {nextMeta.description}.
          The demographic pair will be <strong>{nextMeta.pair}</strong>.
        </p>
        <p style={styles.footnote}>Take a short break if needed before continuing.</p>

        <button
          style={styles.primaryBtn}
          onClick={() => loadBlocks(BIAS_TYPES[biasTypeIdx])}
        >
          Continue to {nextMeta.title} IAT
        </button>
      </div>
    );
  }

  if (phase === 'break') {
    const nextBlock = blocks[blockIdx];
    return (
      <div style={styles.card}>
        <h3 style={styles.heading}>Block {blockIdx} complete</h3>
        {nextBlock && (
          <p style={styles.body}>
            Next: Press <kbd style={styles.kbd}>E</kbd> for{' '}
            <strong>{nextBlock.left_label}</strong> and{' '}
            <kbd style={styles.kbd}>I</kbd> for{' '}
            <strong>{nextBlock.right_label}</strong>.
          </p>
        )}
        <button style={styles.primaryBtn} onClick={() => setPhase('running')}>
          Continue
        </button>
      </div>
    );
  }

  if (phase === 'running' && stimulus && block) {
    return (
      <div style={styles.runner}>
        <div style={styles.runnerHeader}>
          <span style={styles.progressLabel}>
            {currentMeta.title} IAT — Block {block.block_number} / {blocks.length}
            {' '}— Trial {trialIdx + 1} / {block.stimuli.length}
            {block.is_practice && ' (Practice)'}
          </span>
          <div style={styles.progressRow}>
            {BIAS_TYPES.map((t, i) => (
              <div
                key={t}
                style={{
                  ...styles.dot,
                  background: i < biasTypeIdx ? '#16a34a' : i === biasTypeIdx ? '#1d4ed8' : '#d1d5db',
                }}
              />
            ))}
          </div>
        </div>
        <IATStimulus
          stimulus={stimulus}
          leftLabel={block.left_label}
          rightLabel={block.right_label}
          onResponse={handleResponse}
        />
      </div>
    );
  }

  return null;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function CenteredMessage({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
      <p style={{ color: '#6b7280' }}>{children}</p>
    </div>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  card: {
    maxWidth: 560,
    margin: '60px auto',
    padding: '40px 36px',
    lineHeight: 1.7,
    fontSize: 15,
    background: '#fff',
    borderRadius: 12,
    boxShadow: '0 1px 3px rgba(0,0,0,.08), 0 4px 16px rgba(0,0,0,.06)',
  },
  stepBadge: {
    display: 'inline-block',
    marginBottom: 12,
    padding: '3px 10px',
    background: '#eff6ff',
    color: '#1d4ed8',
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 600,
    letterSpacing: 0.3,
  },
  heading: {
    margin: '0 0 14px',
    fontSize: 20,
    fontWeight: 700,
    color: '#111827',
  },
  body: {
    margin: '0 0 12px',
    color: '#374151',
  },
  footnote: {
    margin: '16px 0 20px',
    color: '#9ca3af',
    fontSize: 13,
  },
  primaryBtn: {
    marginTop: 8,
    padding: '12px 32px',
    background: '#1d4ed8',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
  },
  kbd: {
    padding: '1px 6px',
    background: '#f3f4f6',
    border: '1px solid #d1d5db',
    borderRadius: 4,
    fontFamily: 'monospace',
    fontSize: 13,
  },
  progressRow: {
    display: 'flex',
    gap: 6,
    marginBottom: 20,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
  },
  checkRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  checkIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 24,
    height: 24,
    background: '#dcfce7',
    color: '#16a34a',
    borderRadius: '50%',
    fontSize: 13,
    fontWeight: 700,
    flexShrink: 0,
  },
  checkText: {
    color: '#16a34a',
    fontWeight: 600,
    fontSize: 14,
  },
  runner: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    padding: 24,
  },
  runnerHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  progressLabel: {
    fontSize: 12,
    color: '#9ca3af',
  },
};
