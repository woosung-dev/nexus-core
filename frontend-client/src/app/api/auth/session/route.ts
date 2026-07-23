// 현재 세션의 토큰과 사용자 정보를 돌려준다 — api.ts 의 토큰 getter 와 useAuthStore 가 쓴다

import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, type SessionUser } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * 세션 JWT payload 에서 화면 표시용 정보만 꺼낸다.
 *
 * 서명은 검증하지 않는다 — 백엔드가 매 API 요청마다 검증하므로 여기서 다시 할 이유가 없다.
 * 따라서 이 값으로 권한을 판단하면 안 된다.
 */
function readSessionUser(token: string): SessionUser | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const claims = JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
    if (!claims?.sub) return null;
    // 만료된 토큰은 없는 것으로 취급한다(쿠키 maxAge 와 어긋나는 경우 대비).
    if (typeof claims.exp === "number" && claims.exp * 1000 < Date.now()) return null;
    return {
      userid: String(claims.sub).replace(/^hanaro:/, ""),
      // 하나로는 이메일을 주지 않는다(규격서 8장). 없으면 없는 채로 둔다.
      email: typeof claims.email === "string" ? claims.email : undefined,
      isOfficial: claims.is_official === true,
    };
  } catch {
    return null;
  }
}

export async function GET(req: NextRequest) {
  const token = req.cookies.get(SESSION_COOKIE)?.value;
  const user = token ? readSessionUser(token) : null;

  // 비로그인은 오류가 아니라 정상 상태다. 401 로 내리면 공개 페이지마다 콘솔에
  // 빨간 에러가 쌓여 진짜 인증 실패와 구분되지 않는다.
  if (!token || !user) {
    return NextResponse.json({ token: null, user: null });
  }
  return NextResponse.json({ token, user });
}
