import type { Metadata } from 'next';
import { Suspense } from 'react';

import { EmployeeSpaceClient } from '@/components/employee-space/EmployeeSpaceClient';

export const metadata: Metadata = {
  title: 'Employee Space | Customs AI Platform',
  description: 'Document training and model management workspace',
};

export default function EmployeeSpacePage() {
  return (
    <Suspense
      fallback={
        <main className="flex h-dvh items-center justify-center bg-zinc-50">
          <p className="text-sm text-zinc-600" role="status">
            Loading Employee Space…
          </p>
        </main>
      }
    >
      <EmployeeSpaceClient />
    </Suspense>
  );
}
