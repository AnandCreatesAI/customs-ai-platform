'use client';

import { GraduationCap } from 'lucide-react';
import Link from 'next/link';

const EMPLOYEE_SPACE_HREF = '/dashboard/employee-space';

/** Standalone Employee Space entry (dashboard welcome embeds the full card layout). */
export function EmployeeSpaceNavigation() {
  return (
    <aside
      className="w-full max-w-sm shrink-0"
      data-testid="employee-space-navigation"
      aria-label="Employee Space"
    >
      <article className="flex h-full flex-col rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700">
          <GraduationCap className="h-5 w-5" aria-hidden />
        </span>
        <h2 className="mt-4 text-base font-semibold text-zinc-900">Employee Space</h2>
        <p className="mt-2 text-sm leading-relaxed text-zinc-600">
          Upload documents, add knowledge and manage model training.
        </p>
        <Link
          href={EMPLOYEE_SPACE_HREF}
          data-testid="employee-space-nav-main"
          className="mt-5 inline-flex w-full cursor-pointer items-center justify-center rounded-lg border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-900 transition hover:border-indigo-200 hover:bg-indigo-50/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2"
        >
          Open Employee Space
        </Link>
      </article>
    </aside>
  );
}
