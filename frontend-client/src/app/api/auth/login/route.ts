// 하나로 로그인 — 백엔드에서 세션 JWT 를 받아 httpOnly 쿠키로 심는다

import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1";

export async function POST(req: Request) {
  let body: { userid?: string; password?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "BAD_REQUEST" }, { status: 400 });
  }

  const userid = body.userid?.trim();
  const password = body.password;
  if (!userid || !password) {
    return NextResponse.json({ error: "BAD_REQUEST" }, { status: 400 });
  }

  // 비밀번호는 백엔드로 전달만 하고 이 계층에 남기지 않는다(규격서 8장).
  let upstream: Response;
  try {
    upstream = await fetch(`${API_BASE}/auth/hanaro/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userid, password }),
      cache: "no-store",
    });
  } catch (e) {
    console.error("[auth] 백엔드 로그인 호출 실패", e);
    return NextResponse.json({ error: "UPSTREAM_UNREACHABLE" }, { status: 502 });
  }

  const data = (await upstream.json().catch(() => null)) as
    | { access_token?: string; expires_in?: number; is_official?: boolean; error_code?: string; message?: string }
    | null;

  if (!upstream.ok || !data?.access_token) {
    // 백엔드의 상태코드와 에러코드를 그대로 전달한다. 뭉개면 원인을 오진한다.
    return NextResponse.json(
      { error: data?.error_code ?? "LOGIN_FAILED", message: data?.message },
      { status: upstream.status || 500 },
    );
  }

  const res = NextResponse.json({ ok: true, isOfficial: data.is_official === true });
  res.cookies.set(SESSION_COOKIE, data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: data.expires_in ?? 60 * 60 * 12,
  });
  return res;
}
