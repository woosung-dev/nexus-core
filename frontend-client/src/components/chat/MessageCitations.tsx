// 봇 답변이 참고한 RAG 출처(문서명 + 스니펫)를 접이식 카드로 보여주는 사용자용 컴포넌트
"use client";

import { useState } from "react";
import { Paperclip, ChevronDown, FileText } from "lucide-react";
import { Citation } from "@/types/api";

interface MessageCitationsProps {
  citations?: Citation[] | null;
}

// 이보다 긴 스니펫에만 "전체 보기" 토글을 노출 (짧은 건 항상 전문이 보임).
const EXPAND_THRESHOLD = 120;

// 원본 PDF 청크는 표 잔재와 연속 줄바꿈이 많아, 그대로 자르면 미리보기가 공백으로 소진된다.
const normalize = (s: string) => s.replace(/\s+/g, " ").trim();

export function MessageCitations({ citations }: MessageCitationsProps) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  if (!citations || citations.length === 0) return null;

  const toggle = (i: number) =>
    setExpanded((prev) => ({ ...prev, [i]: !prev[i] }));

  // 하나라도 근사 출처면 목록 전체를 근사로 표기한다 (섞여 있으면 보수적으로).
  const isApproximate = citations.some((c) => c.approximate);

  return (
    <div className="mt-2 w-full">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex items-center gap-1.5 text-[12px] font-medium text-zinc-500 hover:text-amber-600 transition-colors"
      >
        <Paperclip className="w-3.5 h-3.5 text-zinc-400" />
        <span>
          {isApproximate
            ? `참고 가능한 자료 ${citations.length}건`
            : `참고한 자료 ${citations.length}건`}
        </span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-zinc-400 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <>
          {isApproximate && (
            <p className="mt-2 text-[11.5px] leading-relaxed text-zinc-500">
              이 답변이 직접 인용한 자료가 아니라, 같은 질문으로 다시 검색해 찾은 관련
              문서입니다. 답변 내용과 다를 수 있으니 확인이 필요하면 원문을 참고해 주세요.
            </p>
          )}
          <ul className="mt-2 flex flex-col divide-y divide-zinc-100 rounded-xl border border-zinc-200 bg-white overflow-hidden">
          {citations.map((c, i) => {
            const content = normalize(c.content ?? "");
            const isLong = content.length > EXPAND_THRESHOLD;
            const isOpen = !!expanded[i];
            return (
              <li key={i} className="p-3 flex gap-2.5">
                <FileText className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <p className="text-[12.5px] font-semibold text-zinc-800 break-all">
                    {c.title || `출처 ${i + 1}`}
                    {typeof c.page_number === "number" && (
                      <span className="ml-1 font-normal text-zinc-400">
                        · p.{c.page_number}
                      </span>
                    )}
                  </p>
                  {content && (
                    <>
                      <p
                        className={`mt-0.5 text-[12px] leading-relaxed text-zinc-500 whitespace-pre-wrap break-words ${
                          isOpen ? "" : "line-clamp-3"
                        }`}
                      >
                        {content}
                      </p>
                      {isLong && (
                        <button
                          type="button"
                          onClick={() => toggle(i)}
                          className="mt-1 text-[11px] font-medium text-amber-600 hover:text-amber-700 transition-colors"
                        >
                          {isOpen ? "접기" : "전체 보기"}
                        </button>
                      )}
                    </>
                  )}
                </div>
              </li>
            );
          })}
          </ul>
        </>
      )}
    </div>
  );
}
