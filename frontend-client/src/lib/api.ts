/**
 * Axios API 클라이언트.
 * Clerk JWT를 자동으로 Authorization 헤더에 첨부합니다.
 */

import axios from "axios";
import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";

const api = axios.create({
  baseURL:
    typeof window !== "undefined"
      ? "/api/v1"
      : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// 모듈 레벨 token getter — React hook 외부의 interceptor에서 사용
let clerkGetToken: (() => Promise<string | null>) | null = null;

export function setClerkTokenGetter(fn: () => Promise<string | null>) {
  clerkGetToken = fn;
}

// Request Interceptor: Clerk JWT를 자동으로 Authorization 헤더에 추가
api.interceptors.request.use(
  async (config) => {
    if (typeof window === "undefined") return config;

    const token = await clerkGetToken?.();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: 401 에러 시 로그인 페이지로 리다이렉트
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;

/**
 * ClerkTokenProvider: Clerk getToken을 api.ts의 모듈 레벨 getter에 등록합니다.
 * Providers 컴포넌트에 추가하세요.
 */
export function ClerkTokenProvider() {
  const { getToken } = useAuth();

  useEffect(() => {
    setClerkTokenGetter(() => getToken({ template: "nexus-backend" }));
  }, [getToken]);

  return null;
}
