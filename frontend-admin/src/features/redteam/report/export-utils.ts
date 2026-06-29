// 보고 데이터 내보내기 유틸 — CSV 다운로드, 차트 SVG→PNG 래스터화 (의존성 없음).

// 배열(객체) → CSV 문자열. 헤더는 columns 순서를 따른다.
export function toCsv(
  rows: Record<string, unknown>[],
  columns: { key: string; label: string }[]
): string {
  const escape = (v: unknown) => {
    const s = v == null ? "" : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const head = columns.map((c) => escape(c.label)).join(",")
  const body = rows.map((r) => columns.map((c) => escape(r[c.key])).join(",")).join("\n")
  return `${head}\n${body}`
}

export function downloadCsv(
  filename: string,
  rows: Record<string, unknown>[],
  columns: { key: string; label: string }[]
) {
  // BOM 추가 — 엑셀에서 한글 깨짐 방지
  const blob = new Blob(["﻿" + toCsv(rows, columns)], {
    type: "text/csv;charset=utf-8",
  })
  triggerDownload(URL.createObjectURL(blob), filename)
}

// recharts가 그린 <svg>를 PNG로 저장. 데이터 색은 hex라 그대로, 축 텍스트(CSS 변수)는 기본색으로 폴백.
export function downloadSvgAsPng(svg: SVGSVGElement, filename: string, scale = 2) {
  const rect = svg.getBoundingClientRect()
  const width = Math.max(1, Math.round(rect.width))
  const height = Math.max(1, Math.round(rect.height))

  const clone = svg.cloneNode(true) as SVGSVGElement
  clone.setAttribute("width", String(width))
  clone.setAttribute("height", String(height))
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg")

  const data = new XMLSerializer().serializeToString(clone)
  const svgUrl = URL.createObjectURL(
    new Blob([data], { type: "image/svg+xml;charset=utf-8" })
  )

  const img = new Image()
  img.onload = () => {
    const canvas = document.createElement("canvas")
    canvas.width = width * scale
    canvas.height = height * scale
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    ctx.fillStyle = "#ffffff"
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.scale(scale, scale)
    ctx.drawImage(img, 0, 0)
    URL.revokeObjectURL(svgUrl)
    canvas.toBlob((blob) => {
      if (blob) triggerDownload(URL.createObjectURL(blob), filename)
    }, "image/png")
  }
  img.src = svgUrl
}

function triggerDownload(url: string, filename: string) {
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  // CSV/PNG blob URL은 약간의 지연 후 해제
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
