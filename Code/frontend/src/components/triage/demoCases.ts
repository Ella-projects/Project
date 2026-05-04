/**
 * Demo triage case data for development / scaffolding.
 * Replace with a real API-backed case loader in production.
 *
 * isCounterStereotypical = true marks experimental stimuli.
 */

import type { TriageCase } from '@/types';

export const DEMO_CASES: TriageCase[] = [
  {
    id: 'case-001',
    patientLabel: 'Patient A',
    chiefComplaint: 'Chest pain, onset 2 hours ago',
    vitals: {
      HR: '102 bpm',
      BP: '148/92 mmHg',
      SpO2: '96%',
      RR: '18 /min',
      Temp: '37.1°C',
    },
    objectiveFindings: [
      'Diaphoresis present',
      'ECG: ST-segment elevation in leads II, III, aVF',
      'Troponin I: 0.8 ng/mL (elevated)',
    ],
    isCounterStereotypical: false,
    nudgeActive: false,
  },
  {
    id: 'case-002',
    patientLabel: 'Patient B',
    chiefComplaint: 'Shortness of breath and fatigue for 3 days',
    vitals: {
      HR: '88 bpm',
      BP: '130/84 mmHg',
      SpO2: '93%',
      RR: '22 /min',
      Temp: '37.4°C',
    },
    objectiveFindings: [
      'Bilateral basal crackles on auscultation',
      'Pedal oedema (2+)',
      'BNP: 820 pg/mL (elevated)',
    ],
    isCounterStereotypical: true, // Counter-stereotypical experimental stimulus
    nudgeActive: false,
  },
];
