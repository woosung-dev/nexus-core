"use client";

import { useState } from "react";
import { LogOut, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";

export function LogoutButton() {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const supabase = createClient();

  const handleLogout = async () => {
    setIsLoading(true);
    try {
      await supabase.auth.signOut();
      router.push("/login");
      router.refresh();
    } catch (error) {
      console.error("Logout failed:", error);
    } finally {
      setIsLoading(false);
    }
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
