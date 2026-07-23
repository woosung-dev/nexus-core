/**
 * Axios API 클라이언트.
 * 하나로 세션 JWT를 자동으로 Authorization 헤더에 첨부합니다.
 *
 * 토큰은 httpOnly 쿠키에 있으므로 브라우저 JS가 직접 읽지 못한다. 대신 같은 오리진의
 * /api/auth/session 이 쿠키를 읽어 토큰을 내려준다.
 *
 * 401 응답을 받으면 캐시를 무시하고 세션을 1회 다시 읽어 재시도하고, 그래도 실패할 때만
 * /login 으로 redirect 한다. (캐시된 토큰 만료로 가끔 401 나는 정상 상황에서 즉시 강제
 * 로그아웃되는 문제를 막기 위함.)
 */

import axios, { AxiosRequestConfig } from "axios";

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

// 세션 토큰 메모리 캐시 — 매 요청마다 /api/auth/session 을 때리지 않도록 짧게 들고 있는다.
let cachedToken: string | null = null;
let cachedAt = 0;
const TOKEN_CACHE_MS = 30_000;

export function clearSessionTokenCache() {
  cachedToken = null;
  cachedAt = 0;
}

export async function getSessionToken(force = false): Promise<string | null> {
  if (!force && cachedToken && Date.now() - cachedAt < TOKEN_CACHE_MS) {
    return cachedToken;
  }
  try {
    const res = await fetch("/api/auth/session", { cache: "no-store" });
    if (!res.ok) {
      clearSessionTokenCache();
      return null;
    }
    const data = (await res.json()) as { token: string | null };
    cachedToken = data.token;
    cachedAt = Date.now();
    return cachedToken;
  } catch {
    return null;
  }
}

// Request Interceptor: 평상시 cached 토큰 첨부
api.interceptors.request.use(
  async (config) => {
    if (typeof window === "undefined") return config;
    const token = await getSessionToken();
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
      !config?._retried
    ) {
      config._retried = true;
      try {
        const token = await getSessionToken(true);
        if (token) {
          if (!config.headers) config.headers = {};
          (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
          return api(config);
        }
      } catch (e) {
        console.warn("세션 토큰 재조회 실패", e);
      }
      // 진짜 인증 실패 → /login
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export default api;
