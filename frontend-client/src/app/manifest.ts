// PWA-lite Web App Manifest. /manifest.webmanifest 로 자동 노출.
// 모바일 사파리/크롬 "홈 화면에 추가" 시 아이콘·테마 색을 nexus 브랜드로.
import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Nexus — AI 챗봇 포털",
    short_name: "Nexus",
    description: "다양한 AI 챗봇과 대화하며 궁금했던 부분을 해결해 보세요.",
    start_url: "/",
    display: "standalone",
    background_color: "#0b1220",
    theme_color: "#f59e0b",
    icons: [
      {
        src: "/nexus-logo.png",
        sizes: "any",
        type: "image/png",
      },
    ],
  };
}
