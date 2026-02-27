/**
 * Zustand 기반 인증 상태 관리 스토어.
 * Supabase 세션과 동기화하여 전역적으로 사용자 인증 상태를 제공합니다.
 */

"use client";

import { create } from "zustand";
import { createClient } from "@/lib/supabase/client";
import type { User, Session } from "@supabase/supabase-js";

interface AuthState {
  // 상태
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  // 액션
  initialize: () => Promise<void>;
  signOut: () => Promise<void>;
  setSession: (session: Session | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  session: null,
  isLoading: true,
  isAuthenticated: false,

  /**
   * 앱 초기 로드 시 Supabase 세션을 확인하고 상태를 동기화합니다.
   * onAuthStateChange 리스너를 등록하여 실시간으로 세션 변경을 추적합니다.
   */
  initialize: async () => {
    const supabase = createClient();

    // 현재 세션 확인
    const {
      data: { session },
    } = await supabase.auth.getSession();

    set({
      user: session?.user ?? null,
      session,
      isLoading: false,
      isAuthenticated: !!session?.user,
    });

    // 세션 변경 리스너 등록 (로그인/로그아웃/토큰 갱신)
    supabase.auth.onAuthStateChange((_event, session) => {
      set({
        user: session?.user ?? null,
        session,
        isAuthenticated: !!session?.user,
      });
    });
  },

  /**
   * 로그아웃 처리. Supabase 세션을 삭제하고 상태를 초기화합니다.
   */
  signOut: async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    set({
      user: null,
      session: null,
      isAuthenticated: false,
    });
  },

  /**
   * 외부에서 세션을 직접 설정할 때 사용합니다.
   */
  setSession: (session) => {
    set({
      user: session?.user ?? null,
      session,
      isAuthenticated: !!session?.user,
    });
  },
}));
