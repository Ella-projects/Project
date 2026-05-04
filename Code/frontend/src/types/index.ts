// ---------------------------------------------------------------------------
// Telemetry
// ---------------------------------------------------------------------------

export interface MousePoint {
  x: number;
  y: number;
  t: number; // Unix timestamp in ms
}

export interface TelemetryFrame {
  session_id: number;
  points: MousePoint[];
}

// ---------------------------------------------------------------------------
// Nudge payloads (mirrors backend schemas)
// ---------------------------------------------------------------------------

export interface HardNudgePayload {
  nudge_type: 'hard';
  window_id: number;
  risk_score: number;
  evidence: string[];
  requires_confirmation: boolean;
}

export interface SoftNudgePayload {
  nudge_type: 'soft';
  window_id: number;
  risk_score: number;
  target_field_ids: string[];
  luminance_delta: number;
  duration_ms: number;
}

export type NudgePayload = HardNudgePayload | SoftNudgePayload;

export interface WindowClearMessage {
  type: 'window_clear';
  window_id: number;
  risk_score: number;
}

export type WebSocketMessage =
  | { type: 'hard_nudge'; data: HardNudgePayload }
  | { type: 'soft_nudge'; data: SoftNudgePayload }
  | WindowClearMessage;

// ---------------------------------------------------------------------------
// IAT
// ---------------------------------------------------------------------------

export interface IATStimulus {
  trial_number: number;
  word: string;
  category: string;
  correct_key: string; // 'e' | 'i'
}

export interface IATBlock {
  block_number: number;
  is_practice: boolean;
  left_label: string;
  right_label: string;
  stimuli: IATStimulus[];
}

export type BiasType = 'age' | 'gender' | 'race';

export interface IATTrialResponse {
  session_id: number;
  bias_type: BiasType;
  block_number: number;
  trial_number: number;
  stimulus_word: string;
  stimulus_category: string;
  correct_key: string;
  response_key: string;
  reaction_time_ms: number;
  is_correct: boolean;
  presented_at: string;
}

export interface IATSummary {
  user_id: number;
  bias_type: BiasType;
  d_score: number;
  interpretation: string;
  completed_at: string;
}

// ---------------------------------------------------------------------------
// Session / Profile
// ---------------------------------------------------------------------------

export interface Session {
  id: number;
  user_id: number;
  nudge_order: 'control_first' | 'treatment_first';
  w_fatigue: number;
  delta_acc: number | null;
  rule_adherence_rate: number | null;
  started_at: string;
  ended_at: string | null;
  is_active: boolean;
}

export interface UserProfile {
  id: number;
  username: string;
  s_bias_age: number | null;
  s_bias_gender: number | null;
  s_bias_race: number | null;
  d_score_baseline: number | null;
  d_score_baseline_std: number | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Triage
// ---------------------------------------------------------------------------

export type TriageDecision = 'high' | 'moderate' | 'low' | 'stable';

export interface TriageCase {
  id: string;
  patientLabel: string;
  chiefComplaint: string;
  vitals: Record<string, string>;
  objectiveFindings: string[];
  isCounterStereotypical: boolean;
  nudgeActive: boolean;
}

export interface NudgeAcknowledgement {
  window_id: number;
  session_id: number;
  original_decision: TriageDecision;
  final_decision: TriageDecision;
  confirmed_at: string;
}
