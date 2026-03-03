"use client";

import { Pen, User, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import Image from "next/image";
import api from "@/lib/api";

interface UserProfile {
  id: number;
  email: string;
  provider: string | null;
  plan_type: string;
  avatar_url: string | null;
  created_at: string;
}

export function ProfileSection() {
  const { data: user, isLoading } = useQuery<UserProfile>({
    queryKey: ["me"],
    queryFn: async () => {
      const res = await api.get("/users/me");
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <section className="bg-white/90 border border-amber-100 shadow-sm rounded-xl p-8 relative overflow-hidden backdrop-blur-xl flex items-center justify-center min-h-[300px]">
        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
      </section>
    );
  }

  // fallback for safety 
  if (!user) {
    return null; 
  }

  // fallback names
  const displayName = user.email.split('@')[0];

  return (
    <section className="bg-white/90 border border-amber-100 shadow-sm rounded-xl p-8 relative overflow-hidden backdrop-blur-xl">
      {/* Background Subtle Glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/5 rounded-full blur-[80px] pointer-events-none" />

      <div className="flex items-center justify-between mb-8 z-10 relative">
        <h2 className="text-xl font-bold text-zinc-900">프로필 정보</h2>
        <Button variant="outline" size="sm" className="bg-white border-zinc-200 text-zinc-700 hover:bg-zinc-50 hover:text-zinc-900 transition-colors h-9 px-4 shadow-sm">
          <Pen className="w-4 h-4 mr-2 text-zinc-500" />
          수정
        </Button>
      </div>

      <div className="flex items-center gap-6 mb-10 z-10 relative">
        <div className="w-24 h-24 rounded-full bg-linear-to-br from-amber-500 to-amber-600 flex items-center justify-center shrink-0 shadow-[0_0_20px_rgba(245,158,11,0.2)] overflow-hidden relative">
          {user.avatar_url ? (
            <Image 
              src={user.avatar_url} 
              alt="Avatar" 
              fill
              className="object-cover" 
            />
          ) : (
            <User className="w-10 h-10 text-black/80" />
          )}
        </div>
        <div className="flex flex-col">
          <h3 className="text-2xl font-bold text-zinc-900 mb-1">{displayName}</h3>
          <p className="text-sm text-zinc-500">{user.email}</p>
        </div>
      </div>

      <div className="space-y-6 z-10 relative">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-zinc-500">플랜</label>
          <p className="text-base text-zinc-900 capitalize">{user.plan_type.toLowerCase()}</p>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-zinc-500">연동 계정</label>
          <p className="text-base text-zinc-900 capitalize">{user.provider || "Standard"}</p>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-zinc-500">가입일</label>
          <p className="text-base text-zinc-900">
            {(() => {
              const date = new Date(user.created_at);
              const year = date.getFullYear();
              const month = String(date.getMonth() + 1).padStart(2, '0');
              const day = String(date.getDate()).padStart(2, '0');
              return `${year}. ${month}. ${day}.`;
            })()}
          </p>
        </div>
      </div>
    </section>
  );
}
