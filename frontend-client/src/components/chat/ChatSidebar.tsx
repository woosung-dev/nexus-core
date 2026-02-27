import { Search, PenSquare, Menu, LayoutGrid, Bolt, MessageSquare, MoreVertical, Send, User } from "lucide-react";
import Link from "next/link";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const recentChats = [
  {
    title: "프로젝트 기획 도움",
    messages: 15,
    snippet: "좋은 아이디어네요! 다음 단계로는...",
    bot: "축복상담AI",
    date: "2024-01-15",
  },
  {
    title: "React 컴포넌트 최적화",
    messages: 23,
    snippet: "useMemo를 사용하면 성능이 개선됩니다",
    bot: "고민상담AI",
    date: "2024-01-15",
  },
  {
    title: "마케팅 카피 작성",
    messages: 8,
    snippet: "다음과 같은 문구는 어떨까요?",
    bot: "CreativeAI",
    date: "2024-01-14",
  },
  {
    title: "매출 데이터 분석",
    messages: 12,
    snippet: "지난 분기 대비 15% 증가했습니다",
    bot: "DataAnalyzer",
    date: "2024-01-14",
  },
  {
    title: "영어 회화 연습",
    messages: 31,
    snippet: "Great job! 발음이 많이 좋아졌어요",
    bot: "LanguageTutor",
    date: "2024-01-13",
  },
];

export function ChatSidebar({ className }: { className?: string }) {
  return (
    <aside className={`bg-zinc-950 flex flex-col h-full border-r border-zinc-900 w-80 shrink-0 ${className}`}>
      {/* Sidebar Header */}
      <div className="p-4 border-b border-zinc-900 shrink-0">
        <div className="flex items-center justify-between mb-4">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-500 to-amber-600 flex items-center justify-center shrink-0">
              <Bolt className="w-4 h-4 text-black" fill="currentColor" />
            </div>
            <span className="font-bold text-lg text-white tracking-tight">AI Chat Hub</span>
          </Link>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-white rounded-lg">
            <PenSquare className="w-4 h-4" />
          </Button>
        </div>
        
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input 
            type="text" 
            placeholder="대화 검색..." 
            className="w-full h-10 bg-black border border-zinc-800 rounded-lg pl-9 pr-4 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-amber-500/50 transition-colors"
          />
        </div>
      </div>

      {/* Chat History List */}
      <ScrollArea className="flex-1 p-4">
        <h3 className="text-xs font-semibold text-zinc-500 mb-3 uppercase tracking-wider">지난 대화</h3>
        <div className="flex flex-col gap-2">
          {recentChats.map((chat, i) => (
            <button key={i} className="text-left bg-zinc-900/40 hover:bg-zinc-800/60 p-3 rounded-xl transition-colors border border-transparent hover:border-zinc-800 group">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm text-zinc-200 group-hover:text-amber-500 transition-colors line-clamp-1">{chat.title}</span>
                <span className="text-[10px] font-medium text-zinc-500 bg-zinc-900 px-1.5 py-0.5 rounded-md shrink-0">{chat.messages}</span>
              </div>
              <p className="text-xs text-zinc-400 mb-3 line-clamp-1">{chat.snippet}</p>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-zinc-500 flex items-center gap-1.5">
                  <div className="w-1 h-1 rounded-full bg-amber-500/50" />
                  {chat.bot}
                </span>
                <span className="text-zinc-600">{chat.date}</span>
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>

      {/* Bottom Profile Link */}
      <div className="p-4 border-t border-zinc-900 shrink-0">
        <Link href="/mypage" className="flex items-center gap-3 p-3 bg-zinc-900/40 hover:bg-zinc-800/80 rounded-xl transition-colors border border-transparent hover:border-zinc-800">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-500 to-amber-600 flex items-center justify-center shrink-0">
            <User className="w-5 h-5 text-black/80" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-white">마이페이지</span>
            <span className="text-xs text-zinc-400">설정 및 정보</span>
          </div>
        </Link>
      </div>
    </aside>
  );
}
