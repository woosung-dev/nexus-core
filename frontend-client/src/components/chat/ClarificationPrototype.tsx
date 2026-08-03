"use client";

// PROTOTYPE — 선택된 인라인 카드형 맥락 보완 UX.
// /chat/new/{botId}?clarify-prototype=1 에서만 사용하며, ChatSession/Message를 저장하지 않는다.

import { useMemo, useState } from "react";
import { Check, CircleAlert, FileText, Loader2, MessageSquareMore, Plus, Send, X } from "lucide-react";

import api from "@/lib/api";
import type { Citation } from "@/types/api";

type Mode = "fixture" | "live";
type SelectionMode = "single" | "multiple";

type ClarificationQuestion = {
  id: string;
  question: string;
  selection_mode: SelectionMode;
  options: string[];
  allow_custom: boolean;
  required: boolean;
  policy: boolean;
};

type ClarificationDiagnostics = {
  applied_rule_id: string | null;
  policy_match_status: "disabled" | "matched" | "unmatched" | "uncertain";
  missing_slot_ids: string[];
  document_ref_ids: string[];
};

type ClarificationAnswer = {
  question_id: string;
  question: string;
  values: string[];
};

type ClarificationResponse = {
  status: "ask" | "ready" | "handoff";
  source: "fixture" | "live" | "fallback";
  questions: ClarificationQuestion[];
  summary: string | null;
  citations: Citation[];
  fallback: boolean;
  handoff_message: string | null;
  diagnostics: ClarificationDiagnostics;
  policy_context: string | null;
};

type DocumentAnswer = {
  content: string;
  citations: Citation[];
  followups: string[];
  source: "rag";
};

const INITIAL_REQUEST = "우리 서비스에 예약 기능을 넣고 싶어요.";

function selectedCount(values: Record<string, string[]>) {
  return Object.values(values).reduce((total, items) => total + items.length, 0);
}

