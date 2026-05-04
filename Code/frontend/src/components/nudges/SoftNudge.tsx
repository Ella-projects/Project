/**
 * SoftNudge — Ambient Saliency Shift
 *
 * Applies a luminance modulation overlay to specified DOM fields,
 * drawing attention toward objective data without interrupting workflow.
 *
 * Renders nothing visible itself — effect is applied via DOM manipulation
 * on the target_field_ids. A subtle pulsing border is added to each target.
 */

import { useEffect } from 'react';
import type { SoftNudgePayload } from '@/types';

interface Props {
  nudge: SoftNudgePayload;
}

export function SoftNudge({ nudge }: Props) {
  useEffect(() => {
    const targets = nudge.target_field_ids
      .map((id) => document.getElementById(id))
      .filter(Boolean) as HTMLElement[];

    const originalStyles = targets.map((el) => ({
      el,
      boxShadow: el.style.boxShadow,
      transition: el.style.transition,
      filter: el.style.filter,
    }));

    const intensity = nudge.luminance_delta;
    targets.forEach((el) => {
      el.style.transition = 'box-shadow 0.4s ease, filter 0.4s ease';
      el.style.boxShadow = `0 0 0 3px rgba(59, 130, 246, ${intensity})`;
      el.style.filter = `brightness(${1 + intensity * 0.2})`;
    });

    return () => {
      originalStyles.forEach(({ el, boxShadow, transition, filter }) => {
        el.style.boxShadow = boxShadow;
        el.style.transition = transition;
        el.style.filter = filter;
      });
    };
  }, [nudge]);

  // No visible DOM output — effect is side-effect only
  return null;
}
