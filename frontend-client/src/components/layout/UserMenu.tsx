"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { 
  User, 
  Shield, 
  LogOut, 
  LayoutDashboard, 
  MessageSquare,
  ChevronRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/useAuthStore";
import { useRouter } from "next/navigation";

export function UserMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { user, signOut } = useAuthStore();
  const router = useRouter();

  const displayName = user?.user_metadata?.name || user?.email?.split("@")[0] || "사용자";
  const email = user?.email || "";
  const avatarUrl = user?.user_metadata?.avatar_url;

  // 외부 클릭 시 닫기
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await signOut();
    router.push("/");
    router.refresh();
  };

  return (
    <div className="relative" ref={menuRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-center w-9 h-9 rounded-full bg-white border border-amber-200 overflow-hidden hover:ring-2 hover:ring-amber-500/50 hover:border-amber-300 transition-all focus:outline-none shadow-sm"
      >
        {avatarUrl ? (
          <Image 
            src={avatarUrl} 
            alt="Profile" 
            width={36} 
            height={36} 
            className="object-cover"
          />
        ) : (
          <User className="w-5 h-5 text-zinc-400" />
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-3 w-72 bg-white border border-amber-100 rounded-2xl shadow-xl shadow-amber-500/5 overflow-hidden z-50 animate-in fade-in zoom-in duration-200">
          {/* Menu Header */}
          <div className="p-5 border-b border-zinc-100 bg-amber-50/50">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full bg-amber-500 flex items-center justify-center shrink-0 overflow-hidden border-2 border-white shadow-sm">
                {avatarUrl ? (
                  <Image src={avatarUrl} alt="Avatar" width={48} height={48} className="object-cover" />
                ) : (
                  <User className="w-6 h-6 text-black" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1">
                  <span className="font-bold text-zinc-900 truncate">{displayName}</span>
                  <ChevronRight className="w-3 h-3 text-zinc-400" />
                </div>
                <p className="text-xs text-zinc-500 truncate">{email}</p>
              </div>
            </div>

            {/* Points / Badge Section */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-white border border-zinc-200 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                  <span className="text-xs font-medium text-zinc-700">Free Plan</span>
                </div>
              </div>
              <Button size="sm" variant="outline" className="h-7 px-3 text-[11px] bg-amber-50 text-amber-600 border border-amber-200 hover:bg-amber-100 font-bold transition-colors">
                PRO 업그레이드
              </Button>
            </div>
          </div>

          {/* Menu Items */}
          <div className="p-2">
            <Link 
              href="/mypage" 
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-3 p-3 rounded-xl hover:bg-zinc-50 transition-colors group"
            >
              <LayoutDashboard className="w-4 h-4 text-zinc-400 group-hover:text-amber-500" />
              <span className="text-sm font-medium text-zinc-700 group-hover:text-zinc-900">마이페이지</span>
            </Link>
            
            <Link 
              href="/chat" 
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-3 p-3 rounded-xl hover:bg-zinc-50 transition-colors group"
            >
              <MessageSquare className="w-4 h-4 text-zinc-400 group-hover:text-amber-500" />
              <span className="text-sm font-medium text-zinc-700 group-hover:text-zinc-900">채팅 목록</span>
            </Link>

            <button className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-zinc-50 transition-colors group text-left">
              <div className="flex items-center gap-3">
                <Shield className="w-4 h-4 text-zinc-400 group-hover:text-amber-500" />
                <span className="text-sm font-medium text-zinc-700 group-hover:text-zinc-900">세이프티</span>
              </div>
              <div className="w-7 h-4 bg-amber-400 rounded-full relative flex items-center px-0.5">
                <div className="w-3 h-3 bg-white rounded-full ml-auto shadow-sm" />
              </div>
            </button>

            <div className="h-px bg-zinc-100 my-2 mx-2" />

            <button 
              onClick={handleLogout}
              className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-red-50 transition-colors group text-left"
            >
              <LogOut className="w-4 h-4 text-zinc-400 group-hover:text-red-500 transition-colors" />
              <span className="text-sm font-medium text-zinc-700 group-hover:text-red-600 transition-colors">로그아웃</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
