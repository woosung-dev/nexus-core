import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, X } from "lucide-react";

export function SearchAndFilter({ 
  activeCategory = "전체", 
  categories = [],
  isLoading = false,
  searchValue = "",
  onCategoryChange,
  onSearchChange
}: { 
  activeCategory?: string;
  categories?: string[];
  isLoading?: boolean;
  searchValue?: string;
  onCategoryChange?: (category: string) => void;
  onSearchChange?: (value: string) => void;
}) {
  const [localQuery, setLocalQuery] = useState(searchValue);

  // 싱크 맞추기 (외부에서 searchValue가 바뀌면 localQuery도 업데이트)
  useEffect(() => {
    setLocalQuery(searchValue);
  }, [searchValue]);

  const handleSearch = () => {
    onSearchChange?.(localQuery);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const clearSearch = () => {
    setLocalQuery("");
    onSearchChange?.("");
  };

  const displayCategories = ["전체", ...categories];

  return (
    <div className="w-full flex md:items-center flex-col items-center mb-12 px-4 space-y-8">
      {/* Search Bar */}
      <div className="relative w-full max-w-2xl group flex items-center">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground group-focus-within:text-amber-500 transition-colors" />
          <Input 
            id="bot-search-input"
            type="text" 
            placeholder="챗봇 이름이나 기능으로 검색하세요..." 
            value={localQuery}
            onChange={(e) => setLocalQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full h-14 pl-12 pr-28 bg-zinc-900/50 border-zinc-800 rounded-xl text-md focus-visible:ring-amber-500/50 focus-visible:border-amber-500 transition-all placeholder:text-zinc-500"
          />
          {localQuery && (
            <button 
              onClick={clearSearch}
              className="absolute right-[90px] top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition-colors p-1"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          <Button 
            onClick={handleSearch}
            className="absolute right-2 top-1/2 -translate-y-1/2 h-10 px-4 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-lg shadow-lg shadow-amber-500/10"
          >
            검색
          </Button>
        </div>
      </div>

      {/* Categories */}
      <div className="w-full max-w-5xl overflow-x-auto pb-4 scrollbar-hide">
        <div className="flex w-max mx-auto gap-2 px-4 md:px-0">
          {isLoading ? (
            // Skeleton Loading State
            <>
              <div className="h-10 w-24 rounded-full bg-zinc-800 animate-pulse" />
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-10 w-20 rounded-full bg-zinc-800/50 animate-pulse" />
              ))}
            </>
          ) : (
            displayCategories.map((category) => (
              <Button
                key={category}
                id={`category-btn-${category}`}
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
            ))
          )}
        </div>
      </div>
    </div>
  );
}
