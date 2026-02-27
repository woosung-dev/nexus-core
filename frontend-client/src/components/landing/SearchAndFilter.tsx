import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search } from "lucide-react";

const CATEGORIES = [
  "전체", "범용", "코딩", "창작", "분석", "교육", "건강", "법률", "비즈니스"
];

export function SearchAndFilter({ 
  activeCategory = "전체", 
  onCategoryChange 
}: { 
  activeCategory?: string;
  onCategoryChange?: (category: string) => void;
}) {
  return (
    <div className="w-full flex md:items-center flex-col items-center mb-12 px-4 space-y-8">
      {/* Search Bar */}
      <div className="relative w-full max-w-2xl group">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground group-focus-within:text-amber-500 transition-colors" />
        <Input 
          type="text" 
          placeholder="챗봇 이름이나 기능으로 검색하세요..." 
          className="w-full h-14 pl-12 pr-4 bg-zinc-900/50 border-zinc-800 rounded-xl text-md focus-visible:ring-amber-500/50 focus-visible:border-amber-500 transition-all placeholder:text-zinc-500"
        />
      </div>

      {/* Categories */}
      <div className="w-full max-w-5xl overflow-x-auto pb-4 scrollbar-hide">
        <div className="flex w-max mx-auto gap-2 px-4 md:px-0">
          {CATEGORIES.map((category) => (
            <Button
              key={category}
              variant={activeCategory === category ? "default" : "outline"}
              className={`rounded-full px-6 transition-all ${
                activeCategory === category 
                  ? "bg-amber-500 hover:bg-amber-600 text-black font-semibold shadow-md shadow-amber-500/20 border-transparent" 
                  : "bg-zinc-900/40 border-zinc-800 text-zinc-300 hover:text-white hover:border-zinc-700"
              }`}
              onClick={() => onCategoryChange?.(category)}
            >
              {category}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}
