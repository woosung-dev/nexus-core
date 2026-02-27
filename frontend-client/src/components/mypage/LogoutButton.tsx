import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";

export function LogoutButton() {
  return (
    <Button 
      variant="outline"
      className="w-full h-14 bg-red-500/5 hover:bg-red-500/10 border-red-500/20 hover:border-red-500/40 text-red-500 hover:text-red-400 transition-all font-medium text-base rounded-xl"
    >
      <LogOut className="w-4 h-4 mr-2" />
      로그아웃
    </Button>
  );
}
