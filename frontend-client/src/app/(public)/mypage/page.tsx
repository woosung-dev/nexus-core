import Header from "@/components/layout/Header";
import { ProfileSection } from "@/components/mypage/ProfileSection";
import { ActivityStatsSection } from "@/components/mypage/ActivityStatsSection";
import { SettingsSection } from "@/components/mypage/SettingsSection";
import { LogoutButton } from "@/components/mypage/LogoutButton";

export default function MyPage() {
  return (
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
  );
}
