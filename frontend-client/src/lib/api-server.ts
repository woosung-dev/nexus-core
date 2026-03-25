import { auth } from "@clerk/nextjs/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1";

/**
 * Server Component 내부에서 백엔드 API를 호출하기 위한 유틸리티.
 * Clerk 세션 토큰을 자동으로 추출하여 Authorization 헤더에 주입합니다.
 */
export async function serverFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const { getToken } = await auth();
  const token = await getToken({ template: "nexus-backend" });

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
