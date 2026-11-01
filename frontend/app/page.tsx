import type { Metadata } from 'next';

import { PublicChatClient } from '@/components/dashboard/PublicChatClient';

export const metadata: Metadata = {
  title: 'Customs AI Platform',
  description: 'Intelligent assistant for customs operations, declarations, compliance and classification',
};

export default function HomePage() {
  return <PublicChatClient />;
}
