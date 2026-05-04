/**
 * ExperimentalStimulus
 *
 * Wraps counter-stereotypical triage cases with ΔAcc telemetry.
 * Emits a custom DOM event on mount so the session monitor can
 * track exposure counts independently of decision outcomes.
 *
 * No visible difference is shown to the clinician.
 */

import { useEffect } from 'react';
import type { TriageCase } from '@/types';

interface Props {
  triageCase: TriageCase;
  children: React.ReactNode;
}

export function ExperimentalStimulus({ triageCase, children }: Props) {
  useEffect(() => {
    if (!triageCase.isCounterStereotypical) return;

    // Emit internal event for analytics / future backend hook
    window.dispatchEvent(
      new CustomEvent('aui:counter_stereotypical_exposed', {
        detail: { caseId: triageCase.id, timestamp: Date.now() },
      })
    );
  }, [triageCase.id, triageCase.isCounterStereotypical]);

  return <>{children}</>;
}
