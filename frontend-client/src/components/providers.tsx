'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { getQueryClient } from '@/lib/get-query-client';
import { ClerkTokenProvider } from '@/lib/api';

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => getQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ClerkTokenProvider />
      {children}
    </QueryClientProvider>
  );
}
