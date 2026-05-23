import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "lh3.googleusercontent.com" },
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
      // Clerk avatars
      { protocol: "https", hostname: "img.clerk.com" },
      // Cloudflare R2
      { protocol: "https", hostname: "*.r2.dev" },
      { protocol: "https", hostname: "*.r2.cloudflarestorage.com" },
    ],
  },
  async rewrites() {
    // rewrite 는 컨테이너 내부에서 평가/실행되므로 도커 네트워크용 INTERNAL_API_URL 우선.
    // 미설정 시(호스트 직접 실행) NEXT_PUBLIC_API_URL → 마지막 localhost 폴백.
    const target =
      process.env.INTERNAL_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8080";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${target}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
