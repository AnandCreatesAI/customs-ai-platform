'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { DashboardWorkspace } from '@/components/dashboard/DashboardWorkspace';
import {
  fetchMe,
  submitLogout,
  type AuthUser,
} from '@/services/auth-service';

type ViewState =
  | { kind: 'loading' }
  | { kind: 'authenticated'; user: AuthUser }
  | { kind: 'error'; message: string };

export function DashboardClient() {
  const router = useRouter();
  const [viewState, setViewState] = useState<ViewState>({ kind: 'loading' });
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const applyMeResult = useCallback(
    (result: Awaited<ReturnType<typeof fetchMe>>) => {
      if (result.ok) {
        setViewState({ kind: 'authenticated', user: result.user });
        return;
      }

      if (result.unauthenticated) {
        router.replace('/login');
        return;
      }

      setViewState({ kind: 'error', message: result.message });
    },
    [router],
  );

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      const result = await fetchMe();
      if (cancelled) {
        return;
      }
      applyMeResult(result);
    })();

    return () => {
      cancelled = true;
    };
  }, [applyMeResult]);

  const retrySession = useCallback(async () => {
    setViewState({ kind: 'loading' });
    const result = await fetchMe();
    applyMeResult(result);
  }, [applyMeResult]);

  const handleLogout = useCallback(async () => {
    setLogoutError(null);
    setIsLoggingOut(true);
    const result = await submitLogout();
    setIsLoggingOut(false);

    if (result.ok) {
      router.replace('/login');
      router.refresh();
      return;
    }

    setLogoutError(result.message);
  }, [router]);

  const handleSessionExpired = useCallback(() => {
    router.replace('/login');
  }, [router]);

  if (viewState.kind === 'loading') {
    return (
      <main className="flex h-dvh items-center justify-center bg-white dark:bg-zinc-950">
        <p className="text-sm text-zinc-600 dark:text-zinc-400" role="status">
          Checking your session…
        </p>
      </main>
    );
  }

  if (viewState.kind === 'error') {
    return (
      <main className="mx-auto flex min-h-full max-w-3xl flex-col gap-4 px-6 py-16">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Dashboard</h1>
        <div
          role="alert"
          className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-100"
        >
          {viewState.message}
        </div>
        <button
          type="button"
          onClick={() => void retrySession()}
          className="w-fit rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
        >
          Retry
        </button>
      </main>
    );
  }

  return (
    <DashboardWorkspace
      user={viewState.user}
      onLogout={handleLogout}
      isLoggingOut={isLoggingOut}
      logoutError={logoutError}
      onSessionExpired={handleSessionExpired}
    />
  );
}
