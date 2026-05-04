/**
 * REST API client
 * All calls go through the Vite proxy (/api → http://localhost:8000)
 */

import type {
  BiasType,
  IATBlock,
  IATSummary,
  IATTrialResponse,
  NudgeAcknowledgement,
  Session,
  UserProfile,
} from '@/types';

const BASE = '/api';

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Session
// ---------------------------------------------------------------------------

export async function startSession(userId: number): Promise<Session> {
  const res = await fetch(`${BASE}/session/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId }),
  });
  return json(res);
}

export async function endSession(sessionId: number): Promise<Session> {
  const res = await fetch(`${BASE}/session/end/${sessionId}`, { method: 'POST' });
  return json(res);
}

// ---------------------------------------------------------------------------
// Profile
// ---------------------------------------------------------------------------

export async function getProfile(userId: number): Promise<UserProfile> {
  const res = await fetch(`${BASE}/profile/${userId}`);
  return json(res);
}

export async function submitBaseline(userId: number, values: number[]): Promise<void> {
  const res = await fetch(`${BASE}/profile/${userId}/baseline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tortuosity_values: values }),
  });
  await json(res);
}

// ---------------------------------------------------------------------------
// IAT
// ---------------------------------------------------------------------------

export async function fetchIATBlocks(sessionId: number, biasType: BiasType): Promise<IATBlock[]> {
  const res = await fetch(`${BASE}/iat/blocks/${sessionId}?bias_type=${biasType}`);
  const data = await json<{ session_id: number; blocks: IATBlock[] }>(res);
  return data.blocks;
}

export async function postTrialResponse(response: IATTrialResponse): Promise<void> {
  const res = await fetch(`${BASE}/iat/response`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(response),
  });
  await json(res);
}

export async function completeIAT(
  sessionId: number,
  userId: number,
  biasType: BiasType,
): Promise<IATSummary> {
  const res = await fetch(`${BASE}/iat/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, user_id: userId, bias_type: biasType }),
  });
  return json(res);
}

// ---------------------------------------------------------------------------
// Nudge
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Cases
// ---------------------------------------------------------------------------

export async function fetchNextCase(sessionId: number): Promise<import('@/types').TriageCase> {
  const res = await fetch(`${BASE}/cases/next/${sessionId}`);
  const data = await json<{
    id: number;
    patient_label: string;
    chief_complaint: string;
    vitals: Record<string, string>;
    objective_findings: string[];
    correct_decision: string;
    is_counter_stereotypical: boolean;
    nudge_active: boolean;
  }>(res);
  return {
    id: String(data.id),
    patientLabel: data.patient_label,
    chiefComplaint: data.chief_complaint,
    vitals: data.vitals,
    objectiveFindings: data.objective_findings,
    isCounterStereotypical: data.is_counter_stereotypical,
    nudgeActive: data.nudge_active,
  };
}

export async function submitCaseDecision(
  sessionId: number,
  caseId: string,
  decision: string,
  windowId?: number,
  nudgeFired?: boolean,
  preNudgeDecision?: string,
): Promise<{ is_correct: boolean; correct_decision: string; delta_acc: number }> {
  const res = await fetch(`${BASE}/cases/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      case_id: Number(caseId),
      decision,
      window_id: windowId ?? null,
      nudge_fired: nudgeFired ?? false,
      pre_nudge_decision: preNudgeDecision ?? null,
    }),
  });
  return json(res);
}

export async function acknowledgeNudge(ack: NudgeAcknowledgement): Promise<void> {
  const res = await fetch(`${BASE}/nudge/acknowledge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ack),
  });
  await json(res);
}
