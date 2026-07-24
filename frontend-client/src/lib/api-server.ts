// Server Component 에서 백엔드 API 를 호출하는 유틸 — 세션 쿠키의 JWT 를 헤더로 넣는다

import { cookies } from "next/headers";
import { SESSION_COOKIE } from "@/lib/session";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1";

/**
 * Server Component 내부에서 백엔드 API를 호출하기 위한 유틸리티.
 * httpOnly 세션 쿠키에서 토큰을 꺼내 Authorization 헤더에 주입합니다.
 */
export async function serverFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE)?.value;

  const fullUrl = `${API_BASE}${path}`;
  console.log(`[serverFetch] Attempting to fetch: ${fullUrl}`);

  const res = await fetch(fullUrl, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
    next: { revalidate: 0, ...options?.next },
  });

  if (!res.ok) {
    console.warn(
      `[serverFetch] Failed: ${res.status} ${res.statusText} at ${path}. Returning null to prevent build failure.`
    );
    return null as T;
  }

  const data = await res.json();
  return data;
}
