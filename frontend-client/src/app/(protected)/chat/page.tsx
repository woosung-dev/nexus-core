import { ChatLayout } from './ChatLayout';

// 빌드 시 정적 최적화(SSG)를 방지하고 런타임에 항상 서버 사이드에서 실행되도록 설정
export const dynamic = "force-dynamic";

export default function NewChatPage() {
  return <ChatLayout />;
}
