// 봇 답변 아래에 노출되는 후속 질문 칩. 클릭 시 즉시 sendMessage 호출.
import { Lightbulb } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface FollowupPillsProps {
  items: string[];
  onSelect: (question: string) => void;
  disabled?: boolean;
}

export function FollowupPills({ items, onSelect, disabled }: FollowupPillsProps) {
  if (!items || items.length === 0) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18, delay: 0.05 }}
        className="mt-3 flex flex-col gap-2"
      >
        <div className="flex items-center gap-1.5 text-[11px] font-medium text-zinc-500 uppercase tracking-wider">
          <Lightbulb className="w-3 h-3 text-amber-500" />
          <span>이어서 물어보면 좋을 질문</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {items.slice(0, 3).map((q, i) => (
            <button
              key={`${i}-${q}`}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(q)}
              className="text-[13px] px-3.5 py-1.5 rounded-full bg-white border border-amber-200 text-zinc-700 hover:border-amber-400 hover:bg-amber-50 hover:text-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              {q}
            </button>
          ))}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
