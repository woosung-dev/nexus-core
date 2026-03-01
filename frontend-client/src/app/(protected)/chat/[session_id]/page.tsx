import { dehydrate, HydrationBoundary } from '@tanstack/react-query';
import { getQueryClient } from '@/lib/get-query-client';
import { serverFetch } from '@/lib/api-server';
import { ChatLayout } from '../ChatLayout';

export default async function ChatRoomPage({
  params,
}: {
  params: Promise<{ session_id: string }> | { session_id: string };
}) {
  const queryClient = getQueryClient();
  const resolvedParams = await params;
  const sessionId = resolvedParams.session_id;

  // 사이드바용 세션 목록 및 특정 채팅방 메시지 내역 prefetch
  try {
    await Promise.all([
      queryClient.prefetchQuery({
        queryKey: ['chats'],
        queryFn: () => serverFetch('/chats'),
      }),
      queryClient.prefetchQuery({
        queryKey: ['messages', sessionId],
        queryFn: () => serverFetch(`/chats/${sessionId}/messages`),
      }),
    ]);
  } catch (error) {
    console.error(`Failed to prefetch chat room ${sessionId}:`, error);
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ChatLayout sessionId={sessionId} />
    </HydrationBoundary>
  );
}
