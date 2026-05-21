/**
 * Axios API 클라이언트.
 * Clerk JWT를 자동으로 Authorization 헤더에 첨부합니다.
 *
 * 401 응답을 받으면 skipCache 옵션으로 fresh 토큰을 1회 minting 해 자동 재시도하고,
 * 그래도 실패할 때만 /login 으로 redirect 한다. (이전엔 캐시된 토큰 만료로 가끔 401 나는
 * 정상 상황에서도 즉시 강제 로그아웃되는 문제 있었음.)
 */

import axios, { AxiosRequestConfig } from "axios";
import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";

// 브라우저/서버 양쪽에서 같은 절대 URL 사용 — Next dev rewrite 프록시(30초 소켓 hang up)
// 우회. RAG 그라운딩 호출이 30초를 넘어가는 경우 프록시가 ECONNRESET 으로 끊어 500 으로 보였음.
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export { API_BASE_URL };

// React hook 외부의 interceptor 에서 사용할 module-level token getter.
// cached — 평상시 (Clerk SDK 의 ~50초 캐시 활용, 빠름)
// fresh  — 401 재시도용 (skipCache: true 로 강제 minting)
let clerkGetTokenCached: (() => Promise<string | null>) | null = null;
let clerkGetTokenFresh: (() => Promise<string | null>) | null = null;

export function setClerkTokenGetters(
  cached: () => Promise<string | null>,
  fresh: () => Promise<string | null>,
) {
  clerkGetTokenCached = cached;
  clerkGetTokenFresh = fresh;
}

// Request Interceptor: 평상시 cached 토큰 첨부
api.interceptors.request.use(
  async (config) => {
    if (typeof window === "undefined") return config;
    const token = await clerkGetTokenCached?.();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response Interceptor: 401 → fresh 토큰으로 1회 재시도. 그래도 401 이면 /login.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config as AxiosRequestConfig & { _retried?: boolean };
    if (
      error.response?.status === 401 &&
      typeof window !== "undefined" &&
      !config?._retried &&
      clerkGetTokenFresh
    ) {
      config._retried = true;
      try {
        const token = await clerkGetTokenFresh();
        if (token) {
          if (!config.headers) config.headers = {};
          (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
          return api(config);
        }
      } catch (e) {
        console.warn("fresh token mint failed", e);
      }
      // 진짜 인증 실패 → /login
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export default api;

/**
 * ClerkTokenProvider: Clerk getToken을 api.ts의 모듈 레벨 getter에 등록합니다.
 * Providers 컴포넌트에 추가하세요.
 */
export function ClerkTokenProvider() {
  const { getToken } = useAuth();

  useEffect(() => {
    setClerkTokenGetters(
      () => getToken({ template: "nexus-backend" }),
      () => getToken({ template: "nexus-backend", skipCache: true }),
    );
  }, [getToken]);

  return null;
}
