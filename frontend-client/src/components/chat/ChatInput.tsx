import { Send } from "lucide-react";

export function ChatInput() {
  return (
    <div className="shrink-0 border-t border-zinc-900 bg-zinc-950 p-4 sm:px-6">
      <div className="max-w-4xl mx-auto flex gap-3 relative">
        <div className="relative flex-1">
          <input 
            type="text" 
            placeholder="메시지를 입력하세요..." 
            className="w-full bg-black border border-zinc-800 rounded-xl px-4 py-4 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:border-amber-500/50 transition-colors shadow-sm min-h-[56px]"
          />
        </div>
        <button 
          className="w-14 h-[56px] shrink-0 bg-amber-500 hover:bg-amber-400 text-black flex items-center justify-center rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(245,158,11,0.2)]"
        >
          <Send className="w-5 h-5 ml-1" />
        </button>
      </div>
    </div>
  );
}