function OptionFields({
  questions,
  values,
  onChange,
}: {
  questions: ClarificationQuestion[];
  values: Record<string, string[]>;
  onChange: (question: ClarificationQuestion, next: string[]) => void;
}) {
  const [customValues, setCustomValues] = useState<Record<string, string>>({});

  const addCustom = (question: ClarificationQuestion) => {
    const custom = customValues[question.id]?.trim();
    if (!custom) return;
    const current = values[question.id] ?? [];
    onChange(
      question,
      question.selection_mode === "single" ? [custom] : [...new Set([...current, custom])],
    );
    setCustomValues((previous) => ({ ...previous, [question.id]: "" }));
  };

  return (
    <div className="space-y-5">
      {questions.map((question) => {
        const current = values[question.id] ?? [];
        const toggleOption = (option: string) => {
          const included = current.includes(option);
          const next =
            question.selection_mode === "single"
              ? included ? [] : [option]
              : included ? current.filter((value) => value !== option) : [...current, option];
          onChange(question, next);
        };

        return (
          <fieldset key={question.id} className="space-y-2.5">
            <legend className="text-sm font-semibold text-zinc-800">
              {question.question}
              {question.required && <span className="ml-2 text-xs font-medium text-amber-700">필수</span>}
              <span className="ml-2 text-xs font-normal text-zinc-400">
                {question.selection_mode === "multiple" ? "복수 선택" : "하나 선택"}
              </span>
            </legend>
            <div className="flex flex-wrap gap-2">
              {question.options.map((option) => {
                const active = current.includes(option);
                return (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleOption(option)}
                    className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                      active
                        ? "border-amber-500 bg-amber-500 text-white"
                        : "border-amber-200 bg-white text-zinc-700 hover:border-amber-400 hover:bg-amber-50"
                    }`}
                  >
                    {active && <Check className="mr-1 inline h-3.5 w-3.5" />}
                    {option}
                  </button>
                );
              })}
            </div>
            {question.allow_custom && (
              <div className="flex gap-2">
                <input
                  value={customValues[question.id] ?? ""}
                  onChange={(event) =>
                    setCustomValues((previous) => ({ ...previous, [question.id]: event.target.value }))
                  }
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.nativeEvent.isComposing) {
                      event.preventDefault();
                      addCustom(question);
                    }
                  }}
                  placeholder="직접 입력"
                  className="min-w-0 flex-1 rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-amber-400"
                />
                <button
                  type="button"
                  onClick={() => addCustom(question)}
                  className="inline-flex items-center gap-1 rounded-lg border border-amber-200 px-3 py-2 text-sm text-amber-700 hover:bg-amber-50"
                >
                  <Plus className="h-4 w-4" /> 추가
                </button>
              </div>
            )}
            {current.filter((value) => !question.options.includes(value)).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => onChange(question, current.filter((item) => item !== value))}
                className="mr-1.5 inline-flex items-center gap-1 rounded-full bg-zinc-100 px-2.5 py-1 text-xs text-zinc-700 hover:bg-zinc-200"
              >
                {value} <X className="h-3 w-3" />
              </button>
            ))}
          </fieldset>
        );
      })}
    </div>
  );
}

export function ClarificationPrototype({ botId }: { botId: string | null }) {
  const [mode, setMode] = useState<Mode>("fixture");
  const [requestMessage, setRequestMessage] = useState(INITIAL_REQUEST);
  const [activeRequest, setActiveRequest] = useState<string | null>(null);
  const [decision, setDecision] = useState<ClarificationResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [round, setRound] = useState(0);
  const [groundingCitations, setGroundingCitations] = useState<Citation[]>([]);
  const [summary, setSummary] = useState("");
  const [completed, setCompleted] = useState<"answered" | "skipped" | null>(null);
  const [documentAnswer, setDocumentAnswer] = useState<DocumentAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [answerLoading, setAnswerLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasPolicyQuestions = decision?.status === "ask" && decision.questions.some((question) => question.policy);
  const canSubmit = hasPolicyQuestions
    ? Boolean(decision?.questions.every((question) => (answers[question.id] ?? []).length > 0))
    : selectedCount(answers) > 0;
  const stateLabel = useMemo(() => {
    if (answerLoading) return "답변을 준비하고 있어요";
    if (documentAnswer) return "답변 완료";
    if (decision?.status === "handoff") return "담당자 안내";
    if (decision?.status === "ready") return "요청 정리 완료";
    if (decision?.status === "ask") return "맥락 수집 중";
    return "시작 전";
  }, [answerLoading, decision, documentAnswer]);

  const requestDecision = async (
    nextAnswers: ClarificationAnswer[],
    nextRound: number,
    message: string,
    policyRuleId?: string | null,
    policyContext?: string | null,
  ): Promise<ClarificationResponse | null> => {
    const numericBotId = Number(botId);
    if (!Number.isInteger(numericBotId)) {
      setError("테스트할 봇을 먼저 선택해 주세요.");
      return null;
    }
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post<ClarificationResponse>("/clarification-preview", {
        bot_id: numericBotId,
        message,
        answers: nextAnswers,
        policy_rule_id: policyRuleId ?? undefined,
        policy_context: policyContext ?? undefined,
        round: nextRound,
        mode,
      });
      setDecision(data);
      setRound(nextRound);
      setAnswers({});
      if (data.status === "ask") {
        setGroundingCitations(data.citations);
      } else {
        setSummary(data.summary ?? "");
      }
      return data;
    } catch (requestError) {
      const detail = (requestError as { response?: { data?: { message?: string } } }).response?.data?.message;
      setError(detail ?? "맥락 보완 질문을 불러오지 못했습니다.");
      return null;
    } finally {
      setLoading(false);
    }
  };

  const requestDocumentAnswer = async (
    kind: "answered" | "skipped",
    requestSummary: string,
  ) => {
    if (answerLoading) return;
    const numericBotId = Number(botId);
    if (numericBotId === 0) {
      setError("답변은 관리자에서 만든 테스트 봇 URL로 열어 확인해 주세요.");
      return;
    }
    setAnswerLoading(true);
    setError(null);
    setCompleted(kind);
    try {
      const { data } = await api.post<DocumentAnswer>("/clarification-preview/answer", {
        bot_id: numericBotId,
        message: requestSummary,
      });
      setDocumentAnswer(data);
    } catch (requestError) {
      const detail = (requestError as { response?: { data?: { message?: string } } }).response?.data?.message;
      setError(detail ?? "답변을 생성하지 못했습니다.");
      setCompleted(null);
    } finally {
      setAnswerLoading(false);
    }
  };

  const finishWithSummary = async (
    nextAnswers: ClarificationAnswer[],
    kind: "answered" | "skipped",
  ) => {
    const response = await requestDecision(
      nextAnswers,
      1,
      activeRequest ?? requestMessage.trim(),
      decision?.diagnostics.applied_rule_id,
      decision?.policy_context,
    );
    if (response?.status === "ready" && response.summary) {
      await requestDocumentAnswer(kind, response.summary);
    }
  };

  const start = () => {
    const nextRequest = requestMessage.trim();
    if (!nextRequest) {
      setError("테스트할 요청을 입력해 주세요.");
      return;
    }
    setDecision(null);
    setActiveRequest(nextRequest);
    setAnswers({});
    setRound(0);
    setGroundingCitations([]);
    setSummary("");
    setCompleted(null);
    setDocumentAnswer(null);
    void (async () => {
      const response = await requestDecision([], 0, nextRequest);
      if (response?.status === "ready" && response.summary) {
        await requestDocumentAnswer("skipped", response.summary);
      }
    })();
  };

  const updateAnswer = (question: ClarificationQuestion, values: string[]) => {
    setAnswers((previous) => ({ ...previous, [question.id]: values }));
  };

  const submitQuestions = () => {
    if (!decision || !canSubmit) return;
    const currentAnswers = decision.questions
      .map((question) => ({
        question_id: question.id,
        question: question.question,
        values: answers[question.id] ?? [],
      }))
      .filter((answer) => answer.values.length > 0);
    void finishWithSummary(currentAnswers, "answered");
  };

  const skipQuestions = () => {
    if (!decision || hasPolicyQuestions) return;
    void finishWithSummary([], "skipped");
  };

  return (
    <div className="relative flex-1 overflow-y-auto bg-gradient-to-b from-amber-50/50 via-white to-white">
      <div className="mx-auto w-full max-w-3xl space-y-7 px-4 py-10 pb-28 sm:px-6">
        <section className="rounded-2xl border border-amber-200 bg-amber-50/70 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">PROTOTYPE · 인라인 카드형</p>
          <h2 className="mt-1 text-xl font-bold text-zinc-900">필요한 맥락을 먼저 확인한 뒤 답변을 준비합니다</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-600">
            첫 요청에서 등록 문서를 한 번 확인해 필요한 질문을 함께 만들고, 선택값은 저장하지 않습니다. 답하거나 건너뛴 내용은 요청을 정리하는 데만 사용합니다.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {(["fixture", "live"] as Mode[]).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setMode(item)}
                className={`rounded-full border px-3 py-1.5 text-sm ${
                  mode === item ? "border-zinc-800 bg-zinc-800 text-white" : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400"
                }`}
              >
                {item === "fixture" ? "고정 시나리오" : "문서 기반 확인"}
              </button>
            ))}
            <span className="self-center text-xs text-zinc-500">봇 ID: {botId ?? "-"}</span>
          </div>
          <label className="mt-4 block text-sm font-semibold text-zinc-800" htmlFor="prototype-request">테스트할 사용자 요청</label>
          <textarea
            id="prototype-request"
            value={requestMessage}
            onChange={(event) => setRequestMessage(event.target.value)}
            rows={3}
            placeholder="예: 회원과 비회원이 모두 예약할 수 있는 클래스 예약 기능을 만들고 싶어요."
            className="mt-2 w-full rounded-xl border border-amber-200 bg-white p-3 text-sm leading-6 text-zinc-800 outline-none focus:border-amber-500"
          />
          <button
            type="button"
            onClick={start}
            disabled={loading || answerLoading}
            className="mt-3 inline-flex items-center gap-2 rounded-xl bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-zinc-700 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageSquareMore className="h-4 w-4" />}
            맥락 보완 시작
          </button>
        </section>

        {decision && activeRequest && (
          <div className="flex justify-end">
            <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-sm bg-amber-500 px-5 py-3 text-[15px] font-medium text-white shadow-sm">
              {activeRequest}
            </div>
          </div>
        )}

        {loading && <div className="flex items-center gap-3 text-sm text-zinc-500"><Loader2 className="h-4 w-4 animate-spin text-amber-500" /> 문서를 확인하고 있어요.</div>}
        {error && <div role="alert" className="flex gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"><CircleAlert className="h-4 w-4 shrink-0" />{error}</div>}

        {decision?.status === "ask" && (
          <div className="flex gap-3">
            <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-zinc-100 bg-white text-amber-500 shadow-sm"><MessageSquareMore className="h-5 w-5" /></div>
            <section className="w-full rounded-2xl rounded-tl-sm border border-amber-200 bg-white p-5 shadow-sm">
              <div className="mb-5"><p className="font-semibold text-zinc-900">몇 가지만 확인할게요</p><p className="text-xs text-zinc-500">{hasPolicyQuestions ? "모든 필수 항목을 선택하거나 직접 입력해 주세요." : "선택하거나 직접 내용을 추가할 수 있어요."}</p></div>
              {decision.source === "live" && groundingCitations.length > 0 && (
                <details className="mb-5 rounded-xl border border-amber-100 bg-amber-50/60 p-3">
                  <summary className="cursor-pointer text-xs font-medium text-amber-800">등록 문서 {groundingCitations.length}개를 참고해 질문을 만들었어요</summary>
                  <ul className="mt-2 space-y-2 text-xs leading-5 text-zinc-600">
                    {groundingCitations.map((citation, index) => (
                      <li key={`${citation.title ?? "문서"}-${index}`}>
                        <span className="font-medium text-zinc-800">{citation.title ?? "문서"}</span>
                        {citation.content ? <span className="mt-0.5 block line-clamp-2">{citation.content}</span> : null}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
              <OptionFields questions={decision.questions} values={answers} onChange={updateAnswer} />
              <div className="mt-5 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={!canSubmit || loading || answerLoading}
                  onClick={submitQuestions}
                  className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Send className="h-4 w-4" /> 답변 보기
                </button>
                {!hasPolicyQuestions && <button
                  type="button"
                  disabled={loading || answerLoading}
                  onClick={skipQuestions}
                  className="rounded-xl border border-amber-300 bg-white px-4 py-2.5 text-sm font-semibold text-amber-800 hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  건너뛰고 답변 보기
                </button>}
              </div>
            </section>
          </div>
        )}

        {decision?.status === "ready" && (
          <section className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 shadow-sm">
            <div className="flex items-start gap-3"><Check className="mt-0.5 h-5 w-5 text-emerald-600" /><div><h3 className="font-semibold text-zinc-900">요청 내용을 정리했어요</h3><p className="mt-1 text-sm text-zinc-600">정리한 내용으로 답변을 준비하고 있어요.</p></div></div>
            {decision.fallback && <p className="mt-4 rounded-lg bg-amber-100 p-3 text-sm text-amber-800">현재 요청을 바탕으로 답변을 준비할게요.</p>}
            <p className="mt-4 whitespace-pre-wrap rounded-xl border border-emerald-200 bg-white p-3 text-sm leading-6 text-zinc-800">{summary}</p>
          </section>
        )}

        {decision?.status === "handoff" && (
          <section className="rounded-2xl border border-amber-200 bg-amber-50/60 p-5 shadow-sm">
            <div className="flex items-start gap-3"><CircleAlert className="mt-0.5 h-5 w-5 text-amber-700" /><div><h3 className="font-semibold text-zinc-900">담당자 확인이 필요해요</h3><p className="mt-1 text-sm leading-6 text-zinc-700">{decision.handoff_message ?? "현재 정보만으로 정확히 안내하기 어려워 담당자 확인이 필요합니다."}</p></div></div>
          </section>
        )}

        {answerLoading && <div className="flex items-center gap-3 text-sm text-zinc-500"><Loader2 className="h-4 w-4 animate-spin text-emerald-600" /> 문서를 확인하고 답변을 준비하고 있어요.</div>}

        {documentAnswer && (
          <div className="flex gap-3">
            <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-zinc-100 bg-white text-emerald-600 shadow-sm"><FileText className="h-5 w-5" /></div>
            <section className="w-full rounded-2xl rounded-tl-sm border border-emerald-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">답변 · {completed === "answered" ? "확인한 내용 반영" : "바로 보기"}</p>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-zinc-800">{documentAnswer.content}</p>
              {documentAnswer.citations.length > 0 && <details className="mt-4 rounded-xl border border-zinc-200 bg-zinc-50 p-3"><summary className="cursor-pointer text-sm font-medium text-zinc-700">참고한 문서 {documentAnswer.citations.length}개</summary><ul className="mt-3 space-y-2 text-sm text-zinc-600">{documentAnswer.citations.map((citation, index) => <li key={`${citation.title ?? "문서"}-${index}`}><span className="font-medium text-zinc-800">{citation.title ?? "문서"}</span>{citation.content ? <span className="block mt-1 line-clamp-3">{citation.content}</span> : null}</li>)}</ul></details>}
              {documentAnswer.followups.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{documentAnswer.followups.map((followup) => <span key={followup} className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs text-emerald-800">{followup}</span>)}</div>}
            </section>
          </div>
        )}
      </div>

      <div className="fixed bottom-4 left-4 rounded-lg border border-zinc-200 bg-white/95 px-3 py-2 text-xs text-zinc-500 shadow-sm">
        상태: {stateLabel} · {mode === "fixture" ? "고정 시나리오" : "문서 기반 확인"} · {selectedCount(answers)}개 선택 · {round + 1}회차
      </div>
    </div>
  );
}
