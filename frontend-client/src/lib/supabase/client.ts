/**
 * 브라우저 환경용 Supabase 클라이언트.
 * 클라이언트 컴포넌트("use client")에서 사용합니다.
 */

import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
