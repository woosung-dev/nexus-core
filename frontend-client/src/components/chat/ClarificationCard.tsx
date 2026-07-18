"use client";
// 추가 정보를 받아 질문을 보완해 재전송하는 카드.

import { useState } from "react";
import { HelpCircle } from "lucide-react";
import { motion } from "framer-motion";

interface ClarificationCardProps {
  items: { id: string; question: string; options: string[] }[];
  originalQuestion: string;
  disabled?: boolean;
  onSubmit: (enrichedMessage: string) => void;
}

export function ClarificationCard({
  items,
  originalQuestion,
  disabled,
  onSubmit,
}: ClarificationCardProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [selectedOptions, setSelectedOptions] = useState<Record<string, string>>({});
  const [customAnswers, setCustomAnswers] = useState<Record<string, string>>({});

  const selectOption = (id: string, option: string) => {
    const next = selectedOptions[id] === option ? "" : option;
    setSelectedOptions((prev) => ({ ...prev, [id]: next }));
    setCustomAnswers((prev) => ({ ...prev, [id]: "" }));
    setAnswers((prev) => ({ ...prev, [id]: next }));
  };

  const setCustomAnswer = (id: string, value: string) => {
    setCustomAnswers((prev) => ({ ...prev, [id]: value }));
    setAnswers((prev) => ({ ...prev, [id]: value || selectedOptions[id] || "" }));
  };

  const submit = () => {
    const lines = items
      .map((it) => {
        const v = answers[it.id];
        return v ? `- ${it.question}: ${v}` : null;
      })
      .filter(Boolean)
      .join("\n");
    onSubmit(`${originalQuestion}\n\n[추가 정보]\n${lines}`);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, delay: 0.05 }}
      className="mt-3 rounded-2xl border border-amber-200 bg-amber-50/40 p-4 space-y-3 motion-safe:transition-opacity"
    >
      <div className="flex items-center gap-1.5 text-[13px] font-medium text-amber-700">
        <HelpCircle className="h-4 w-4 text-amber-500" />
        <span>몇 가지만 확인할게요</span>
      </div>
      {items.map((item) => (
        <div key={item.id} className="space-y-2">
          <p className="text-[13px] text-zinc-700">{item.question}</p>
          <div className="flex flex-wrap gap-1.5">
            {item.options.map((option) => {
              const selected = !customAnswers[item.id] && selectedOptions[item.id] === option;
              return (
                <button
                  key={option}
                  type="button"
                  disabled={disabled}
                  onClick={() => selectOption(item.id, option)}
                  className={`text-[13px] px-3.5 py-1.5 rounded-full border transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed ${
                    selected
                      ? "bg-amber-500 text-white border-amber-500"
                      : "bg-white border-amber-200 text-zinc-700 hover:border-amber-400 hover:bg-amber-50 hover:text-amber-700"
                  }`}
                >
                  {option}
                </button>
              );
            })}
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor={`clarification-${item.id}`} className="text-[12px] text-amber-700">
              직접 입력
            </label>
            <input
              id={`clarification-${item.id}`}
              disabled={disabled}
              value={customAnswers[item.id] ?? ""}
              onChange={(event) => setCustomAnswer(item.id, event.target.value)}
              className="text-[13px] px-3 py-1.5 rounded-full border border-amber-200 bg-white disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
        </div>
      ))}
      <button
        type="button"
        disabled={disabled || !Object.values(answers).some(Boolean)}
        onClick={submit}
        className="text-[13px] px-3.5 py-1.5 rounded-full bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        이대로 질문하기
      </button>
    </motion.div>
  );
}
