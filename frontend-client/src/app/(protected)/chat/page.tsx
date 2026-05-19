// /chat — 활성 세션 없을 때의 안내 화면. ChatLayout(공유) 이 sessionId 없으면 이 page 의 children 을 렌더한다.
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ChatIndexPage() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-linear-to-b from-sky-50/50 via-white to-white relative">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(245,158,11,0.05),transparent_70%)] pointer-events-none" />

      <div className="w-16 h-16 bg-white rounded-3xl flex items-center justify-center mb-6 border border-amber-100 shadow-xl backdrop-blur-xl relative z-10">
        <Sparkles className="w-8 h-8 text-amber-500 animate-pulse" />
      </div>
      <h2 className="text-xl font-bold text-zinc-900 mb-3 relative z-10">대화할 전문 챗봇을 선택해주세요</h2>
      <p className="text-sm text-zinc-500 max-w-sm mb-8 relative z-10">
        좌측 사이드바에서 기존 대화를 이어나가거나
        <br />홈 화면에서 새로운 챗봇을 선택하여 대화를 시작해보세요.
      </p>
      <Link href="/" passHref className="relative z-10">
        <Button className="bg-amber-500 hover:bg-amber-600 text-white font-semibold rounded-xl px-8 h-12 shadow-[0_0_15px_rgba(245,158,11,0.2)] transition-colors">
          챗봇 골라보기
        </Button>
      </Link>
    </div>
  );
}
