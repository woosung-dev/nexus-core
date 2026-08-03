"use client";

import { useState } from "react";
import { Check, Loader2, MessageCircleMore, Send } from "lucide-react";

import { useChat } from "@/app/(protected)/chat/ChatProvider";

export function ClarificationCard() {
  const { clarification, awaiting, actOnClarification } = useChat();
  const [values, setValues] = useState<string[]>([]);
  const [custom, setCustom] = useState("");

  if (!clarification) return null;
  if (clarification.mode === "terminal") {
    return (
      <div className="shrink-0 border-t border-zinc-100 bg-white px-4 py-3 sm:px-6">
        <p className="mx-auto max-w-3xl text-sm text-zinc-600">{clarification.message}</p>
      </div>
    );
  }

  if (clarification.mode === "optional") {
    return (
      <div className="shrink-0 border-t border-amber-100 bg-amber-50/70 px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3">
          <p className="text-sm text-zinc-700">일반 안내를 먼저 드렸어요. 필요하면 내 상황에 맞춰 함께 확인할 수 있어요.</p>
          <button
            type="button"
            disabled={awaiting}
            onClick={() => void actOnClarification("start_companion")}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-amber-500 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {awaiting ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageCircleMore className="h-4 w-4" />}
            {clarification.cta_label ?? "함께 확인하기"}
          </button>
        </div>
      </div>
    );
  }

  const facet = clarification.facet;
  if (!facet) return null;
  const toggle = (option: string) => {
    setValues((current) => {
      if (facet.selection_mode === "single") return current[0] === option ? [] : [option];
      return current.includes(option)
        ? current.filter((value) => value !== option)
        : [...current, option];
    });
  };
  const addCustom = () => {
    const value = custom.trim();
    if (!value) return;
    setValues((current) =>
      facet.selection_mode === "single" ? [value] : [...new Set([...current, value])],
    );
    setCustom("");
  };
  const canSubmit = values.length > 0 && !awaiting;

  return (
    <div className="shrink-0 border-t border-amber-100 bg-amber-50/70 px-4 py-3 sm:px-6">
      <section className="mx-auto max-w-3xl rounded-2xl border border-amber-200 bg-white p-4 shadow-sm" aria-label="추가 확인">
        <p className="mb-3 text-sm font-semibold text-zinc-800">{facet.question}</p>
        {facet.options.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {facet.options.map((option) => {
              const selected = values.includes(option);
              return (
                <button
                  key={option}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => toggle(option)}
                  className={`rounded-full border px-3 py-1.5 text-sm ${selected ? "border-amber-500 bg-amber-500 text-white" : "border-amber-200 text-zinc-700"}`}
                >
                  {selected && <Check className="mr-1 inline h-3.5 w-3.5" />}{option}
                </button>
              );
            })}
          </div>
        )}
        {facet.allow_custom && (
          <div className="flex gap-2">
            <input
              value={custom}
              onChange={(event) => setCustom(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.nativeEvent.isComposing) {
                  event.preventDefault();
                  addCustom();
                }
              }}
              placeholder="직접 입력"
              className="min-w-0 flex-1 rounded-xl border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-amber-400"
            />
            <button type="button" onClick={addCustom} className="rounded-xl border border-amber-200 px-3 text-sm text-amber-800">추가</button>
          </div>
        )}
        <div className="mt-3 flex justify-end">
          <button
            type="button"
            disabled={!canSubmit}
            onClick={() => void actOnClarification("submit", values)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-amber-500 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {awaiting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} 확인
          </button>
        </div>
      </section>
    </div>
  );
}
