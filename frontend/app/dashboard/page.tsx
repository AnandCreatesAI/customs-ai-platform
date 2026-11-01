import type { Metadata } from 'next';

import { DashboardClient } from '@/components/dashboard/DashboardClient';

export const metadata: Metadata = {
  title: 'Workspace | Customs AI Platform',
  description: 'Customs AI Platform enterprise workspace',
};

export default function DashboardPage() {
  return <DashboardClient />;
}
