# 신규 공문 4종·규정집 PDF를 pdfplumber 로 텍스트 추출하는 일회성 스크립트
# 사용: uv run --with pdfplumber python exports/round3_rag/_extract.py
import sys
from pathlib import Path

import pdfplumber

OUT = Path("/Users/woosung/project/agy-project/nexus-core/exports/round3_redteam/03_RAG데이터")
OUT.mkdir(parents=True, exist_ok=True)
DL = Path("/Users/woosung/Downloads")

# (출력파일 stem, 원본 PDF 경로)
DOCS = {
    "gongmun1_매칭자격_연령변경": DL / "축복자녀-1세 매칭확정자 자격 및 기준 변경v1.pdf",
    "gongmun2_2025이수교육_인정기준확대": DL / "20241015 '2025 축복후보자 이수 교육 인정기준 확대' 안내 _v2.pdf",
    "gongmun3_12일_가정출발의식": DL / "(가정출발교육) 미혼2세1세 축복후 2세가정 확정을 위한 12일 가정출발의식(20210510) v6.pdf",
    "gongmun4_장애축복자녀_헌금축도권": DL / "세가한본 제2024-96호(가정-8)장애 축복자녀 축복헌금 조정 및 축도권 안내 안내.pdf",
}
REG = DL / "[2022_ver.] 축복행정 국제 규정집.pdf"


def extract(path: Path) -> tuple[str, int]:
    if not path.exists():
        return f"[MISSING] {path}", 0
    parts = []
    with pdfplumber.open(path) as pdf:
        npages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ""
            parts.append(f"\n=== p.{i+1} ===\n{txt}")
    return "".join(parts), npages


def main():
    for stem, path in DOCS.items():
        text, npages = extract(path)
        outp = OUT / f"{stem}.raw.txt"
        outp.write_text(text, encoding="utf-8")
        print(f"[공문] {stem}: pages={npages} chars={len(text)} -> {outp.name}")
        print("  head:", " ".join(text.split())[:160])
        print()

    # 규정집: 9장 구조 검증용으로 추출(대용량이라 별도)
    if "--reg" in sys.argv:
        text, npages = extract(REG)
        (OUT / "regulation_2022.raw.txt").write_text(text, encoding="utf-8")
        print(f"[규정집] pages={npages} chars={len(text)} -> regulation_2022.raw.txt")


if __name__ == "__main__":
    main()
