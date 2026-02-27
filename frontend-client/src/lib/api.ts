/**
 * Axios API 클라이언트.
 * Supabase 세션의 access_token을 자동으로 Authorization 헤더에 첨부합니다.
 */

import axios from "axios";
import { createClient } from "@/lib/supabase/client";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// Request Interceptor: Supabase JWT를 자동으로 Authorization 헤더에 추가
api.interceptors.request.use(
  async (config) => {
    // 서버 사이드에서는 Supabase 클라이언트를 생성하지 않음
    if (typeof window === "undefined") return config;

    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
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
