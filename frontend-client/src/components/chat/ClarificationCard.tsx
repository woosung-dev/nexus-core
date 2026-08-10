"use client";

// 봇이 되물었을 때 대화 안에 붙는 선택지 카드.
//
// 프로토타입(`ClarificationPrototype.tsx`)의 ask/handoff 렌더를 그대로 옮겨 왔다.
// **프레젠테이션 전용이다** — API 를 부르지 않고, 고른 값을 문장으로 만들어 `onSubmit` 으로
// 올려보낼 뿐이다. 실제 재질의는 `ChatProvider.sendMessage` 가 기존 `/chats/completions` 로
// 한다(세션·메시지 영속화, 인용 백필, 피드백 PATCH 를 전부 물려받는다).
//
// 문구는 전부 관리자가 쓴 것이다. 여기서 질문을 만들어 내지 않는다.

import { useState } from "react";
import { Check, CircleAlert, MessageSquareMore, Plus, Send, X } from "lucide-react";

import type { ChatClarification, ClarificationQuestion } from "@/types/api";

function OptionFields({
  questions,
  values,
  onChange,
  disabled,
}: {
  questions: ClarificationQuestion[];
  values: Record<string, string[]>;
  onChange: (question: ClarificationQuestion, next: string[]) => void;
  disabled: boolean;
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
          <fieldset key={question.id} className="space-y-2.5" disabled={disabled}>
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
                    className={`rounded-full border px-3 py-1.5 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
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

export function ClarificationCard({
  clarification,
  originalQuestion,
  onSubmit,
  disabled = false,
}: {
  clarification: ChatClarification;
  /** 되묻기 직전의 사용자 질문. 재질의 문장 앞에 붙여 검색어를 살린다. */
  originalQuestion: string;
  /** 고른 값을 담은 재질의 문장과 다음 라운드 번호. */
  onSubmit: (message: string, nextRound: number) => void;
  disabled?: boolean;
}) {
  const [values, setValues] = useState<Record<string, string[]>>({});
  const [sent, setSent] = useState(false);

  if (clarification.status === "handoff") {
    return (
      <section className="mt-3 rounded-2xl border border-amber-200 bg-amber-50/60 p-4">
        <div className="flex items-start gap-3">
          <CircleAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
          <p className="text-sm leading-6 text-zinc-700">
            현재 정보만으로 정확히 안내하기 어려워 담당자 확인이 필요합니다.
          </p>
        </div>
      </section>
    );
  }

  const questions = clarification.questions;
  // 필수 항목이 전부 채워져야 보낼 수 있다. 관리자가 정한 슬롯이므로 건너뛰기를 두지 않는다.
  const canSubmit =
    questions.length > 0 &&
    questions.every((question) => !question.required || (values[question.id]?.length ?? 0) > 0);

  const submit = () => {
    if (!canSubmit || sent || disabled) return;
    const picked = questions
      .map((question) => {
        const chosen = values[question.id] ?? [];
        return chosen.length ? `${question.question} → ${chosen.join(", ")}` : null;
      })
      .filter(Boolean)
      .join("\n");
    setSent(true);
    onSubmit(`${originalQuestion}\n\n${picked}`, clarification.round + 1);
  };

  return (
    <section className="mt-3 rounded-2xl border border-amber-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <MessageSquareMore className="h-4 w-4 text-amber-500" />
        <p className="text-sm font-semibold text-zinc-900">몇 가지만 확인할게요</p>
      </div>
      <OptionFields
        questions={questions}
        values={values}
        onChange={(question, next) =>
          setValues((previous) => ({ ...previous, [question.id]: next }))
        }
        disabled={sent || disabled}
      />
      <div className="mt-4">
        <button
          type="button"
          disabled={!canSubmit || sent || disabled}
          onClick={submit}
          className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send className="h-4 w-4" /> {sent ? "답변을 준비하고 있어요" : "답변 보기"}
        </button>
      </div>
    </section>
  );
}
