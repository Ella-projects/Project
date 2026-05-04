/**
 * Global state store (Zustand)
 *
 * Manages:
 *  - Active session and user profile
 *  - IAT phase (not_started | in_progress | complete)
 *    IATAdministrator manages its own per-block/trial state locally;
 *    the store only tracks the coarse phase used by Dashboard.
 *  - Active nudge queue
 *  - Soft nudge highlight targets
 */

import { create } from 'zustand';
import type {
  HardNudgePayload,
  Session,
  SoftNudgePayload,
  TriageCase,
  UserProfile,
} from '@/types';

type IATPhase = 'not_started' | 'in_progress' | 'complete';
type AppPhase = 'iat' | 'calibration' | 'triage';

interface AdaptiveState {
  // Identity
  user: UserProfile | null;
  session: Session | null;

  // Phase
  appPhase: AppPhase;
  /** Coarse IAT phase — IATAdministrator owns all fine-grained block/trial state */
  iatPhase: IATPhase;

  // Triage
  currentCase: TriageCase | null;

  // Nudges
  pendingHardNudge: HardNudgePayload | null;
  activeSoftNudge: SoftNudgePayload | null;
  lastRiskScore: number;

  // Actions
  setUser: (user: UserProfile) => void;
  setSession: (session: Session) => void;
  setAppPhase: (phase: AppPhase) => void;
  setIATPhase: (phase: IATPhase) => void;
  setCurrentCase: (c: TriageCase) => void;
  enqueueHardNudge: (nudge: HardNudgePayload) => void;
  dismissHardNudge: () => void;
  setActiveSoftNudge: (nudge: SoftNudgePayload | null) => void;
  updateRiskScore: (score: number) => void;
}

export const useAdaptiveStore = create<AdaptiveState>((set) => ({
  user: null,
  session: null,
  appPhase: 'iat',
  iatPhase: 'not_started',
  currentCase: null,
  pendingHardNudge: null,
  activeSoftNudge: null,
  lastRiskScore: 0,

  setUser:           (user)    => set({ user }),
  setSession:        (session) => set({ session }),
  setAppPhase:       (appPhase)  => set({ appPhase }),
  setIATPhase:       (iatPhase)  => set({ iatPhase }),
  setCurrentCase:    (currentCase) => set({ currentCase }),
  enqueueHardNudge:  (nudge) => set({ pendingHardNudge: nudge }),
  dismissHardNudge:  ()      => set({ pendingHardNudge: null }),
  setActiveSoftNudge:(nudge) => set({ activeSoftNudge: nudge }),
  updateRiskScore:   (score) => set({ lastRiskScore: score }),
}));
