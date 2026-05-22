// 채팅 전용 공유 레이아웃. ChatProvider 가 phase/sessionId/botId 단일 진실원을 들고,
// ChatShell 이 그 phase 에 따라 입력칸 중앙 정렬/하단 모드를 모핑한다.
// 라우트 변경(/chat ↔ /chat/{id} ↔ /chat/new/{bot}) 시 본 레이아웃은 mount 1회만 유지된다.
import type { Metadata } from "next";
import { ChatProvider } from "./ChatProvider";
import { ChatShell } from "./ChatShell";

// 채팅 하위 전체 noindex — 사용자 사적 대화 콘텐츠는 검색엔진에 노출되면 안 됨.
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

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
