import type { NextConfig } from "next";

/**
 * 환경 변수(NEXT_PUBLIC_API_URL)에서 백엔드 호스트 정보를 추출합니다.
 * 예: http://localhost:8080/api/v1 -> hostname: localhost, port: 8080
 */
const getBackendHostInfo = () => {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1";
    const url = new URL(apiUrl);
    return {
      protocol: url.protocol.replace(":", "") as "http" | "https",
      hostname: url.hostname,
      port: url.port || (url.protocol === "https:" ? "" : "80"),
    };
  } catch {
    // 기본값 (로컬 개발 서버)
    return {
      protocol: "http" as const,
      hostname: "localhost",
      port: "8080",
    };
  }
};

const hostInfo = getBackendHostInfo();

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: hostInfo.protocol,
        hostname: hostInfo.hostname,
        port: hostInfo.port,
        pathname: "/static/uploads/**",
      },
      // 로컬 개발 시 호스트명(localhost 등) 외에 127.0.0.1로 직접 접근하는 경우도 허용합니다. (동적 포트 반영)
      {
        protocol: hostInfo.protocol,
        hostname: "127.0.0.1",
        port: hostInfo.port,
        pathname: "/static/uploads/**",
      },
      // 소셜 서비스(Google, GitHub 등) 프로필 이미지 허용
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "avatars.githubusercontent.com",
        pathname: "/**",
      },
      {
        protocol: "http",
        hostname: "k.kakaocdn.net",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "k.kakaocdn.net",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
