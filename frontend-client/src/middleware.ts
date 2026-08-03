// 세션 쿠키 유무로 보호 경로 접근을 막는다 (서명 검증은 백엔드가 매 요청 수행)

import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

const PROTECTED_PATHS = [/^\/chat(\/.*)?$/, /^\/mypage(\/.*)?$/];
const PROTOTYPE_BYPASS_HEADER = "x-nexus-clarification-prototype";

export default function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const requestHeaders = new Headers(req.headers);
  // 외부 요청이 이 헤더를 위조해도 서버 레이아웃까지 전달되지 않도록 항상 제거한다.
  requestHeaders.delete(PROTOTYPE_BYPASS_HEADER);
  const next = () => NextResponse.next({ request: { headers: requestHeaders } });

  if (!PROTECTED_PATHS.some((re) => re.test(pathname))) {
    return next();
  }

  const isPrototypeTestRoute =
    process.env.NEXT_PUBLIC_CLARIFICATION_PROTOTYPE_BYPASS_AUTH === "true" &&
    /^\/chat\/new\/\d+$/.test(pathname) &&
    req.nextUrl.searchParams.get("clarify-prototype") === "1";
  if (isPrototypeTestRoute) {
    requestHeaders.set(PROTOTYPE_BYPASS_HEADER, "1");
    return next();
  }

  if (req.cookies.get(SESSION_COOKIE)?.value) {
    return next();
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
