"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useState } from "react"

/**
 * React Query 전역 Provider.
 * 서버 컴포넌트인 root layout에서 직접 사용할 수 없으므로
 * "use client" 경계로 분리.
 */
export function ReactQueryProvider({
  children,
}: {
  children: React.ReactNode
}) {
  // 컴포넌트 내부에서 생성해야 요청 간 캐시가 공유되지 않음
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 창 포커스 시 자동 re-fetch (개발 중 비활성화 권장)
            refetchOnWindowFocus: false,
            // 실패 시 1회 재시도
            retry: 1,
            // 5분간 캐시 유지
            staleTime: 5 * 60 * 1000,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}
