/**
 * 인용 구간을 원문에서 찾는다 — `exports/wiki_2026-08/_common.py:squash` 와 같은 규칙.
 *
 * 왜 공백을 다 지우고 비교하나 —
 *   원문은 PDF 에서 뽑은 것이라 줄바꿈 자리에 공백이 끼어 있다("탕 감봉", "12 일").
 *   공백을 남기고 비교하면 멀쩡한 인용이 거짓 불일치로 떨어진다.
 *   지우고 찾은 뒤, 칠할 위치는 원문 좌표로 되돌린다.
 */
function squash(s: string): { text: string; index: number[] } {
  const nfc = s.normalize("NFC")
  const chars: string[] = []
  const index: number[] = []
  for (let i = 0; i < nfc.length; i++) {
    if (/\s/.test(nfc[i])) continue
    chars.push(nfc[i])
    index.push(i)
  }
  return { text: chars.join(""), index }
}

/** 원문에서 인용이 차지하는 구간 `[시작, 끝)`. 못 찾으면 null — 그 자체가 검증 실패 신호다. */
export function findQuote(raw: string, quote: string): [number, number] | null {
  if (!quote.trim()) return null
  const R = squash(raw)
  const q = squash(quote).text
  const at = R.text.indexOf(q)
  if (at < 0) return null
  return [R.index[at], R.index[at + q.length - 1] + 1]
}
