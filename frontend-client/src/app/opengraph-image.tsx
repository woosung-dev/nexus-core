// 카카오톡/Slack/iMessage 등 URL 공유 시 노출되는 1200x630 OG 카드.
// Next.js ImageResponse 로 동적 렌더 — 별도 PNG 파일 관리 없이 코드에서 디자인.
import { ImageResponse } from "next/og";
import { readFileSync } from "fs";
import path from "path";

export const runtime = "nodejs";
export const alt = "Nexus — AI 챗봇 포털";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  // public/nexus-logo.png 를 빌드 시점에 inline 으로 embed (런타임 외부 fetch 없음).
  const logoPath = path.join(process.cwd(), "public", "nexus-logo.png");
  const logoData = readFileSync(logoPath);
  const logoBase64 = `data:image/png;base64,${logoData.toString("base64")}`;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background:
            "radial-gradient(ellipse at center, #1f2937 0%, #0b1220 70%, #050810 100%)",
          padding: "80px",
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "48px",
          }}
        >
          {/* 로고: 새 nexus-logo.png (어두운 발광 N 디자인).
             * ImageResponse 안에서는 next/image 사용 불가하므로 plain img 가 정상. */}
          <img
            src={logoBase64}
            alt="Nexus"
            width={320}
            height={320}
            style={{ borderRadius: "40px" }}
          />

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              color: "#f8fafc",
            }}
          >
            <div
              style={{
                fontSize: 140,
                fontWeight: 800,
                lineHeight: 1,
                letterSpacing: "-0.04em",
                background:
                  "linear-gradient(135deg, #93c5fd 0%, #60a5fa 50%, #f59e0b 100%)",
                backgroundClip: "text",
                color: "transparent",
              }}
            >
              Nexus
            </div>
            <div
              style={{
                marginTop: 28,
                fontSize: 38,
                fontWeight: 500,
                color: "#cbd5e1",
                letterSpacing: "-0.01em",
              }}
            >
              AI 챗봇과 함께
            </div>
            <div
              style={{
                fontSize: 38,
                fontWeight: 500,
                color: "#cbd5e1",
                letterSpacing: "-0.01em",
              }}
            >
              고민을 해결해 보세요
            </div>
          </div>
        </div>

        {/* 하단 우측 사이트명 워터마크 */}
        <div
          style={{
            position: "absolute",
            bottom: 56,
            right: 80,
            fontSize: 28,
            color: "#64748b",
            fontWeight: 600,
            letterSpacing: "0.1em",
          }}
        >
          NEXUS · AI CHAT PORTAL
        </div>
      </div>
    ),
    { ...size }
  );
}
