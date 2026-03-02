import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      // Cloud Run 배포 주소 직접 지정 (와일드카드 활용)
      {
        protocol: "https",
        hostname: "nexus-core-58481128769.asia-northeast3.run.app",
        pathname: "/static/uploads/**",
      },
      // 로컬 개발 환경
      {
        protocol: "http",
        hostname: "127.0.0.1",
        port: "8080",
        pathname: "/static/uploads/**",
      },
      {
        protocol: "http",
        hostname: "localhost",
        port: "8080",
        pathname: "/static/uploads/**",
      },
      // 소셜 서비스 프로필 이미지
      { protocol: "https", hostname: "lh3.googleusercontent.com", pathname: "/**" },
      { protocol: "https", hostname: "avatars.githubusercontent.com", pathname: "/**" },
      { protocol: "http", hostname: "k.kakaocdn.net", pathname: "/**" },
      { protocol: "https", hostname: "k.kakaocdn.net", pathname: "/**" },
    ],
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1";
    // /api/v1을 안전하게 제거하여 베이스 URL 추출
    const backendBase = apiUrl.replace(/\/api\/v1\/?$/, "");

    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiUrl}/:path*`,
      },
      {
        source: "/static/uploads/:path*",
        destination: `${backendBase}/static/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
