import { Menu, MoreVertical, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ChatHeaderProps {
  onMenuClick?: () => void;
}

export function ChatHeader({ onMenuClick }: ChatHeaderProps) {
  return (
    <header className="h-[76px] shrink-0 border-b border-zinc-900 bg-zinc-950/80 backdrop-blur-md flex items-center justify-between px-4 sm:px-6 sticky top-0 z-20">
      <div className="flex items-center gap-4">
        {/* Mobile Menu Trigger */}
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={onMenuClick}
          className="lg:hidden text-zinc-400 hover:text-white hover:bg-zinc-800 -ml-2"
        >
          <Menu className="w-5 h-5" />
        </Button>

        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center shrink-0 overflow-hidden relative">
            <div className="absolute inset-0 bg-amber-500/10" />
            <Bot className="w-5 h-5 text-amber-500 relative z-10" />
          </div>
          <div className="flex flex-col">
            <h2 className="text-base font-bold text-white leading-tight">축복상담AI</h2>
            <span className="text-xs text-zinc-400">범용</span>
          </div>
        </div>
      </div>

      <Button variant="ghost" size="icon" className="text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-full">
        <MoreVertical className="w-5 h-5" />
      </Button>
    </header>
  );
}
