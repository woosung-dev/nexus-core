"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Header from "@/components/layout/Header";
import { HeroSection } from "@/components/landing/HeroSection";
import { SearchAndFilter } from "@/components/landing/SearchAndFilter";
import { BotGrid } from "@/components/landing/BotGrid";
import { BotListResponse } from "@/types/api";

export function LandingClient() {
  const [activeCategory, setActiveCategory] = useState("전체");
  const [searchQuery, setSearchQuery] = useState("");

  // React Query Client: 서버에서 넘겨받은 캐시(`HydrationBoundary`)를 활용해 즉시 표시
  // serverFetch 대신 브라우저용 API 호출이 필요하지만, 여기서는 단순화를 위해 RSC 주입 데이터를 소비만 하거나,
  // 브라우저 측 API client(axios)로 재구성할 수도 있습니다.
  // hydrate 처리되었으므로 추가 API 호출 없이 initialData가 사용됩니다 (staleTime 60초 내)
  const { data: botList, isLoading: isBotsLoading } = useQuery<BotListResponse>({
    queryKey: ['bots'],
    // 클라이언트 마운트 시 필요하다면 client API 호출 함수가 들어가야 하지만, 
    // RSC Hydration의 힘으로 이 함수는 캐시가 만료되기 전까지 실행되지 않음
    queryFn: async () => {
      // 클라이언트 사이드에서 재요청이 필요한 경우를 대비해 fetch 로직 작성
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1'}/bots`);
      return res.json();
    }
  });

  const bots = botList?.bots || [];

  // 카테고리 목록 API 호출
  const { data: categories = [], isLoading: isFetchingCategories } = useQuery<string[]>({
    queryKey: ['bot-categories'],
    queryFn: async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1'}/bots/categories`);
        if (!res.ok) return [];
        return await res.json();
      } catch (error) {
        console.error('Failed to fetch categories:', error);
        return [];
      }
    }
  });

  // 통합 필터링 로직 (카테고리 + 검색어)
  const filteredBots = bots.filter(bot => {
    // 1. 카테고리 필터
    const matchesCategory = activeCategory === "전체" || (bot.tags || []).includes(activeCategory);
    
    // 2. 검색어 필터 (이름, 설명, 태그 통합 검색)
    const lowerQuery = searchQuery.toLowerCase().trim();
    const matchesSearch = !lowerQuery || 
      bot.name.toLowerCase().includes(lowerQuery) ||
      (bot.description || "").toLowerCase().includes(lowerQuery) ||
      (bot.tags || []).some((tag: string) => tag.toLowerCase().includes(lowerQuery));

    return matchesCategory && matchesSearch;
  });

  return (
    <div className="min-h-screen flex flex-col bg-background selection:bg-amber-500/30">
      <Header />
      
      <main className="flex-1 flex flex-col items-center w-full relative">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-[1000px] h-[500px] bg-amber-500/5 blur-[120px] rounded-full pointer-events-none" />
        
        <div className="w-full max-w-screen-2xl mx-auto flex flex-col items-center relative z-10">
          <HeroSection />
          <SearchAndFilter 
            activeCategory={activeCategory} 
            categories={categories}
            isLoading={isFetchingCategories}
            searchValue={searchQuery}
            onCategoryChange={setActiveCategory} 
            onSearchChange={setSearchQuery}
          />
          <div className="w-full max-w-7xl mx-auto">
            <BotGrid bots={filteredBots} title={activeCategory === "전체" ? "인기 챗봇" : `${activeCategory} 챗봇`} />
          </div>
        </div>
      </main>
    </div>
  );
}
