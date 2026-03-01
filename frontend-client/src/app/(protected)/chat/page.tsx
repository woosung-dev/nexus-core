import { dehydrate, HydrationBoundary } from '@tanstack/react-query';
import { getQueryClient } from '@/lib/get-query-client';
import { serverFetch } from '@/lib/api-server';
import { ChatLayout } from './ChatLayout';

export default async function NewChatPage() {
  const queryClient = getQueryClient();

  // 사이드바용 세션 목록 prefetch (에러 무시, 캐싱)
  try {
    await queryClient.prefetchQuery({
      queryKey: ['chats'],
      queryFn: () => serverFetch('/chats'),
    });
  } catch (error) {
    console.error("Failed to prefetch chats:", error);
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ChatLayout />  {/* sessionId 없음 = 새 채팅 */}
    </HydrationBoundary>
  );
}
