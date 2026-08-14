// 한 턴이 8단계를 어떻게 지났는지 보여주는 관리자 전용 뷰.
//
// **왜 필요했나.** 사용자가 받는 문장은 여덟 단계의 합작인데(FAQ 가 가로챌 수도, strict 가
// 막을 수도, 빈 답변이 고정 문구로 갈릴 수도 있다) 지금까지 우리가 잰 것은 생성 하나였다.
// 「유보율」은 strict 와 unanswered 가 만드는 값이라 생성만 봐서는 아예 못 잰다.
//
// 이 화면의 주인공은 **주입한 근거와 답변이 표기한 근거의 대조**다. 첫 실측 턴에서 바로
// 표기 4건 중 2건이 주입 목록 밖으로 나왔고, strict 게이트는 「하나라도 맞으면 통과」라
// 막지 않았다. 그 사실이 한 줄로 보여야 한다.
"use client";

import { useMemo, useState } from "react";
import { ChevronDown, Activity } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface TraceStage {
  stage: string;
  decision: string;
  ms: number;
  [k: string]: unknown;
}

interface TraceConfig {
  bot_id?: number;
  bot_name?: string;
  model?: string;
  retrieval_mode?: string | null;
  evidence_policy_mode?: string;
  use_rag?: boolean;
  history_window?: number;
  prompt_sha8?: string;
  prompt_len?: number;
  stream?: boolean;
  code_rev?: string;
}

export interface TurnTrace {
  v?: number;
  total_ms?: number;
  config?: TraceConfig;
  stages?: TraceStage[];
}

const STAGE_LABEL: Record<string, string> = {
  faq: "FAQ",
  ops_facts: "운영 사실",
  retrieval: "근거 검색",
  strict: "근거 게이트",
  strip: "표기 제거",
  unanswered: "답변 못 함",
  term: "용어 통일",
  crisis: "위기 안내",
  record: "기록",
};

// 사람이 읽는 결정 문구. 원문 코드는 mono 로 따로 보여준다.
const DECISION_LABEL: Record<string, string> = {
  pass: "통과",
  faq_override: "FAQ 로 응답",
  policy_block: "정책 차단",
  none: "없음",
  overlay: "덧붙임",
  lexical: "어휘 검색",
  file_search: "의미 검색",
  both: "혼합",
  fallback: "폴백",
  skipped: "건너뜀",
  blocked: "차단",
  off: "꺼짐",
  stripped: "제거함",
  replaced: "고정 문구로 치환",
  appended: "안전 안내 덧붙임",
  self_refusal: "봇이 스스로 거절",
  applied: "적용",
  recorded: "기록함",
};

// 결정이 「주의해서 볼 것」인지. 색은 라벨과 **함께만** 쓴다(색만으로 뜻을 싣지 않는다).
function tone(stage: string, decision: string): "bad" | "warn" | "hot" | "ok" | "idle" {
  if (decision === "blocked" || decision === "policy_block") return "bad";
  if (decision === "fallback" || decision === "replaced" || decision === "self_refusal") return "warn";
  if (stage === "crisis") return "hot";
  if (stage === "retrieval") return "hot";
  if (stage === "unanswered" && decision === "none") return "ok";
  return "idle";
}

const TONE_CLASS: Record<string, string> = {
  bad: "bg-destructive/10 text-destructive",
  warn: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
  hot: "bg-primary/10 text-primary",
  ok: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  idle: "bg-muted text-muted-foreground",
};

/** `"reg-53:제53조(...)"` → `{ id, locator }`. locator 가 없는 형태도 받는다. */
function splitRef(ref: string): { id: string; locator: string } {
  const i = ref.indexOf(":");
  return i < 0 ? { id: ref, locator: "" } : { id: ref.slice(0, i), locator: ref.slice(i + 1) };
}

