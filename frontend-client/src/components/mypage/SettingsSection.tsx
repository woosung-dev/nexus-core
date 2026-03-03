import { Lock, Bell, Shield, ChevronRight } from "lucide-react";
import Link from "next/link";

export function SettingsSection() {
  const settingsItems = [
    { label: "비밀번호 변경", icon: <Lock className="w-5 h-5 text-zinc-400 group-hover:text-amber-500 transition-colors" />, href: "/mypage/password" },
    { label: "알림 설정", icon: <Bell className="w-5 h-5 text-zinc-400 group-hover:text-amber-500 transition-colors" />, href: "/mypage/notifications" },
    { label: "개인정보 보호", icon: <Shield className="w-5 h-5 text-zinc-400 group-hover:text-amber-500 transition-colors" />, href: "/mypage/privacy" },
  ];

  return (
    <section className="bg-white/90 border border-amber-100 rounded-xl p-8 backdrop-blur-xl shadow-sm">
      <h2 className="text-xl font-bold text-zinc-900 mb-6">설정</h2>
      
      <div className="flex flex-col gap-4">
        {settingsItems.map((item, i) => (
          <Link 
            key={i} 
            href={item.href}
            className="group flex items-center justify-between p-4 rounded-xl bg-zinc-50/80 hover:bg-white transition-all border border-transparent hover:border-amber-200 hover:shadow-sm shadow-zinc-100 w-full"
          >
            <div className="flex items-center gap-4">
              {item.icon}
              <span className="text-sm font-medium text-zinc-700 group-hover:text-zinc-900 transition-colors">{item.label}</span>
            </div>
            <ChevronRight className="w-4 h-4 text-zinc-400 group-hover:text-amber-500 transition-colors" />
          </Link>
        ))}
      </div>
    </section>
  );
}
