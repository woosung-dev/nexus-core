// 하나로 SSO 로그인 라우트 — 서버측 자격검증 + Clerk sign-in token(ticket) 발급
import { NextResponse } from "next/server";
import { clerkClient } from "@clerk/nextjs/server";
import { checkOfficial, findOrCreateHanaroUser } from "@/lib/hanaro";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const STATUS_BY_REASON: Record<string, number> = {
  invalid_credentials: 401,
  rate_limited: 429,
  server_config: 500,
  upstream_error: 502,
  bad_request: 400,
};

export async function POST(req: Request) {
  let body: { userid?: string; password?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "bad_request" }, { status: 400 });
  }
  const userid = body.userid?.trim();
  const password = body.password;
  if (!userid || !password) {
    return NextResponse.json({ error: "bad_request" }, { status: 400 });
  }

  const check = await checkOfficial(userid, password);
  if (!check.ok) {
    return NextResponse.json({ error: check.reason }, { status: STATUS_BY_REASON[check.reason] ?? 500 });
  }

  try {
    const userId = await findOrCreateHanaroUser(userid, check.isOfficial);
    const client = await clerkClient();
    const token = await client.signInTokens.createSignInToken({ userId, expiresInSeconds: 300 });
    return NextResponse.json({ ticket: token.token, isOfficial: check.isOfficial });
  } catch (e) {
    // 비밀번호/키는 로깅하지 않는다. 에러 객체만 기록.
    console.error("[hanaro] sign-in token 발급 실패", e);
    return NextResponse.json({ error: "server_error" }, { status: 500 });
  }
}
