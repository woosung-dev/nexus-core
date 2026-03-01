"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { MessageSquare, User } from "lucide-react";
import { useAuthStore } from "@/store/useAuthStore";
import { UserMenu } from "./UserMenu";

export default function Header() {
  const pathname = usePathname();
  const { isAuthenticated, isLoading, initialize } = useAuthStore();

  // 로그인, 회원가입 페이지에서는 헤더를 숨김
  const isAuthPage = pathname === "/login" || pathname === "/signup";

  // 컴포넌트 마운트 시 인증 상태 초기화
  useEffect(() => {
    initialize();
  }, [initialize]);

  if (isAuthPage) return null;

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
      <div className="container flex h-16 max-w-screen-2xl items-center px-4 md:px-8 mx-auto">
        <div className="flex flex-1 items-center justify-between">
          {/* Logo & Brand */}
          <Link href="/" className="group flex items-center space-x-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/20 group-hover:border-amber-500/50 transition-all">
              <span className="font-bold text-amber-500">N</span>
            </div>
            <span className="font-bold inline-block text-lg tracking-tight shrink-0 group-hover:text-amber-500 transition-colors">
              Nexus Core
            </span>
          </Link>

          {/* Navigation & Actions */}
          <nav className="flex items-center space-x-2 md:space-x-4 shrink-0">
            {!isLoading && isAuthenticated ? (
              <div className="flex items-center gap-3">
                {/* 인증된 사용자 */}
                <Button
                  variant="ghost"
                  size="sm"
                  asChild
                  className="text-muted-foreground hover:text-foreground hidden sm:inline-flex"
                >
                  <Link href="/chat">
                    <MessageSquare className="h-4 w-4 mr-2" />
                    채팅하기
                  </Link>
                </Button>
                <UserMenu />
              </div>
            ) : !isLoading ? (
              <>
                {/* 비인증 사용자 */}
                {/* <Button
                  variant="ghost"
                  size="sm"
                  asChild
                  className="text-muted-foreground hover:text-foreground hidden sm:inline-flex"
                >
                  <Link href="/mypage">
                    <LayoutDashboard className="h-4 w-4 mr-2" />
                    마이페이지
                  </Link>
                </Button> */}

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
