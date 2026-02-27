"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import { HeroSection } from "@/components/landing/HeroSection";
import { SearchAndFilter } from "@/components/landing/SearchAndFilter";
import { BotGrid } from "@/components/landing/BotGrid";
import { BotData } from "@/components/landing/BotCard";

// Mock Data for Prototyping
const MOCK_BOTS: BotData[] = [
  {
    id: "1",
    name: "Nexus Core Assistant",
    creator: "Nexus Team",
    description: "넥서스 플랫폼의 공식 어시스턴트입니다. 플랫폼 사용법과 각종 기술 지원을 담당합니다.",
    category: "범용",
    tags: ["공식", "가이드", "도우미"],
    rating: 4.9,
    users: 12500,
    isOfficial: true,
  },
  {
    id: "2",
    name: "Python Code Master",
    creator: "TechLead",
    description: "파이썬 알고리즘 풀이, 최적화 팁, 코드 리뷰를 전문으로 하는 최고의 코딩 파트너입니다.",
    category: "코딩",
    tags: ["Python", "알고리즘", "리뷰"],
    rating: 4.8,
    users: 8200,
  },
  {
    id: "3",
    name: "창작의 요정",
    creator: "StoryTeller",
    description: "소설, 에세이, 블로그 포스팅 등 글쓰기 아이디어를 제공하고 문맥을 다듬어줍니다.",
    category: "창작",
    tags: ["글쓰기", "아이디어", "에세이"],
    rating: 4.7,
    users: 5300,
  },
  {
    id: "4",
    name: "법률 상담 봇",
    creator: "Lawyer_AI",
    description: "일상생활에서 겪는 가벼운 법률적 궁금증에 대한 판례와 기본 해석을 돕습니다.",
    category: "법률",
    tags: ["상담", "판례", "생활법률"],
    rating: 4.5,
    users: 3100,
  },
  {
    id: "5",
    name: "비즈니스 통번역가",
    creator: "GlobalBiz",
    description: "비즈니스 이메일, 계약서 등 포멀한 문서 번역과 문화권별 뉘앙스 검수를 지원합니다.",
    category: "비즈니스",
    tags: ["번역", "이메일", "영어"],
    rating: 4.9,
    users: 9800,
  },
  {
    id: "6",
    name: "건강 체크봇",
    creator: "HealthCoach",
    description: "간단한 증상 기반 건강 조언과 식단/운동 가이드를 제공합니다. (의료기기 아님)",
    category: "건강",
    tags: ["식단", "운동", "상담"],
    rating: 4.6,
    users: 4200,
  }
];

export default function LandingPage() {
  const [activeCategory, setActiveCategory] = useState("전체");

  // 현재 활성화된 카테고리에 맞게 봇 필터링
  const filteredBots = activeCategory === "전체" 
    ? MOCK_BOTS 
    : MOCK_BOTS.filter(bot => bot.category === activeCategory);

  return (
    <div className="min-h-screen flex flex-col bg-background selection:bg-amber-500/30">
      <Header />
      
      <main className="flex-1 flex flex-col items-center w-full relative">
        {/* Background Ambient Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-[1000px] h-[500px] bg-amber-500/5 blur-[120px] rounded-full pointer-events-none" />
        
        <div className="w-full max-w-screen-2xl mx-auto flex flex-col items-center relative z-10">
          <HeroSection />
          <SearchAndFilter 
            activeCategory={activeCategory} 
            onCategoryChange={setActiveCategory} 
          />
          <div className="w-full max-w-7xl mx-auto">
            <BotGrid bots={filteredBots} title={activeCategory === "전체" ? "인기 챗봇" : `${activeCategory} 챗봇`} />
          </div>
        </div>
      </main>
    </div>
  );
}
