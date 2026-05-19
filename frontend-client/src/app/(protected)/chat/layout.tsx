// 채팅 전용 공유 레이아웃 — /chat, /chat/new/[bot_id], /chat/[session_id] 사이를 이동해도
// ChatLayout 인스턴스가 유지되어 첫 응답 깜빡임/스트리밍 상태 손실을 차단한다.
import { ChatLayout } from "./ChatLayout";

export default function ChatRouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ChatLayout>{children}</ChatLayout>;
}
