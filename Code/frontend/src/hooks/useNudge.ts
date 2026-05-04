/**
 * useNudge
 *
 * Provides convenience selectors and actions for the active nudge state.
 * Soft nudges auto-expire after duration_ms.
 */

import { useEffect } from 'react';
import { useAdaptiveStore } from '@/store/adaptiveStore';

export function useNudge() {
  const pendingHardNudge = useAdaptiveStore((s) => s.pendingHardNudge);
  const activeSoftNudge = useAdaptiveStore((s) => s.activeSoftNudge);
  const dismissHardNudge = useAdaptiveStore((s) => s.dismissHardNudge);
  const setActiveSoftNudge = useAdaptiveStore((s) => s.setActiveSoftNudge);

  // Auto-clear soft nudge after its duration expires
  useEffect(() => {
    if (!activeSoftNudge) return;
    const timer = setTimeout(() => {
      setActiveSoftNudge(null);
    }, activeSoftNudge.duration_ms);
    return () => clearTimeout(timer);
  }, [activeSoftNudge, setActiveSoftNudge]);

  return {
    pendingHardNudge,
    activeSoftNudge,
    dismissHardNudge,
    hasHardNudge: pendingHardNudge !== null,
    hasSoftNudge: activeSoftNudge !== null,
  };
}
