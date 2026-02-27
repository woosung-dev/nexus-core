import { Pen, User } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ProfileSection() {
  return (
    <section className="bg-zinc-950/80 border border-zinc-800 rounded-xl p-8 relative overflow-hidden backdrop-blur-xl">
      {/* Background Subtle Glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/5 rounded-full blur-[80px] pointer-events-none" />

      <div className="flex items-center justify-between mb-8 z-10 relative">
        <h2 className="text-xl font-bold text-white">프로필 정보</h2>
        <Button variant="outline" size="sm" className="bg-zinc-900 border-zinc-800 text-white hover:bg-zinc-800 hover:text-white transition-colors h-9 px-4">
          <Pen className="w-4 h-4 mr-2 text-zinc-400" />
          수정
        </Button>
      </div>

      <div className="flex items-center gap-6 mb-10 z-10 relative">
        <div className="w-24 h-24 rounded-full bg-gradient-to-br from-amber-500 to-amber-600 flex items-center justify-center shrink-0 shadow-[0_0_20px_rgba(245,158,11,0.2)]">
          <User className="w-10 h-10 text-black/80" />
        </div>
        <div className="flex flex-col">
          <h3 className="text-2xl font-bold text-white mb-1">홍길동</h3>
          <p className="text-sm text-zinc-400">hong@example.com</p>
        </div>
      </div>

      <div className="space-y-6 z-10 relative">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-zinc-400">이름</label>
          <p className="text-base text-white">홍길동</p>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-zinc-400">이메일</label>
          <p className="text-base text-white">hong@example.com</p>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-zinc-400">소개</label>
          <p className="text-base text-white">AI 기술에 관심이 많은 개발자입니다.</p>
        </div>
      </div>
    </section>
  );
}
