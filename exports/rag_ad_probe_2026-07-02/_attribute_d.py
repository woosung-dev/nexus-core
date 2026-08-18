# D 아키텍처: 저장된 표시답변(P)을 읽기 전용으로 문장 분리해 PF 청크에 임베딩 정렬(재생성 0회)
import os
import sys
import json
import asyncio
import math
import re
from pathlib import Path

ROOT = Path("/Users/woosung/project/agy-project/nexus-core")
for _l in (ROOT / "backend/.env").read_text().splitlines():
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        k, v = _l.split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"').strip("'"))
sys.path.insert(0, str(ROOT / "backend"))
import logging  # noqa: E402
logging.disable(logging.INFO)

from google.genai import types  # noqa: E402

from app.services.llm.gemini import _get_genai_client  # noqa: E402

DIR = Path(__file__).parent
CAPS = json.loads((DIR / "captures.json").read_text())
OUT = DIR / "attribution.json"
EMBED_MODEL = "gemini-embedding-001"
THRESHOLDS = [round(0.50 + 0.05 * i, 2) for i in range(9)]  # 0.50 ~ 0.90
BATCH = 50  # 임베딩 무료 쿼터가 분당 100 '콘텐츠' 기준이라 배치 50 + 40s 페이싱

# 한국어 문장 분리: 종결어미+문장부호 뒤 경계. 목록 항목·짧은 조각은 별도 처리.
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    parts = []
    for raw in _SENT_SPLIT_RE.split(text):
        s = raw.strip().lstrip("-•*").strip()
        s = re.sub(r"^#+\s*", "", s)  # 마크다운 헤딩 제거
        s = re.sub(r"\*\*", "", s)
        if len(s) >= 10:  # 너무 짧은 조각(인사·접속부)은 귀속 대상에서 제외
            parts.append(s)
    return parts


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


CACHE_PATH = Path(__file__).parent / "_embed_cache.json"


async def embed_all(client, texts: list[str]) -> list[list[float]]:
    """분당 100요청(무료 쿼터) 페이싱 + 429 백오프 + 디스크 캐시(resume-safe)."""
    disk: dict[str, list[float]] = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}
    out: dict[str, list[float]] = {}
    todo = [t for t in texts if t not in disk]
    print(f"임베딩: 캐시 {len(texts) - len(todo)} / 신규 {len(todo)}")
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        for attempt in range(6):
            try:
                res = await client.aio.models.embed_content(
                    model=EMBED_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY", output_dimensionality=768),
                )
                for t, e in zip(batch, res.embeddings):
                    disk[t] = e.values
                break
            except Exception as e:
                if "429" not in str(e) and "RESOURCE_EXHAUSTED" not in str(e):
                    raise
                wait = 35.0 * (attempt + 1)
                print(f"  429 — {wait:.0f}s 대기 (batch {i // BATCH})")
                await asyncio.sleep(wait)
        else:
            raise RuntimeError("임베딩 429 재시도 소진")
        CACHE_PATH.write_text(json.dumps(disk), encoding="utf-8")
        print(f"  batch {i // BATCH + 1}/{(len(todo) + BATCH - 1) // BATCH} 완료")
        if i + BATCH < len(todo):
            await asyncio.sleep(40.0)  # 분당 쿼터 페이싱 (배치=요청 N개로 계산됨)
    for t in texts:
        out[t] = disk[t]
    return [out[t] for t in texts]


async def main():
    client = _get_genai_client()

    # 전 질문의 문장·청크를 모아 한 번에 임베딩 (중복 텍스트 캐시)
    jobs = []  # (qid, sentences, chunks)
    for key in sorted(CAPS, key=int):
        rec = CAPS[key]
        p, pf = rec.get("P") or {}, rec.get("PF") or {}
        if p.get("error") or pf.get("error") or not p.get("answer"):
            continue
        sentences = split_sentences(p["answer"])
        # 청크 dedupe (title+text 기준)
        seen, chunks = set(), []
        for ch in pf.get("chunks") or []:
            k = (ch.get("title") or "") + "|" + (ch.get("text") or "")[:200]
            if k in seen or not ch.get("text"):
                continue
            seen.add(k)
            chunks.append(ch)
        if sentences and chunks:
            jobs.append((key, sentences, chunks))

    cache: dict[str, list[float]] = {}
    uniq = []
    for _, sents, chunks in jobs:
        for t in sents + [c["text"][:2000] for c in chunks]:
            if t not in cache:
                cache[t] = []
                uniq.append(t)
    print(f"질문 {len(jobs)}건 · 고유 임베딩 대상 {len(uniq)}개")
    vecs = await embed_all(client, uniq)
    for t, v in zip(uniq, vecs):
        cache[t] = v

    results = {}
    for key, sents, chunks in jobs:
        svecs = [cache[s] for s in sents]
        cvecs = [cache[c["text"][:2000]] for c in chunks]
        sent_rows = []
        for s, sv in zip(sents, svecs):
            scores = [cosine(sv, cv) for cv in cvecs]
            best = max(range(len(scores)), key=lambda i: scores[i])
            sent_rows.append({
                "sentence": s,
                "best_chunk": best,
                "best_title": chunks[best].get("title"),
                "score": round(scores[best], 4),
            })
        # 임계값별 인용 산출: 임계값을 넘긴 문장이 가리키는 청크의 합집합
        by_threshold = {}
        for th in THRESHOLDS:
            cited = sorted({r["best_chunk"] for r in sent_rows if r["score"] >= th})
            by_threshold[str(th)] = {
                "cited_chunks": cited,
                "covered_sentences": sum(1 for r in sent_rows if r["score"] >= th),
            }
        results[key] = {
            "n_sentences": len(sents),
            "n_chunks": len(chunks),
            "chunk_titles": [c.get("title") for c in chunks],
            "sentences": sent_rows,
            "by_threshold": by_threshold,
        }

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    # 요약 출력
    for th in THRESHOLDS:
        with_cit = sum(1 for r in results.values() if r["by_threshold"][str(th)]["cited_chunks"])
        cov = sum(r["by_threshold"][str(th)]["covered_sentences"] for r in results.values())
        tot = sum(r["n_sentences"] for r in results.values())
        print(f"th={th:.2f}  인용≥1 질문 {with_cit}/{len(results)}  문장커버리지 {cov}/{tot} ({cov / tot * 100:.0f}%)")
    print(f"→ {OUT.name}")


asyncio.run(main())
