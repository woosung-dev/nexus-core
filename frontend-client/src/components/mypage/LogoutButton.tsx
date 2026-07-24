"use client";

import { useState } from "react";
import { LogOut, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/useAuthStore";

export function LogoutButton() {
  const [isLoading, setIsLoading] = useState(false);
  const { signOut } = useAuthStore();

  const handleLogout = async () => {
    setIsLoading(true);
    // signOut 이 세션 정리 후 /login 으로 전체 새로고침한다(로딩 상태 유지한 채 이동).
    await signOut("/login");
  };

  return (
    <Button 
      variant="outline"
      onClick={handleLogout}
      disabled={isLoading}
      className="w-full h-14 bg-red-500/5 hover:bg-red-500/10 border-red-500/20 hover:border-red-500/40 text-red-500 hover:text-red-400 transition-all font-medium text-base rounded-xl"
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
      ) : (
        <LogOut className="w-4 h-4 mr-2" />
      )}
      로그아웃
    </Button>
  );
}
