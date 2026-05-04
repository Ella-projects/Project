/**
 * Calibration
 *
 * Collects motor baseline data over 30 seconds of free mouse movement.
 * Computes per-window tortuosity locally and submits the values to
 * /profile/{userId}/baseline to establish the user's D-Score Baseline.
 *
 * The user sees a simple guided task (follow the moving dot) to produce
 * naturalistic movement without cognitive load.
 */

import { useEffect, useRef, useState } from 'react';
import { submitBaseline } from '@/services/apiService';

const DURATION_MS = 30_000;
const WINDOW_MS = 5_000;
const MIN_POINTS = 10;

interface Point { x: number; y: number; t: number }

function tortuosity(points: Point[]): number {
  if (points.length < 2) return 1;
  let pathLen = 0;
  for (let i = 0; i < points.length - 1; i++) {
    const dx = points[i + 1].x - points[i].x;
    const dy = points[i + 1].y - points[i].y;
    pathLen += Math.sqrt(dx * dx + dy * dy);
  }
  const dx = points[points.length - 1].x - points[0].x;
  const dy = points[points.length - 1].y - points[0].y;
  const displacement = Math.sqrt(dx * dx + dy * dy);
  return displacement < 0.001 ? pathLen || 1 : pathLen / displacement;
}

interface Props {
  userId: number;
  onComplete: () => void;
}

export function Calibration({ userId, onComplete }: Props) {
  const [phase, setPhase] = useState<'instructions' | 'running' | 'submitting' | 'done'>('instructions');
  const [remaining, setRemaining] = useState(DURATION_MS / 1000);
  const [dotPos, setDotPos] = useState({ x: 50, y: 50 }); // percent
  const bufferRef = useRef<Point[]>([]);
  const windowsRef = useRef<Point[][]>([]);
  const windowStartRef = useRef<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // Animate the target dot on a Lissajous path
  useEffect(() => {
    if (phase !== 'running') return;
    const start = performance.now();
    let raf: number;
    const animate = (now: number) => {
      const t = (now - start) / 1000;
      setDotPos({
        x: 50 + 35 * Math.sin(t * 0.7),
        y: 50 + 30 * Math.sin(t * 0.5 + 1),
      });
      raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [phase]);

  // Countdown timer
  useEffect(() => {
    if (phase !== 'running') return;
    const interval = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          clearInterval(interval);
          finish();
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [phase]);

  // Mouse tracking
  useEffect(() => {
    if (phase !== 'running') return;
    windowStartRef.current = performance.now();

    const onMove = (e: MouseEvent) => {
      const now = performance.timeOrigin + performance.now();
      bufferRef.current.push({ x: e.clientX, y: e.clientY, t: now });

      const elapsed = performance.now() - windowStartRef.current;
      if (elapsed >= WINDOW_MS) {
        if (bufferRef.current.length >= MIN_POINTS) {
          windowsRef.current.push([...bufferRef.current]);
        }
        bufferRef.current = [];
        windowStartRef.current = performance.now();
      }
    };

    window.addEventListener('mousemove', onMove, { passive: true });
    return () => window.removeEventListener('mousemove', onMove);
  }, [phase]);

  const finish = async () => {
    // Flush remaining buffer
    if (bufferRef.current.length >= MIN_POINTS) {
      windowsRef.current.push([...bufferRef.current]);
    }

    const tauValues = windowsRef.current.map(tortuosity);

    if (tauValues.length < 2) {
      // Not enough data — skip baseline, proceed anyway
      onComplete();
      return;
    }

    setPhase('submitting');
    try {
      await submitBaseline(userId, tauValues);
    } catch {
      // Non-fatal — proceed without baseline
    }
    setPhase('done');
    onComplete();
  };

  if (phase === 'instructions') {
    return (
      <div style={styles.center}>
        <h2 style={styles.title}>Motor Calibration</h2>
        <p style={styles.body}>
          Before your session begins, we need to establish your baseline movement profile.
        </p>
        <p style={styles.body}>
          For the next <strong>30 seconds</strong>, move your mouse to follow the blue dot
          as it moves around the screen. Move naturally — there is no correct speed.
        </p>
        <button style={styles.btn} onClick={() => setPhase('running')}>
          Start Calibration
        </button>
      </div>
    );
  }

  if (phase === 'submitting') {
    return <div style={styles.center}><p>Saving baseline…</p></div>;
  }

  return (
    <div ref={containerRef} style={styles.canvas}>
      <div style={styles.hud}>
        <span>Follow the dot — {remaining}s remaining</span>
        <div style={styles.progressBar}>
          <div
            style={{
              ...styles.progressFill,
              width: `${((DURATION_MS / 1000 - remaining) / (DURATION_MS / 1000)) * 100}%`,
            }}
          />
        </div>
      </div>

      {/* Target dot */}
      <div
        style={{
          ...styles.dot,
          left: `${dotPos.x}%`,
          top: `${dotPos.y}%`,
        }}
      />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  center: {
    maxWidth: 480, margin: '80px auto', padding: 32, textAlign: 'center',
  },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 16 },
  body: { fontSize: 15, color: '#374151', lineHeight: 1.7, marginBottom: 12 },
  btn: {
    marginTop: 24, padding: '12px 32px', background: '#1d4ed8', color: '#fff',
    border: 'none', borderRadius: 6, fontSize: 15, fontWeight: 600, cursor: 'pointer',
  },
  canvas: {
    position: 'relative', width: '100%', height: '100%',
    background: '#f0f4ff', overflow: 'hidden', cursor: 'none',
  },
  hud: {
    position: 'absolute', top: 24, left: '50%', transform: 'translateX(-50%)',
    background: 'rgba(255,255,255,0.9)', borderRadius: 8, padding: '10px 20px',
    fontSize: 14, fontWeight: 600, color: '#374151', textAlign: 'center', minWidth: 260,
  },
  progressBar: {
    marginTop: 8, height: 4, background: '#e5e7eb', borderRadius: 2, overflow: 'hidden',
  },
  progressFill: {
    height: '100%', background: '#1d4ed8',
    transition: 'width 1s linear', borderRadius: 2,
  },
  dot: {
    position: 'absolute',
    width: 24, height: 24,
    borderRadius: '50%',
    background: '#1d4ed8',
    transform: 'translate(-50%, -50%)',
    boxShadow: '0 0 0 6px rgba(29,78,216,0.2)',
    transition: 'left 0.1s ease, top 0.1s ease',
    pointerEvents: 'none',
  },
};
