// 봇 답변이 제안한 후속 질문을 칩으로 보여주는 관리자(읽기 전용) 컴포넌트
import { Lightbulb } from "lucide-react";

interface MessageFollowupsProps {
  items?: string[];
}

export function MessageFollowups({ items }: MessageFollowupsProps) {
  if (!items || items.length === 0) return null;

  return (
    <div className="mt-3 flex flex-col gap-2">
      <div className="flex items-center gap-1.5 text-[11px] font-medium text-zinc-500 uppercase tracking-wider">
        <Lightbulb className="w-3 h-3 text-amber-500" />
        <span>이어서 물어보면 좋을 질문</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {items.slice(0, 3).map((q, i) => (
          <span
            key={`${i}-${q}`}
            className="text-[13px] px-3.5 py-1.5 rounded-full bg-white border border-amber-200 text-zinc-700 shadow-sm"
          >
            {q}
          </span>
        ))}
      </div>
    </div>
  );
}
