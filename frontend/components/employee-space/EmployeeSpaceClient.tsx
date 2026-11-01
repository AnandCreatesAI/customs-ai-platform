'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { EmployeeSpace } from '@/components/employee-space/EmployeeSpace';
import { fetchMe, type AuthUser } from '@/services/auth-service';

type ViewState =
  | { kind: 'loading' }
  | { kind: 'authenticated'; user: AuthUser }
  | { kind: 'error'; message: string };

export function EmployeeSpaceClient() {
  const router = useRouter();
  const [viewState, setViewState] = useState<ViewState>({ kind: 'loading' });

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
      if (!cancelled) {
        applyMeResult(result);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applyMeResult]);

  if (viewState.kind === 'loading') {
    return (
      <main className="flex h-dvh items-center justify-center bg-zinc-50">
        <p className="text-sm text-zinc-600" role="status">
          Checking your session…
        </p>
      </main>
    );
  }

  if (viewState.kind === 'error') {
    return (
      <main className="mx-auto max-w-3xl px-6 py-16">
        <p role="alert" className="text-sm text-red-700">
          {viewState.message}
        </p>
      </main>
    );
  }

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-zinc-100">
      <EmployeeSpace user={viewState.user} />
    </div>
  );
}
