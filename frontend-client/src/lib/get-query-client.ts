import { QueryClient } from '@tanstack/react-query';

// 서버 요청마다 새 인스턴스 생성 (요청 간 데이터 공유 방지)
export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 60초 — 서버 prefetch 데이터 즉시 재요청 방지
      },
    },
  });
}

// 클라이언트는 싱글톤 유지
let browserQueryClient: QueryClient | undefined = undefined;

export function getQueryClient() {
  if (typeof window === 'undefined') return makeQueryClient();
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}
