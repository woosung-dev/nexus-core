import fs from "node:fs/promises"
import path from "node:path"
import { NextResponse } from "next/server"

/**
 * 위키 산출물 파일을 그대로 읽어 준다 — 화면에 뜬 문장이 진짜 그 파일에서 왔는지
 * 관리자가 원본을 직접 열어 확인하기 위한 통로다.
 *
 * `exports/` 는 gitignore 라 정적 자원으로 서빙되지 않는다. 그래서 라우트가 필요하다.
 *
 * 임시 다리다 — 위키가 DB 에 적재되면(`_load.py`) 이 라우트는 없어진다.
 * 그때까지만 개발 환경에서 산다.
 */

// 이 접두어 밖은 절대 못 읽는다. 레포 전체가 열리면 안 된다.
const ALLOWED_PREFIX = "exports/wiki_2026-08/"
const ALLOWED_EXT = new Set([".md", ".json"])

export async function GET(req: Request) {
  if (process.env.NODE_ENV === "production") {
    return NextResponse.json({ error: "개발 환경에서만 열립니다." }, { status: 404 })
  }

  const rel = new URL(req.url).searchParams.get("path") ?? ""
  if (!rel.startsWith(ALLOWED_PREFIX) || !ALLOWED_EXT.has(path.extname(rel))) {
    return NextResponse.json({ error: "허용되지 않은 경로입니다." }, { status: 400 })
  }

  // frontend-admin/ 에서 실행되므로 레포 루트는 한 칸 위다.
  const root = path.resolve(process.cwd(), "..")
  const abs = path.resolve(root, rel)
  // `..` 로 빠져나가는 경로를 막는다 — 위 접두어 검사만으로는 부족하다.
  if (!abs.startsWith(path.join(root, ALLOWED_PREFIX))) {
    return NextResponse.json({ error: "허용되지 않은 경로입니다." }, { status: 400 })
  }

  try {
    const body = await fs.readFile(abs, "utf-8")
    return new NextResponse(body, {
      headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
    })
  } catch {
    return NextResponse.json({ error: `파일이 없습니다: ${rel}` }, { status: 404 })
  }
}
