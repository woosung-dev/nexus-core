/**
 * OAuth Callback 라우트 핸들러.
 * Supabase OAuth(Kakao, Google) 로그인 후 리다이렉트되는 엔드포인트입니다.
 * code 파라미터를 세션으로 교환하고 적절한 페이지로 리다이렉트합니다.
 */

import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  // OAuth 이후 리다이렉트 할 경로 (기본값: 메인 페이지)
  const next = searchParams.get("next") ?? "/";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  // 에러 발생 시 로그인 페이지로 리다이렉트 (에러 메시지 포함)
  return NextResponse.redirect(`${origin}/login?error=auth_callback_failed`);
}
