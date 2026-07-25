// 답변 본문의 근거 구간 끝에 자료 카드 번호를 각주로 심는 로직 (마크다운 파이프라인용)
import { Citation } from "@/types/api";
import { groupByDocument } from "./citationGroups";

// 본문에 잠시 심는 표식. 마크다운 특수문자가 없어 파싱 후에도 텍스트 노드 하나 안에 통째로 남고,
// 답변이 이 문자를 스스로 쓸 일도 없다. rehype 단계에서 <sup> 엘리먼트로 바꿔 뺀다.
const OPEN = "⟦cite:";
const CLOSE = "⟧";
export const MARKER_RE = /⟦cite:(\d+)⟧/;
const MARKER_RE_G = /⟦cite:(\d+)⟧/g;

/**
 * 각 근거 구간(segments)의 끝에 그 구간을 뒷받침한 자료의 카드 번호를 심는다.
 *
 * 구간 문자열은 답변 본문에 그대로 존재한다(2026-07-25 D-1 실측 37/37) — 그래서 byte offset 없이
 * 문자열 검색만으로 앵커한다. 근사 인용은 구간 기준 답변이 달라 segments 가 비고, 따라서 각주도 안 붙는다.
 */
export function insertCitationMarkers(
  content: string,
  citations?: Citation[] | null
): string {
  const groups = groupByDocument(citations ?? []);
  if (groups.length === 0 || !content) return content;

  // 위치 → 그 위치에 붙일 카드 번호들. 한 구간을 여러 자료가 뒷받침하면 번호가 여러 개 붙는다.
  const marks = new Map<number, number[]>();
  groups.forEach((g, gi) => {
    const num = gi + 1;
    for (const chunk of g.chunks) {
      for (const seg of chunk.segments ?? []) {
        const text = seg.trim();
        if (text.length < 4) continue;
        const at = content.indexOf(text);
        if (at < 0) continue;
        // 구간 끝이 강조 기호 사이일 수 있다(실측: 구간이 "… 것은 **가능합니다" 로 끝남).
        // 그 틈에 표식을 끼우면 마크다운이 깨지므로 기호 뒤로 밀어낸다.
        let end = at + text.length;
        while (end < content.length && (content[end] === "*" || content[end] === "_")) end += 1;
        const nums = marks.get(end) ?? [];
        if (!nums.includes(num)) nums.push(num);
        marks.set(end, nums);
      }
    }
  });
  if (marks.size === 0) return content;

  // 뒤에서부터 넣어야 앞쪽 인덱스가 밀리지 않는다.
  let out = content;
  for (const pos of [...marks.keys()].sort((a, b) => b - a)) {
    const tag = marks
      .get(pos)!
      .sort((a, b) => a - b)
      .map((n) => `${OPEN}${n}${CLOSE}`)
      .join("");
    out = out.slice(0, pos) + tag + out.slice(pos);
  }
  return out;
}

interface HastNode {
  type: string;
  tagName?: string;
  value?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
}

/**
 * 심어둔 표식을 <sup data-cite="n"> 엘리먼트로 바꾸는 rehype 플러그인.
 *
 * 마크다운을 raw HTML 로 다루지 않는 이유 — rehype-raw 를 안 쓰기 때문이고, 쓰고 싶지도 않다.
 * 답변 본문은 모델이 만든 문자열이라 HTML 을 그대로 신뢰하면 안 된다. 표식→엘리먼트 변환은
 * 파싱이 끝난 트리에서 일어나므로 본문의 어떤 문자도 마크업으로 재해석되지 않는다.
 */
export function rehypeCitationMarkers() {
  const walk = (node: HastNode) => {
    if (!node.children) return;
    const next: HastNode[] = [];
    for (const child of node.children) {
      if (child.type !== "text" || !child.value || !MARKER_RE.test(child.value)) {
        walk(child);
        next.push(child);
        continue;
      }
      let cursor = 0;
      const value = child.value;
      for (const m of value.matchAll(MARKER_RE_G)) {
        const at = m.index ?? 0;
        if (at > cursor) next.push({ type: "text", value: value.slice(cursor, at) });
        next.push({
          type: "element",
          tagName: "sup",
          properties: { dataCite: m[1] },
          children: [{ type: "text", value: m[1] }],
        });
        cursor = at + m[0].length;
      }
      if (cursor < value.length) next.push({ type: "text", value: value.slice(cursor) });
    }
    node.children = next;
  };
  return walk;
}
