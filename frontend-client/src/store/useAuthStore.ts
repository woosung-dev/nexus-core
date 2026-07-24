"use client";

// 하나로 세션 상태를 읽어오는 훅 — /api/auth/session 이 httpOnly 쿠키를 대신 읽어준다

import { useCallback, useEffect, useState } from "react";
import { clearSessionTokenCache } from "@/lib/api";
import type { SessionUser } from "@/lib/session";

type AuthUser = {
  email: string | undefined;
  user_metadata: {
    name: string | undefined;
    avatar_url: string | undefined;
  };
};

export function useAuthStore() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/auth/session", { cache: "no-store" });
      if (!res.ok) {
        setUser(null);
        return;
      }
      const data = (await res.json()) as { user: SessionUser | null };
      // 하나로는 이름·프로필을 반환하지 않으므로(규격서 8장) 아이디를 표시 이름으로 쓴다.
      setUser(
        data.user
          ? {
              email: data.user.email,
              user_metadata: { name: data.user.userid, avatar_url: undefined },
            }
          : null,
      );
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // 로그아웃 후에는 전체 새로고침으로 이동한다. router.push+refresh(소프트
  // 네비게이션)는 react-query 캐시·진행 중 요청을 초기화하지 못해, 쿠키가
  // 지워진 뒤에도 컴포넌트가 인증 API를 재호출해 에러가 난다. 세션 정리는
  // 로그아웃 요청 성공 여부와 무관하게 항상 수행한다.
  const signOut = useCallback(async (redirectTo: string = "/login") => {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      clearSessionTokenCache();
      window.location.href = redirectTo;
    }
  }, []);

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    initialize: load,
    signOut,
  };
}
