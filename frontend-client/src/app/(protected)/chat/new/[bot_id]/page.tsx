import { dehydrate, HydrationBoundary } from '@tanstack/react-query';
import { getQueryClient } from '@/lib/get-query-client';
import { serverFetch } from '@/lib/api-server';
import { ChatLayout } from '../../ChatLayout';

export default async function NewChatWithBotPage({ params }: { params: Promise<{ bot_id: string }> | { bot_id: string } }) {
  const queryClient = getQueryClient();
  const resolvedParams = await params;
  const botId = resolvedParams.bot_id;

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
      <ChatLayout botId={botId} />
    </HydrationBoundary>
  );
}
