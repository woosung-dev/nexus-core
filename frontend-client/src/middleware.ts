// 세션 쿠키 유무로 보호 경로 접근을 막는다 (서명 검증은 백엔드가 매 요청 수행)

import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

const PROTECTED_PATHS = [/^\/chat(\/.*)?$/, /^\/mypage(\/.*)?$/];

export default function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (!PROTECTED_PATHS.some((re) => re.test(pathname))) {
    return NextResponse.next();
  }

  if (req.cookies.get(SESSION_COOKIE)?.value) {
    return NextResponse.next();
  }

  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = `?redirect_url=${encodeURIComponent(pathname)}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: [
    // Skip Next.js internals and all static files
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
