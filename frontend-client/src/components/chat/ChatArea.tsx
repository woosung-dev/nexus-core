import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, User } from "lucide-react";

const messages = [
  {
    role: "ai",
    content: "안녕하세요! 무엇을 도와드릴까요?",
    time: "2024-01-15 14:00",
  },
  {
    role: "user",
    content: "웹사이트 프로젝트를 시작하려고 하는데 어떻게 시작하면 좋을까요?",
    time: "2024-01-15 14:01",
  },
  {
    role: "ai",
    content: "웹사이트 프로젝트를 시작하시는군요! 먼저 다음 단계를 추천드립니다:\n\n1. 목적과 목표 정의하기\n2. 타겟 사용자 파악하기\n3. 필요한 기능 목록 작성하기\n4. 디자인 컨셉 정하기\n5. 기술 스택 선택하기\n\n어떤 종류의 웹사이트를 만들고 싶으신가요?",
    time: "2024-01-15 14:02",
  }
];

export function ChatArea() {
  return (
    <ScrollArea className="flex-1 px-4 sm:px-8 bg-black relative">
      {/* Background Ambience */}
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-amber-500/5 rounded-full blur-[120px] pointer-events-none" />
      
      <div className="w-full max-w-4xl mx-auto py-8 flex flex-col gap-8 relative z-10">
        {messages.map((msg, idx) => {
          const isUser = msg.role === "user";
          return (
            <div key={idx} className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
              <div className={`flex gap-4 max-w-[85%] sm:max-w-[75%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 shadow-sm ${
                  isUser 
                    ? "bg-gradient-to-br from-amber-400 to-amber-600 ring-2 ring-amber-500/20" 
                    : "bg-zinc-900 border border-zinc-800"
                }`}>
                  {isUser ? (
                    <User className="w-4 h-4 text-black/80" />
                  ) : (
                    <Bot className="w-4 h-4 text-amber-500" />
                  )}
                </div>

                {/* Bubble Config */}
                <div className="flex flex-col gap-2 min-w-0">
                  <div className={`px-5 py-4 rounded-2xl whitespace-pre-wrap text-[15px] leading-relaxed break-words shadow-sm ${
                    isUser 
                      ? "bg-gradient-to-br from-amber-500 to-amber-600 text-black rounded-tr-sm" 
                      : "bg-zinc-900 border border-zinc-800 text-zinc-100 rounded-tl-sm ring-1 ring-white/5"
                  }`}>
                    {msg.content}
                  </div>
                  <span className={`text-[11px] text-zinc-500 px-1 ${isUser ? "text-right" : "text-left"}`}>
                    {msg.time}
                  </span>
                </div>

              </div>
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}