export function MessageTrace({ trace }: { trace?: TurnTrace | null }) {
  const [open, setOpen] = useState(false);

  const evidence = useMemo(() => {
    const stages = trace?.stages ?? [];
    const retrieval = stages.find((s) => s.stage === "retrieval");
    const strict = stages.find((s) => s.stage === "strict");
    const refs = (retrieval?.unit_refs as string[] | undefined) ?? [];
    const cited = (strict?.cited as string[] | undefined) ?? [];

    const injected = refs.map(splitRef).filter((r) => !r.id.startsWith("…"));
    const injectedIds = new Set(injected.map((r) => r.id));
    const citedSet = new Set(cited.filter((c) => !c.startsWith("…")));

    return {
      used: injected.filter((r) => citedSet.has(r.id)),
      unused: injected.filter((r) => !citedSet.has(r.id)),
      // 주입한 적 없는데 답변이 근거로 든 것. 이 화면이 존재하는 이유다.
      ghost: [...citedSet].filter((c) => !injectedIds.has(c)),
      hasCited: cited.length > 0,
    };
  }, [trace]);

  if (!trace?.stages?.length) return null;

  const cfg = trace.config ?? {};
  const total = trace.total_ms ?? 0;
  const slowest = Math.max(...trace.stages.map((s) => s.ms ?? 0), 1);

  return (
    <div className="mt-2 w-full rounded-md border bg-card">
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left hover:bg-muted/50">
          <Activity className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
          <span className="text-xs font-medium">실행 추적</span>
          <span className="text-2xs tabular-nums text-muted-foreground">
            {trace.stages.length}단계 · {Math.round(total).toLocaleString()}ms
          </span>
          {evidence.ghost.length > 0 && (
            <span className="rounded bg-destructive/10 px-1.5 py-0.5 text-2xs font-medium text-destructive">
              출처 불명 {evidence.ghost.length}
            </span>
          )}
          <ChevronDown
            className={`ml-auto size-3.5 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
            aria-hidden
          />
        </CollapsibleTrigger>

        <CollapsibleContent className="border-t">
          {/* 설정 스냅샷 — 「이 답변이 어느 프롬프트에서 나왔나」의 유일한 열쇠다. */}
          <div className="flex flex-wrap gap-1 border-b px-3 py-2">
            {[
              cfg.bot_name && `봇 ${cfg.bot_id} ${cfg.bot_name}`,
              cfg.model,
              cfg.retrieval_mode && `검색 ${DECISION_LABEL[cfg.retrieval_mode] ?? cfg.retrieval_mode}`,
              cfg.evidence_policy_mode && `정책 ${cfg.evidence_policy_mode}`,
              cfg.prompt_sha8 && `프롬프트 ${cfg.prompt_sha8} · ${cfg.prompt_len?.toLocaleString()}자`,
              cfg.code_rev && `코드 ${cfg.code_rev}`,
            ]
              .filter(Boolean)
              .map((t) => (
                <span key={t as string} className="rounded border px-1.5 py-0.5 text-2xs text-muted-foreground">
                  {t as string}
                </span>
              ))}
          </div>

          {/* 근거 대조. 이 블록이 이 화면의 주인공이다. */}
          {evidence.hasCited && (
            <div className="border-b px-3 py-2.5">
              {evidence.ghost.length > 0 && (
                <p className="mb-2 rounded-sm border-l-2 border-destructive bg-destructive/5 py-1 pl-2 text-2xs leading-relaxed">
                  답변이 <span className="font-mono font-medium">{evidence.ghost.join(" · ")}</span> 을 근거로
                  들었으나 이번 턴에 주입한 원문에 없습니다.
                </p>
              )}
              <div className="grid gap-x-4 gap-y-1 sm:grid-cols-2">
                <EvidenceList label="사용됨" tone="ok" rows={evidence.used} />
                <EvidenceList label="출처 불명" tone="bad" rows={evidence.ghost.map((id) => ({ id, locator: "주입한 적 없음" }))} />
                <EvidenceList label="주입했으나 미사용" tone="idle" rows={evidence.unused} />
              </div>
            </div>
          )}

          {/* 단계별. 시간 비중은 가는 획 하나로만 — 배경 트랙을 두면 표가 시끄러워진다. */}
          <ul className="divide-y">
            {trace.stages.map((s, i) => {
              const t = tone(s.stage, s.decision);
              return (
                <li key={`${s.stage}-${i}`} className="flex items-start gap-2 px-3 py-1.5">
                  <span className="w-4 shrink-0 pt-0.5 text-2xs tabular-nums text-muted-foreground">{i + 1}</span>
                  <span className="w-20 shrink-0 pt-0.5 text-2xs">{STAGE_LABEL[s.stage] ?? s.stage}</span>
                  <span className={`shrink-0 rounded px-1.5 py-0.5 text-2xs ${TONE_CLASS[t]}`}>
                    {DECISION_LABEL[s.decision] ?? s.decision}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-2xs text-muted-foreground">
                    <StageFacts stage={s} />
                  </span>
                  <span className="shrink-0 text-right text-2xs tabular-nums text-muted-foreground">
                    {(s.ms ?? 0).toFixed(1)}ms
                    <i
                      className="mt-0.5 block h-px bg-primary"
                      style={{ width: `${Math.max(1, ((s.ms ?? 0) / slowest) * 44)}px`, marginLeft: "auto" }}
                    />
                  </span>
                </li>
              );
            })}
          </ul>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

function EvidenceList({
  label,
  tone,
  rows,
}: {
  label: string;
  tone: "ok" | "bad" | "idle";
  rows: { id: string; locator: string }[];
}) {
  if (!rows.length) return null;
  return (
    <div className="py-0.5">
      <p className={`mb-0.5 text-2xs ${tone === "bad" ? "text-destructive" : "text-muted-foreground"}`}>
        {label} <span className="tabular-nums">{rows.length}</span>
      </p>
      <ul className="space-y-0.5">
        {rows.map((r) => (
          <li key={r.id} className="flex gap-1.5 text-2xs leading-snug">
            <span className={`shrink-0 font-mono ${tone === "bad" ? "text-destructive" : ""}`}>{r.id}</span>
            <span className="min-w-0 truncate text-muted-foreground" title={r.locator}>
              {r.locator}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** 단계가 무엇을 보고 정했는지. 알려진 키만 사람 말로 옮기고 나머지는 그대로 흘린다. */
function StageFacts({ stage: s }: { stage: TraceStage }) {
  const bits: string[] = [];
  const n = (k: string) => (typeof s[k] === "number" ? (s[k] as number) : undefined);

  if (s.stage === "faq") {
    if (n("faqs") !== undefined) bits.push(`등록 ${n("faqs")}건`);
    if (typeof s.top_similarity === "number") bits.push(`최고 유사도 ${(s.top_similarity as number).toFixed(3)} / 임계 ${s.threshold}`);
    if (s.skipped) bits.push(String(s.skipped));
  } else if (s.stage === "ops_facts") {
    if (n("n") !== undefined) bits.push(`사실 ${n("n")}건`);
    if (Array.isArray(s.kinds)) bits.push((s.kinds as string[]).join("·"));
    if (n("prompt_len") !== undefined) bits.push(`프롬프트 ${n("prompt_len")!.toLocaleString()}자`);
  } else if (s.stage === "retrieval") {
    if (n("units") !== undefined) bits.push(`주입 ${n("units")}건`);
    if (n("answer_len") !== undefined) bits.push(`답변 ${n("answer_len")}자`);
    if (n("citations") !== undefined) bits.push(`인용 ${n("citations")}건`);
    if (s.direct_citation === false) bits.push("직접 인용 없음");
    if (Array.isArray(s.reasons)) bits.push((s.reasons as string[]).join("·"));
  } else if (s.stage === "strict") {
    if (Array.isArray(s.cited)) bits.push(`표기 ${(s.cited as string[]).length}건`);
    if (s.reason) bits.push(String(s.reason));
  } else if (s.stage === "strip") {
    if (n("removed_chars")) bits.push(`${n("removed_chars")}자 제거`);
  } else if (s.stage === "term") {
    if (n("rules")) bits.push(`규칙 ${n("rules")}건`);
  } else if (s.stage === "record") {
    if (Array.isArray(s.reasons)) bits.push((s.reasons as string[]).join("·"));
  }
  return <>{bits.join(" · ")}</>;
}
