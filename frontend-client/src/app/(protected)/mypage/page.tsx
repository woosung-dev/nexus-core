import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { getQueryClient } from "@/lib/get-query-client";
import { serverFetch } from "@/lib/api-server";

import Header from "@/components/layout/Header";
import { ProfileSection } from "@/components/mypage/ProfileSection";
import { ActivityStatsSection } from "@/components/mypage/ActivityStatsSection";
import { SettingsSection } from "@/components/mypage/SettingsSection";
import { LogoutButton } from "@/components/mypage/LogoutButton";

export default async function MyPage() {
  const queryClient = getQueryClient();

  // 서버 환경에서 API 데이터 프리페치 (에러 처리는 생략, QueryClient 내부 캐싱됨)
  try {
    await Promise.all([
      queryClient.prefetchQuery({
        queryKey: ["me"],
        queryFn: () => serverFetch("/users/me"),
      }),
      queryClient.prefetchQuery({
        queryKey: ["chats", { limit: 5 }],
        queryFn: () => serverFetch("/chats?limit=5"), // limit 등 쿼리파람을 API가 미지원해도 무방함
      }),
    ]);
  } catch (error) {
    console.error("Failed to prefetch MyPage data:", error);
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <div className="min-h-screen flex flex-col bg-black selection:bg-amber-500/30 overflow-x-hidden">
        <Header />
        
        <main className="flex-1 flex flex-col items-center w-full px-4 sm:px-8 py-12">
          {/* Ambient Dark Background Effect */}
          <div className="fixed inset-0 bg-zinc-950/20 -z-10" />
          
          <div className="w-full max-w-4xl flex flex-col">
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">마이페이지</h1>
              <p className="text-zinc-400">계정 정보를 관리하세요</p>
            </div>

            <div className="flex flex-col gap-6">
              <ProfileSection />
              <ActivityStatsSection />
              <SettingsSection />
              <LogoutButton />
            </div>
          </div>
        </main>
      </div>
    </HydrationBoundary>
  );
}
