"use client";

import { MessageCircle, Bot, Clock } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

interface ChatSessionResponse {
  id: number;
  bot_id: number | null;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ChatSessionListResponse {
  sessions: ChatSessionResponse[];
  total: number;
}

export function ActivityStatsSection() {
  // SSR Hydration된 데이터를 바로 사용하며, 필요 시 클라이언트에서도 재요청 가능하도록 queryFn 추가
  const { data } = useQuery<ChatSessionListResponse>({
    queryKey: ["chats", { limit: 5 }],
    queryFn: async () => {
      const res = await api.get("/chats?limit=5");
      return res.data;
    },
  });

  const totalChats = data?.total || 0;
  
  // 현재 가져온 세션들로부터 고유한 챗봇 수 계산 (전체 데이터가 아닐 수 있음)
  const uniqueBots = new Set(
    data?.sessions
      ?.map(s => s.bot_id)
      .filter((id): id is number => id !== null)
  ).size;

  const stats = [
    { label: "총 대화", value: totalChats.toString(), icon: <MessageCircle className="w-5 h-5 text-amber-500" /> },
    { label: "사용한 챗봇", value: uniqueBots > 0 ? uniqueBots.toString() : "-", icon: <Bot className="w-5 h-5 text-amber-500" /> },
    { label: "총 사용 시간", value: "-", icon: <Clock className="w-5 h-5 text-amber-500" /> },
  ];

  return (
    <section className="bg-white/90 border border-amber-100 rounded-xl p-8 backdrop-blur-xl shadow-sm">
      <h2 className="text-xl font-bold text-zinc-900 mb-8">활동 통계</h2>
      
      <div className="grid grid-cols-3 gap-6">
        {stats.map((stat, i) => (
          <div key={i} className="flex flex-col items-center">
            <div className="w-16 h-16 rounded-full flex items-center justify-center bg-amber-500/10 mb-4 ring-1 ring-amber-500/20 shadow-sm shadow-amber-500/5">
              {stat.icon}
            </div>
            <p className="text-2xl font-bold text-zinc-900 mb-1">{stat.value}</p>
            <p className="text-sm text-zinc-500 text-center">{stat.label}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
