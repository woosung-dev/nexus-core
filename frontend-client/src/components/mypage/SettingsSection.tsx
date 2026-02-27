import { Lock, Bell, Shield, ChevronRight } from "lucide-react";
import Link from "next/link";

export function SettingsSection() {
  const settingsItems = [
    { label: "비밀번호 변경", icon: <Lock className="w-5 h-5 text-zinc-400 group-hover:text-amber-500 transition-colors" />, href: "/mypage/password" },
    { label: "알림 설정", icon: <Bell className="w-5 h-5 text-zinc-400 group-hover:text-amber-500 transition-colors" />, href: "/mypage/notifications" },
    { label: "개인정보 보호", icon: <Shield className="w-5 h-5 text-zinc-400 group-hover:text-amber-500 transition-colors" />, href: "/mypage/privacy" },
  ];

  return (
    <section className="bg-zinc-950/80 border border-zinc-800 rounded-xl p-8 backdrop-blur-xl">
      <h2 className="text-xl font-bold text-white mb-6">설정</h2>
      
      <div className="flex flex-col gap-4">
        {settingsItems.map((item, i) => (
          <Link 
            key={i} 
            href={item.href}
            className="group flex items-center justify-between p-4 rounded-xl bg-zinc-900/50 hover:bg-zinc-800/80 transition-all border border-transparent hover:border-zinc-700 w-full"
          >
            <div className="flex items-center gap-4">
              {item.icon}
              <span className="text-sm font-medium text-white">{item.label}</span>
            </div>
            <ChevronRight className="w-4 h-4 text-zinc-500 group-hover:text-white transition-colors" />
          </Link>
        ))}
      </div>
    </section>
  );
}
