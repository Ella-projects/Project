/**
 * App root
 *
 * Bootstraps the session and user profile, then hands off to Dashboard.
 * In production, user identity comes from your auth layer.
 * For scaffolding, we use a hardcoded dev user (id=1).
 */

import { useEffect, useRef, useState } from 'react';
import { Dashboard } from '@/components/layout/Dashboard';
import { useAdaptiveStore } from '@/store/adaptiveStore';
import { getProfile, startSession } from '@/services/apiService';

// TODO: Replace with real auth/login flow
const DEV_USER_ID = 10;

export default function App() {
  const { setUser, setSession } = useAdaptiveStore((s) => ({
    setUser: s.setUser,
    setSession: s.setSession,
  }));

  const [booting, setBooting] = useState(true);
  const [bootError, setBootError] = useState<string | null>(null);
  // Ref guard prevents StrictMode's double-invocation from creating two sessions
  const bootedRef = useRef(false);

  useEffect(() => {
    if (bootedRef.current) return;
    bootedRef.current = true;

    (async () => {
      try {
        const [profile, session] = await Promise.all([
          getProfile(DEV_USER_ID),
          startSession(DEV_USER_ID),
        ]);
        setUser(profile);
        setSession(session);
      } catch (e) {
        setBootError(e instanceof Error ? e.message : 'Boot failed');
      } finally {
        setBooting(false);
      }
    })();
  }, [setUser, setSession]);

  if (booting) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <p>Initialising session…</p>
      </div>
    );
  }

  if (bootError) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <p style={{ color: '#dc2626' }}>Error: {bootError}</p>
      </div>
    );
  }

  return <Dashboard />;
}
