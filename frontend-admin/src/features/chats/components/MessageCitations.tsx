// 봇 답변이 인용한 RAG 출처를 문서 단위로 묶어 접이식 카드로 보여주는 관리자 컴포넌트
"use client";

import { useMemo, useState } from "react";
import { Paperclip, ChevronDown, FileText } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface Citation {
  title?: string | null;
  content?: string | null;
  // true = 표시된 답변이 직접 인용한 게 아니라, 같은 질문으로 재검색한 근사 출처.
  approximate?: boolean | null;
  uri?: string | null;
  page_number?: number | null;
  cite_count?: number | null;
}

interface MessageCitationsProps {
  citations?: Citation[];
}

// 이보다 긴 스니펫에만 "전체 보기" 토글을 노출 (짧은 건 항상 전문이 보임).
const EXPAND_THRESHOLD = 120;

// 원본 PDF 청크는 표 잔재와 연속 줄바꿈이 많아, 그대로 자르면 미리보기가 공백으로 소진된다.
const normalize = (s: string) => s.replace(/\s+/g, " ").trim();

interface DocGroup {
  title: string;
  pages: number[];
  chunks: Citation[];
  score: number; // 이 문서가 뒷받침한 구간 수의 합 — 정렬용
}

// 인용은 청크 단위로 온다. 한 문서가 여러 청크로 쪼개지고 각 청크가 여러 구간을
// 뒷받침해 목록이 수십 건으로 보이지만(실측 35건), 실제 문서는 2~3개뿐이다.
// client 쪽 MessageCitations 와 동일 로직 — 두 화면이 같은 판단을 보이도록 유지할 것.
function groupByDocument(citations: Citation[]): DocGroup[] {
  const byTitle = new Map<string, DocGroup>();
  for (const c of citations) {
    const title = c.title || "제목 없는 문서";
    let g = byTitle.get(title);
    if (!g) {
      g = { title, pages: [], chunks: [], score: 0 };
      byTitle.set(title, g);
    }
    g.chunks.push(c);
    g.score += c.cite_count ?? 1;
    if (typeof c.page_number === "number" && !g.pages.includes(c.page_number)) {
      g.pages.push(c.page_number);
    }
  }
  const groups = [...byTitle.values()];
  for (const g of groups) {
    g.pages.sort((a, b) => a - b);
    g.chunks.sort((a, b) => (b.cite_count ?? 1) - (a.cite_count ?? 1));
  }
  return groups.sort((a, b) => b.score - a.score);
}

export function MessageCitations({ citations }: MessageCitationsProps) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const groups = useMemo(() => groupByDocument(citations ?? []), [citations]);

  if (groups.length === 0) return null;

  const toggle = (key: string) =>
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  // 하나라도 근사 출처면 목록 전체를 근사로 표기한다 (섞여 있으면 보수적으로).
  const isApproximate = (citations ?? []).some((c) => c.approximate);

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="mt-2 w-full">
      <CollapsibleTrigger className="flex items-center gap-1.5 text-[12px] font-medium text-zinc-600 hover:text-zinc-900 transition-colors">
        <Paperclip className="w-3.5 h-3.5 text-zinc-400" />
        <span>
          {isApproximate
            ? `참고 가능한 자료 ${groups.length}건`
            : `참고한 자료 ${groups.length}건`}
        </span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-zinc-400 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-2">
        {isApproximate && (
          <p className="mb-2 text-[11.5px] leading-relaxed text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-2">
            <strong>근사 출처</strong> — 이 답변이 직접 인용한 자료가 아니라, 같은 질문으로
            백필이 다시 생성한 답변의 출처입니다. 표시된 답변과 근거가 어긋날 수 있으니
            (실측 25문항 중 7건) 평가 시 원문을 대조해 주세요.
          </p>
        )}
        <ul className="flex flex-col divide-y divide-zinc-100 rounded-xl border border-zinc-200 bg-white overflow-hidden">
          {groups.map((g, gi) => {
            const preview = normalize(g.chunks[0]?.content ?? "");
            const isLong = preview.length > EXPAND_THRESHOLD;
            const isOpen = !!expanded[g.title];
            return (
              <li key={g.title} className="p-3 flex gap-2.5">
                <FileText className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-1.5 flex-wrap">
                    <p className="text-[12.5px] font-semibold text-zinc-800 break-all">
                      {g.title}
                    </p>
                    {gi === 0 && groups.length > 1 && (
                      <span className="text-[10.5px] font-medium text-amber-600 bg-amber-50 rounded px-1.5 py-0.5 shrink-0">
                        {isApproximate ? "가장 많이 검색됨" : "주요 근거"}
                      </span>
                    )}
                  </div>
                  {g.pages.length > 0 && (
                    <p className="mt-0.5 text-[11px] text-zinc-400">
                      p.{g.pages.join(", ")}
                    </p>
                  )}
                  {preview && (
                    <>
                      <p
                        className={`mt-0.5 text-[12px] leading-relaxed text-zinc-500 break-words ${
                          isOpen ? "whitespace-pre-line" : "line-clamp-3"
                        }`}
                      >
                        {isOpen
                          ? g.chunks
                              .map((c) => normalize(c.content ?? ""))
                              .filter(Boolean)
                              .join("\n\n———\n\n")
                          : preview}
                      </p>
                      {(isLong || g.chunks.length > 1) && (
                        <button
                          type="button"
                          onClick={() => toggle(g.title)}
                          className="mt-1 text-[11px] font-medium text-amber-600 hover:text-amber-700 transition-colors"
                        >
                          {isOpen
                            ? "접기"
                            : g.chunks.length > 1
                              ? `전체 보기 (${g.chunks.length}개 부분)`
                              : "전체 보기"}
                        </button>
                      )}
                    </>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </CollapsibleContent>
    </Collapsible>
  );
}
