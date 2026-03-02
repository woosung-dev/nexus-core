import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "nexus-core-58481128769.asia-northeast3.run.app" },
      { protocol: "https", hostname: "lh3.googleusercontent.com" },
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
      { protocol: "https", hostname: "k.kakaocdn.net" },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1"}/:path*`,
      },
      {
        source: "/static/uploads/:path*",
        destination: `${(process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api/v1").replace("/api/v1", "")}/static/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
