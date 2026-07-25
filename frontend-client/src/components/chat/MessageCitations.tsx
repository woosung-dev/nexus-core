// 봇 답변이 참고한 RAG 출처를 문서 단위로 묶어 접이식 카드로 보여주는 사용자용 컴포넌트
"use client";

import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { Paperclip, ChevronDown, FileText, Highlighter } from "lucide-react";
import { Citation } from "@/types/api";
import { groupByDocument } from "./citationGroups";

interface MessageCitationsProps {
  citations?: Citation[] | null;
  // 본문 각주 클릭 — 목록을 펼치고 해당 카드로 스크롤한다. nonce 는 같은 번호 재클릭 대응용.
  focus?: { num: number; nonce: number } | null;
}

// 이보다 긴 스니펫에만 "전체 보기" 토글을 노출 (짧은 건 항상 전문이 보임).
const EXPAND_THRESHOLD = 120;
// 접힌 상태에서 근거 구절 앞뒤로 함께 보여줄 글자 수 — 형광펜이 3줄 클램프 밖으로 밀려나지 않게 한다.
const LEAD = 40;
const TRAIL = 90;

// 원본 PDF 청크는 표 잔재와 연속 줄바꿈이 많아, 그대로 자르면 미리보기가 공백으로 소진된다.
const normalize = (s: string) => s.replace(/\s+/g, " ").trim();

// 근거 구절에 노란 형광펜을 칠한다.
// evidence 는 백엔드가 원문 대조로 스냅해 넣어 항상 content 의 부분문자열이지만, 화면에 그리는 건
// 공백을 압축한 normalize() 결과이므로 비교도 압축본끼리 해야 위치가 맞는다.
function highlight(text: string, spans: string[]): ReactNode {
  const ranges: [number, number][] = [];
  for (const raw of spans) {
    const span = normalize(raw);
    if (span.length < 4) continue;
    const at = text.indexOf(span);
    if (at >= 0) ranges.push([at, at + span.length]);
  }
  if (ranges.length === 0) return text;

  // 구절끼리 겹치면 <mark> 가 중첩되므로 하나로 합친다.
  ranges.sort((a, b) => a[0] - b[0]);
  const merged: [number, number][] = [];
  for (const r of ranges) {
    const last = merged[merged.length - 1];
    if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]);
    else merged.push([...r]);
  }

  const out: ReactNode[] = [];
  let cursor = 0;
  merged.forEach(([s, e], i) => {
    if (s > cursor) out.push(text.slice(cursor, s));
    out.push(
      <mark
        key={i}
        className="bg-amber-200/70 text-zinc-900 rounded-[3px] px-0.5 box-decoration-clone"
      >
        {text.slice(s, e)}
      </mark>
    );
    cursor = e;
  });
  if (cursor < text.length) out.push(text.slice(cursor));
  return out;
}

// 접힌 미리보기는 청크 앞부분이 아니라 첫 근거 구절 주변을 보여준다 — 형광펜이 안 보이면 의미가 없다.
function previewWindow(text: string, spans: string[]): string {
  for (const raw of spans) {
    const span = normalize(raw);
    const at = span.length >= 4 ? text.indexOf(span) : -1;
    if (at < 0) continue;
    const from = Math.max(0, at - LEAD);
    const to = Math.min(text.length, at + span.length + TRAIL);
    return (from > 0 ? "… " : "") + text.slice(from, to) + (to < text.length ? " …" : "");
  }
  return text;
}

export function MessageCitations({ citations, focus }: MessageCitationsProps) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const cardRefs = useRef<Record<number, HTMLLIElement | null>>({});
  const [flash, setFlash] = useState<number | null>(null);

  const groups = useMemo(() => groupByDocument(citations ?? []), [citations]);

  // 각주에서 지목된 카드를 펼쳐 보여준다. 목록이 접혀 있으면 먼저 펴야 해서 스크롤은 다음 프레임에 건다.
  useEffect(() => {
    if (!focus) return;
    setOpen(true);
    setFlash(focus.num);
    const timer = setTimeout(() => {
      cardRefs.current[focus.num]?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 60);
    const clear = setTimeout(() => setFlash(null), 1600);
    return () => {
      clearTimeout(timer);
      clearTimeout(clear);
    };
  }, [focus]);

  if (groups.length === 0) return null;

  const toggle = (key: string) =>
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  // 하나라도 근사 출처면 목록 전체를 근사로 표기한다 (섞여 있으면 보수적으로).
  const isApproximate = (citations ?? []).some((c) => c.approximate);

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
            ? `참고 가능한 자료 ${groups.length}건`
            : `참고한 자료 ${groups.length}건`}
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
            {groups.map((g, gi) => {
              const head = g.chunks[0];
              const headEvidence = head?.evidence ?? [];
              const full = normalize(head?.content ?? "");
              const preview = previewWindow(full, headEvidence);
              const isLong = full.length > EXPAND_THRESHOLD;
              const isOpen = !!expanded[g.title];
              const hasEvidence = g.chunks.some((c) => (c.evidence?.length ?? 0) > 0);
              const num = gi + 1;
              return (
                <li
                  key={g.title}
                  ref={(el) => {
                    cardRefs.current[num] = el;
                  }}
                  className={`p-3 flex gap-2.5 transition-colors duration-500 ${
                    flash === num ? "bg-amber-50" : ""
                  }`}
                >
                  <FileText className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline gap-1.5 flex-wrap">
                      {/* 본문 각주 [n] 과 같은 번호 — 근사 인용은 각주가 안 붙으므로 번호도 숨긴다. */}
                      {!isApproximate && (
                        <span className="text-[10.5px] font-semibold text-amber-600 shrink-0">
                          [{num}]
                        </span>
                      )}
                      <p className="text-[12.5px] font-semibold text-zinc-800 break-all">
                        {g.title}
                      </p>
                      {gi === 0 && groups.length > 1 && (
                        // 근사 인용일 땐 "주요 근거"라 쓸 수 없다 — 이 순위는 표시된 답변이
                        // 아니라 백필이 새로 생성한 답변을 뒷받침한 정도이기 때문.
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
                    {hasEvidence && (
                      <p className="mt-1 flex items-center gap-1 text-[10.5px] text-amber-700">
                        <Highlighter className="w-3 h-3 shrink-0" />
                        노란 부분이 이 답변에 실제로 참고된 대목입니다
                      </p>
                    )}
                    {preview && (
                      <>
                        {isOpen ? (
                          // 펼친 상태에선 청크마다 자기 근거 구절로 칠해야 하므로 따로 그린다.
                          <div className="mt-0.5 flex flex-col gap-2">
                            {g.chunks.map((c, ci) => {
                              const body = normalize(c.content ?? "");
                              if (!body) return null;
                              return (
                                <p
                                  key={ci}
                                  className="text-[12px] leading-relaxed text-zinc-500 break-words whitespace-pre-line border-t border-zinc-100 first:border-t-0 pt-2 first:pt-0"
                                >
                                  {highlight(body, c.evidence ?? [])}
                                </p>
                              );
                            })}
                          </div>
                        ) : (
                          <p className="mt-0.5 text-[12px] leading-relaxed text-zinc-500 break-words line-clamp-3">
                            {highlight(preview, headEvidence)}
                          </p>
                        )}
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
        </>
      )}
    </div>
  );
}
