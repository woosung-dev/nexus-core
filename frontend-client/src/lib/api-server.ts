import { createClient } from '@/lib/supabase/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

/**
 * Server Component 내부에서 백엔드 API를 호출하기 위한 유틸리티.
 * Supabase 세션 토큰을 자동으로 추출하여 Authorization 헤더에 주입합니다.
 */
export async function serverFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const supabase = await createClient();
  const { data: { session } } = await supabase.auth.getSession();

  const fullUrl = `${API_BASE}${path}`;
  console.log(`[serverFetch] Attempting to fetch: ${fullUrl}`);

  const res = await fetch(fullUrl, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}),
      ...options?.headers,
    },
    // Next.js fetch cache 설정: 기본적으로 매 요청 시 최신 데이터(SSR)
    // 캐싱이 필요한 경우 호출 측에서 options.next.revalidate 등을 덮어씁니다.
    next: { revalidate: 0, ...options?.next },
  });

  if (!res.ok) {
    console.warn(`[serverFetch] Failed: ${res.status} ${res.statusText} at ${path}. Returning null to prevent build failure.`);
    return null as T;
  }
  
  const data = await res.json();
  return data;
}
