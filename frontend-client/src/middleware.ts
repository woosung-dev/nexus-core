/**
 * Next.js Middleware.
 * 모든 요청에서 Supabase 세션을 갱신(Refresh)하고,
 * 보호된 라우트에 비인증 사용자의 접근을 차단합니다.
 */

import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

// 인증이 필요한 라우트 목록
const PROTECTED_ROUTES = ["/mypage", "/chat"];

export async function middleware(request: NextRequest) {
  // 1. 초기 응답 객체 생성
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  // 환경 변수 체크 (Vercel 배포 시 누락 방지)
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    return response;
  }

  // 2. Supabase 클라이언트 초기화
  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value, options }) =>
          request.cookies.set(name, value)
        );
        response = NextResponse.next({
          request,
        });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options)
        );
      },
    },
  });

  // 3. 세션 갱신 및 유저 정보 확인
  // getUser()는 토큰을 서버측에서 직접 검증하므로 안전합니다.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;

  // 4. 보호된 라우트 접근 제어
  if (!user && PROTECTED_ROUTES.some((route) => pathname.startsWith(route))) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  // 5. 로그인 상태에서 인증 페이지 접근 시 리다이렉트
  if (user && (pathname === "/login" || pathname === "/signup")) {
    const url = request.nextUrl.clone();
    url.pathname = "/";
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * 정적 파일과 이미지를 제외한 모든 경로에 대해 미들웨어를 실행합니다.
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
