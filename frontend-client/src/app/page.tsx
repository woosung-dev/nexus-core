import { dehydrate, HydrationBoundary } from '@tanstack/react-query';
import { getQueryClient } from '@/lib/get-query-client';
import { serverFetch } from '@/lib/api-server';
import { LandingClient } from '@/components/landing/LandingClient';
import { BotListResponse } from '@/types/api';

// 랜딩 페이지 전체의 기본 재검증 주기 설정 (60초)
export const revalidate = 60;

export default async function LandingPage() {
  const queryClient = getQueryClient();

  // 서버 환경에서 API 데이터 프리페치
  try {
    await queryClient.prefetchQuery({
      queryKey: ['bots'],
      queryFn: async () => {
        // serverFetch 호출 시에도 ISR 옵션 전달
        const data = await serverFetch<BotListResponse>('/bots', {
          next: { revalidate: 60 }
        });
        return data || { bots: [], total: 0 };
      },
    });
  } catch (error) {
    console.error('[LandingPage] prefetchQuery failed:', error);
  }

  return (
    // QueryClient의 현재 상태(프리페치된 데이터)를 직렬화하여 클라이언트에 주입
    <HydrationBoundary state={dehydrate(queryClient)}>
      <LandingClient />
    </HydrationBoundary>
  );
}
