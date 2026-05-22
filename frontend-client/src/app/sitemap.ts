// 검색엔진용 sitemap. /sitemap.xml 로 자동 노출.
// 공개 페이지만 포함 — 사용자 사적 영역(채팅/마이페이지)/인증 페이지는 noindex 라 제외.
import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: `${SITE_URL}/`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1.0,
    },
  ];
}
