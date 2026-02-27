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
  let supabaseResponse = NextResponse.next({
    request,
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          // Request 쿠키에도 설정하여, 이후 서버 컴포넌트에서 갱신된 값을 읽을 수 있도록 함
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({
            request,
          });
          // Response 쿠키에도 설정하여 브라우저에 전달
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  // 세션 갱신 (중요: getUser()는 서버측에서 토큰을 검증합니다)
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;

  // 보호된 라우트 접근 시 비인증 사용자를 로그인 페이지로 리다이렉트
  if (!user && PROTECTED_ROUTES.some((route) => pathname.startsWith(route))) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  // 이미 로그인된 사용자가 인증 페이지 접근 시 메인으로 리다이렉트
  if (user && (pathname === "/login" || pathname === "/signup")) {
    const url = request.nextUrl.clone();
    url.pathname = "/";
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    /*
     * 정적 파일과 이미지를 제외한 모든 경로에 대해 미들웨어를 실행합니다.
     * _next/static, _next/image, favicon.ico 등은 제외
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
