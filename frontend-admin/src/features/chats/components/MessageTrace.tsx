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
    // ⚠ 모델이 받는 근거는 `unit_refs` 만이 아니다. 어휘 경로는 `# 규정 원문`(units) 뒤에
    // `# 참고 정리`(위키 페이지)를 함께 넣고, 그 페이지의 `## 사실` 에는 원문 인용이 붙어
    // 있어 units 에 없는 조문이 프롬프트에 들어간다. 이걸 빼고 대조하면 **정확한 인용이
    // 「출처 불명」으로 찍힌다** — replay 600건에서 그렇게 잡힌 57건 중 56건이 오경보였다.
    const pageSrcs = (retrieval?.page_srcs as string[] | undefined) ?? [];

    const injected = refs.map(splitRef).filter((r) => !r.id.startsWith("…"));
    const injectedIds = new Set(injected.map((r) => r.id));
    const availableIds = new Set([...injectedIds, ...pageSrcs]);
    const citedSet = new Set(cited.filter((c) => !c.startsWith("…")));

    return {
      used: injected.filter((r) => citedSet.has(r.id)),
      unused: injected.filter((r) => !citedSet.has(r.id)),
      // 위키 페이지로 들어온 근거를 답변이 인용한 것. 정상이다 — 다만 원문 카드로는 안 보인다.
      viaPage: [...citedSet].filter((c) => !injectedIds.has(c) && availableIds.has(c)),
      // 어느 채널로도 준 적 없는데 답변이 근거로 든 것. 이 화면이 존재하는 이유다.
      ghost: [...citedSet].filter((c) => !availableIds.has(c)),
      pageCount: (retrieval?.pages as string[] | undefined)?.length ?? 0,
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
                  들었으나 이번 턴에는 <strong>원문으로도 참고 정리로도 준 적이 없습니다.</strong>
                </p>
              )}
              <div className="grid gap-x-4 gap-y-1 sm:grid-cols-2">
                <EvidenceList label="사용됨" tone="ok" rows={evidence.used} />
                <EvidenceList label="출처 불명" tone="bad" rows={evidence.ghost.map((id) => ({ id, locator: "어느 채널로도 준 적 없음" }))} />
                <EvidenceList label="주입했으나 미사용" tone="idle" rows={evidence.unused} />
                <EvidenceList
                  label="참고 정리로 받음"
                  tone="idle"
                  rows={evidence.viaPage.map((id) => ({ id, locator: "위키 페이지가 실어 온 조문" }))}
                />
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
                  {/* 판독 문장. 잘라내지 않는다 — 이 화면의 목적이 「읽고 개발자에게 전달」이다. */}
                  <span className="min-w-0 flex-1 text-2xs leading-relaxed text-muted-foreground">
                    <StageFacts stage={s} evidence={evidence} />
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

/** 단계가 무엇을 보고 그렇게 정했는지를 **완성된 한국어 문장**으로 쓴다.
 *
 * 조각(`표기 4건 · 주입 4건`)이 아니라 문장이어야 하는 이유: 이 화면을 읽는 사람은
 * 개발자가 아니라 관리자다. 화면을 캡처해 그대로 전달할 수 있어야 값어치가 생긴다.
 * 알 수 없는 단계는 빈 문자열을 돌려주고 조용히 비운다 — 억지 문장을 만들지 않는다. */
function StageFacts({
  stage: s,
  evidence,
}: {
  stage: TraceStage;
  evidence: { used: unknown[]; ghost: string[]; viaPage: string[]; pageCount: number };
}) {
  const n = (k: string) => (typeof s[k] === "number" ? (s[k] as number) : undefined);
  const num = (v?: number) => (v ?? 0).toLocaleString();

  let text = "";

  if (s.stage === "faq") {
    if (s.decision === "faq_override") text = "등록된 응답으로 답했습니다";
    else if (typeof s.top_similarity === "number")
      text = `최고 유사도 ${(s.top_similarity as number).toFixed(3)} 가 임계 ${s.threshold} 에 못 미쳐 넘겼습니다`;
    else text = `등록된 FAQ ${num(n("faqs"))}건이라 검색을 건너뛰었습니다`;
  } else if (s.stage === "ops_facts") {
    text = n("n")
      ? `승인된 운영 사실 ${num(n("n"))}건을 프롬프트에 덧붙였습니다`
      : `승인된 운영 사실 0건. 프롬프트가 ${num(n("prompt_len"))}자 그대로입니다`;
  } else if (s.stage === "crisis") {
    text = "위기 신호로 보고 안전 안내를 답변 앞에 붙였습니다";
  } else if (s.stage === "retrieval") {
    if (s.decision === "skipped") {
      text = "검색을 쓰지 않는 봇이라 건너뛰었습니다";
    } else {
      const how = DECISION_LABEL[String(s.decision)] ?? String(s.decision);
      const page = evidence.pageCount ? `, 참고 정리 ${evidence.pageCount}쪽을 함께 넣고` : "";
      text = `${how}으로 원문 ${num(n("units"))}건을 골라 주입${page} ${num(n("answer_len"))}자를 생성했습니다`;
      if (Array.isArray(s.reasons) && s.reasons.length)
        text += ` (${(s.reasons as string[]).join("·")})`;
    }
  } else if (s.stage === "strict") {
    const cited = Array.isArray(s.cited) ? (s.cited as string[]).length : 0;
    if (s.decision === "blocked") {
      text = "준 근거를 짚지 못해 답변을 고정 문구로 바꿨습니다";
    } else if (s.decision === "off") {
      text = `근거 게이트가 꺼져 있어 표기 ${cited}건을 검사하지 않았습니다`;
    } else if (cited === 0) {
      text = "답변이 근거를 하나도 표기하지 않았습니다";
    } else {
      const ok = cited - evidence.ghost.length;
      text = `표기 ${cited}건 중 ${ok}건이 준 근거와 맞아 통과시켰습니다`;
      if (evidence.viaPage.length)
        text += ` (${evidence.viaPage.length}건은 참고 정리로 받은 것)`;
      if (evidence.ghost.length) text += `. 나머지 ${evidence.ghost.length}건은 확인하지 않습니다`;
    }
  } else if (s.stage === "strip") {
    text = n("removed_chars")
      ? `화면에 나가면 안 되는 내부 표기 ${num(n("removed_chars"))}자를 벗겼습니다`
      : "벗겨낼 내부 표기가 없었습니다";
  } else if (s.stage === "unanswered") {
    text =
      s.decision === "none"
        ? "빈 답변도 자기거절도 아니라 답변 못 함 목록에 넣지 않았습니다"
        : "답변 못 함으로 기록했습니다";
  } else if (s.stage === "term") {
    text = n("rules") ? `표기 통일 규칙 ${num(n("rules"))}건을 적용했습니다` : "적용할 표기 통일 규칙이 없습니다";
  } else if (s.stage === "record") {
    text = Array.isArray(s.reasons) && s.reasons.length
      ? `남긴 신호: ${(s.reasons as string[]).join("·")}`
      : "남길 신호가 없습니다";
  }

  return <>{text}</>;
}
