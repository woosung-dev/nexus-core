// 인용 청크를 문서 단위 카드로 묶는 공용 로직 — 자료 목록과 본문 각주 번호가 같은 순서를 써야 한다
import { Citation } from "@/types/api";

export interface DocGroup {
  title: string;
  pages: number[];
  chunks: Citation[];
  score: number; // 이 문서가 뒷받침한 구간 수의 합 — 정렬용
}

// 인용은 청크 단위로 온다. 한 문서가 여러 청크로 쪼개지고 각 청크가 여러 구간을
// 뒷받침해 목록이 수십 건으로 보이지만(실측 35건), 실제 문서는 2~3개뿐이다.
// 사용자에게 의미 있는 단위는 문서이므로 파일명으로 묶고 많이 참고한 순으로 세운다.
export function groupByDocument(citations: Citation[]): DocGroup[] {
  const byTitle = new Map<string, DocGroup>();
  for (const c of citations) {
    const title = c.title || "제목 없는 문서";
    let g = byTitle.get(title);
    if (!g) {
      g = { title, pages: [], chunks: [], score: 0 };
      byTitle.set(title, g);
    }
    g.chunks.push(c);
    g.score += c.cite_count ?? 1;
    if (typeof c.page_number === "number" && !g.pages.includes(c.page_number)) {
      g.pages.push(c.page_number);
    }
  }
  const groups = [...byTitle.values()];
  for (const g of groups) {
    g.pages.sort((a, b) => a - b);
    g.chunks.sort((a, b) => (b.cite_count ?? 1) - (a.cite_count ?? 1));
  }
  return groups.sort((a, b) => b.score - a.score);
}
