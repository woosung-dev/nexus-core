// 채팅 전용 공유 레이아웃. ChatProvider 가 phase/sessionId/botId 단일 진실원을 들고,
// ChatShell 이 그 phase 에 따라 입력칸 중앙 정렬/하단 모드를 모핑한다.
// 라우트 변경(/chat ↔ /chat/{id} ↔ /chat/new/{bot}) 시 본 레이아웃은 mount 1회만 유지된다.
import { ChatProvider } from "./ChatProvider";
import { ChatShell } from "./ChatShell";

export default function ChatRouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ChatProvider>
      <ChatShell>{children}</ChatShell>
    </ChatProvider>
  );
}
