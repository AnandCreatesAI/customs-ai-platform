'use client';

import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

import { EmployeeSpaceWorkspace } from '@/components/employee-space/EmployeeSpaceWorkspace';
import type { AuthUser } from '@/services/auth-service';

type EmployeeSpaceProps = {
  user: AuthUser;
};

export function EmployeeSpace({ user }: EmployeeSpaceProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col bg-zinc-50" data-testid="employee-space">
      <header className="shrink-0 border-b border-zinc-200 bg-white px-4 py-4 md:px-6">
        <div className="flex flex-col gap-2">
          <Link
            href="/dashboard"
            data-testid="employee-space-back"
            className="inline-flex w-fit cursor-pointer items-center gap-1.5 text-sm font-medium text-zinc-600 transition hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Back to dashboard
          </Link>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900">Employee Space</h1>
          <p className="text-sm text-zinc-600">
            Upload training data, monitor pipeline progress, and manage documents per business
            model.
          </p>
        </div>
      </header>

      <EmployeeSpaceWorkspace user={user} />
    </div>
  );
}
