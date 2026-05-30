// 봇 답변이 인용한 RAG 출처(문서명 + 스니펫)를 접이식 카드로 보여주는 관리자 컴포넌트
"use client";

import { useState } from "react";
import { Paperclip, ChevronDown, FileText } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface Citation {
  title?: string | null;
  content?: string | null;
}

interface MessageCitationsProps {
  citations?: Citation[];
}

export function MessageCitations({ citations }: MessageCitationsProps) {
  const [open, setOpen] = useState(false);

  if (!citations || citations.length === 0) return null;

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="mt-2 w-full">
      <CollapsibleTrigger className="flex items-center gap-1.5 text-[12px] font-medium text-zinc-600 hover:text-zinc-900 transition-colors">
        <Paperclip className="w-3.5 h-3.5 text-zinc-400" />
        <span>참고한 자료 {citations.length}건</span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-zinc-400 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-2">
        <ul className="flex flex-col divide-y divide-zinc-100 rounded-xl border border-zinc-200 bg-white overflow-hidden">
          {citations.map((c, i) => (
            <li key={i} className="p-3 flex gap-2.5">
              <FileText className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-[12.5px] font-semibold text-zinc-800 break-all">
                  {c.title || `출처 ${i + 1}`}
                </p>
                {c.content && (
                  <p className="mt-0.5 text-[12px] leading-relaxed text-zinc-500 line-clamp-3 whitespace-pre-wrap">
                    {c.content}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      </CollapsibleContent>
    </Collapsible>
  );
}
