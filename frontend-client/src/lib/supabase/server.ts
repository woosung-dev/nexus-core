/**
 * 서버 환경용 Supabase 클라이언트.
 * RSC, Route Handler, Middleware에서 사용합니다.
 * 쿠키를 통한 세션 관리를 지원합니다.
 */

import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // Server Component에서 setAll이 호출될 수 있으나,
            // Middleware에서 세션 갱신이 처리되므로 무시해도 안전합니다.
          }
        },
      },
    }
  );
}
