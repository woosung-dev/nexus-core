// 검색엔진 크롤링 정책. /robots.txt 로 자동 노출.
import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/"],
        // 사용자 사적 영역 + 인증 콜백 + API 전부 차단.
        disallow: [
          "/login",
          "/signup",
          "/mypage",
          "/chat",
          "/sso-callback",
          "/api",
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
