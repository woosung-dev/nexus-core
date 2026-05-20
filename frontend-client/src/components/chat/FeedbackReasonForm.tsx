// 봇 응답 메시지에 대한 피드백 사유 입력 (칩 + 자유텍스트). 저장/건너뛰기 모두 단일 PATCH 로 커밋.
import { useState } from "react";
import { motion } from "framer-motion";
import {
  FeedbackType,
  NEGATIVE_FEEDBACK_REASONS,
  POSITIVE_FEEDBACK_REASONS,
} from "@/types/api";

interface FeedbackReasonFormProps {
  type: FeedbackType;
  onSubmit: (reasons: string[], comment: string) => void;
}

const COMMENT_MAX = 1000;

export function FeedbackReasonForm({ type, onSubmit }: FeedbackReasonFormProps) {
  const [reasons, setReasons] = useState<string[]>([]);
  const [comment, setComment] = useState<string>("");

  const isDown = type === "down";
  const chipOptions = isDown ? NEGATIVE_FEEDBACK_REASONS : POSITIVE_FEEDBACK_REASONS;
  const title = isDown ? "어떤 점이 아쉬웠나요?" : "어떤 점이 좋았나요?";
  const containerCls = isDown
    ? "bg-red-50/60 border-red-100"
    : "bg-amber-50/60 border-amber-100";

  const toggle = (code: string) => {
    setReasons((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
    );
  };

  const handleSave = () => onSubmit(reasons, comment.trim());
  const handleSkip = () => onSubmit([], "");

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.15 }}
      className={`mt-3 rounded-xl border px-4 py-3 ${containerCls}`}
    >
      <div className="mb-2.5">
        <span className="text-[13px] font-medium text-zinc-700">
          {title} <span className="text-zinc-400 font-normal">(선택)</span>
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-2.5">
        {chipOptions.map((opt) => {
          const selected = reasons.includes(opt.code);
          return (
            <button
              key={opt.code}
              type="button"
              onClick={() => toggle(opt.code)}
              className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                selected
                  ? "bg-zinc-900 text-white border-zinc-900"
                  : "bg-white text-zinc-700 border-zinc-200 hover:border-zinc-400"
              }`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value.slice(0, COMMENT_MAX))}
        placeholder={
          isDown
            ? "좀 더 자세히 알려주시면 개선에 도움이 됩니다 (선택)"
            : "어떤 점이 좋았는지 자유롭게 적어주세요 (선택)"
        }
        rows={2}
        className="w-full text-[13px] text-zinc-800 placeholder:text-zinc-400 bg-white border border-zinc-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400"
      />

      <div className="flex justify-end gap-2 mt-2.5">
        <button
          type="button"
          onClick={handleSkip}
          className="px-3 py-1.5 text-xs text-zinc-500 hover:text-zinc-800 rounded-md transition-colors"
        >
          건너뛰기
        </button>
        <button
          type="button"
          onClick={handleSave}
          className="px-3.5 py-1.5 text-xs font-medium text-white bg-zinc-900 hover:bg-zinc-800 rounded-md transition-colors"
        >
          저장
        </button>
      </div>
    </motion.div>
  );
}
