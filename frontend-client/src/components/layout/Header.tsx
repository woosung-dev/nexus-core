"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { LayoutDashboard, User, LogOut } from "lucide-react";
import { useAuthStore } from "@/store/useAuthStore";

export default function Header() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, initialize, signOut } =
    useAuthStore();

  // 컴포넌트 마운트 시 인증 상태 초기화
  useEffect(() => {
    initialize();
  }, [initialize]);

  // 로그아웃 처리
  const handleSignOut = async () => {
    await signOut();
    router.push("/");
    router.refresh();
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 max-w-screen-2xl items-center px-4 md:px-8 mx-auto">
        <div className="flex flex-1 items-center justify-between">
          {/* Logo & Brand */}
          <Link href="/" className="flex items-center space-x-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <span className="font-bold text-primary">N</span>
            </div>
            <span className="font-bold inline-block text-lg shrink-0">
              AI Chat Hub
            </span>
          </Link>

          {/* Navigation & Actions */}
          <nav className="flex items-center space-x-2 md:space-x-4 shrink-0">
            {!isLoading && isAuthenticated ? (
              <>
                {/* 인증된 사용자 */}
                <Button
                  variant="ghost"
                  size="sm"
                  asChild
                  className="text-muted-foreground hover:text-foreground hidden sm:inline-flex"
                >
                  <Link href="/mypage">
                    <LayoutDashboard className="h-4 w-4 mr-2" />
                    마이페이지
                  </Link>
                </Button>

                {/* Mobile Mypage Icon */}
                <Button
                  variant="ghost"
                  size="icon"
                  asChild
                  className="text-muted-foreground hover:text-foreground sm:hidden"
                >
                  <Link href="/mypage" aria-label="마이페이지">
                    <User className="h-5 w-5" />
                  </Link>
                </Button>

                {/* 프로필 + 로그아웃 */}
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground hidden md:inline truncate max-w-[120px]">
                    {user?.user_metadata?.name ||
                      user?.email?.split("@")[0] ||
                      "사용자"}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleSignOut}
                    className="text-muted-foreground hover:text-red-400 transition-colors"
                  >
                    <LogOut className="h-4 w-4 mr-1" />
                    <span className="hidden sm:inline">로그아웃</span>
                  </Button>
                </div>
              </>
            ) : !isLoading ? (
              <>
                {/* 비인증 사용자 */}
                <Button
                  variant="ghost"
                  size="sm"
                  asChild
                  className="text-muted-foreground hover:text-foreground hidden sm:inline-flex"
                >
                  <Link href="/mypage">
                    <LayoutDashboard className="h-4 w-4 mr-2" />
                    마이페이지
                  </Link>
                </Button>

                <Button
                  variant="ghost"
                  size="icon"
                  asChild
                  className="text-muted-foreground hover:text-foreground sm:hidden"
                >
                  <Link href="/mypage" aria-label="마이페이지">
                    <User className="h-5 w-5" />
                  </Link>
                </Button>

                <Button
                  size="sm"
                  asChild
                  className="font-semibold bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <Link href="/login">로그인</Link>
                </Button>
              </>
            ) : null}
          </nav>
        </div>
      </div>
    </header>
  );
}
