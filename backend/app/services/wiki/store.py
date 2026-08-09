"""
LLM 위키 저장소 — 페이지·원문 로딩과 하이브리드 멀티스케일 검색 인덱스.

**임시 다리다.** 위키 산출물은 아직 DB 에 없고 `exports/wiki_2026-08/` 파일에만 있다
(`wiki-todo.md` P1). DB 적재가 끝나면 이 모듈의 로딩부는 crud 로 바뀐다.
인덱스와 검색 로직은 그대로 쓴다.

## 검색 설계

처음에는 **페이지 요약만 dense 로** 찾았고, 45문항 측정에서 위키 계열이 전패했다.
진 원인이 위키가 아니라 이 1단 검색기라는 정황이 로그에 남아 있었다 —
「가정회비 미납」에서 1위가 `유아회비`(0.808), 정답 `가정공과금`은 2위(0.790).

그래서 두 가지를 비워 뒀던 자리에 채웠다.

    하이브리드   BM25(어휘) + dense(의미) 를 RRF 로 합친다
    멀티스케일   페이지 요약 138 · 원문 조각 250 · 위키 사실문장 971 을 각각 인덱싱한다

**top_k 는 늘리지 않았다.** 후보 풀(리스트당 `DEPTH`)만 넓히고 최종 선택 폭은 그대로다 —
무관한 문서 한 건만 섞여도 생성 품질이 떨어진다는 게 문헌의 반대 방향 경고다.

인덱스는 파일 캐시다. 1,300여 문서 × 768차원이면 메모리 4MB 수준이라
프로세스 전역에 들고 있어도 되고, 재계산은 임베딩 API 1,200여 회라 캐시가 필요하다.
"""

import asyncio
import hashlib
import json
import logging
import math
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.services.wiki.retrieval import BM25, rrf
from app.utils.embeddings import get_embedding

logger = logging.getLogger(__name__)

# 위키 산출물 위치. DB 적재 전까지의 임시 경로다.
WIKI_ROOT = Path(
    os.getenv(
        "WIKI_ROOT",
        Path(__file__).resolve().parents[4] / "exports" / "wiki_2026-08",
    )
)

_FRONT = re.compile(r"^---\n(.*?)\n---\n+(.*)", re.S)


@dataclass
class WikiPage:
    slug: str
    title: str
    summary: str
    facts: str
    sources: list[str]


@dataclass
class SourceUnit:
    src_id: str
    doc: str
    locator: str
    text: str


@dataclass
class Retrieved:
    """1단 검색 결과 — 어떤 페이지를 왜 골랐는지가 남아야 디버깅이 된다.

    원문을 두 가지로 낸다. **둘 다 필요하다.**

        units         상위 페이지의 sources 합집합. 페이지 하나가 22건을 달고 있기도 해서
                      최대 24건까지 부푼다. 기존 팔 B 의 주입 정책이다.
        ranked_units  RRF 로 유닛 자체에 매긴 순위. 페이지를 거치지 않으므로 부풀지 않는다.

    한쪽만 남기면 "검색기를 고쳤더니 좋아졌다"와 "주입량을 줄였더니 좋아졌다"를 못 가른다.
    """

    pages: list[tuple[WikiPage, float]]
    units: list[SourceUnit]
    ranked_units: list[tuple[SourceUnit, float]] = field(default_factory=list)
    # 진단용. dense 만·BM25 만 썼으면 무엇이 1위였는지 — 순위가 뒤집혔는지 눈으로 본다.
    debug: dict = field(default_factory=dict)

    @property
    def top_score(self) -> float:
        return self.pages[0][1] if self.pages else 0.0


def _section(body: str, name: str) -> str:
    m = re.search(rf"^## {name}\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    return m.group(1).strip() if m else ""


def load_pages(bot_id: int) -> list[WikiPage]:
    """`bots/<id>/wiki/pages/*.md` 를 읽는다."""
    d = WIKI_ROOT / "bots" / str(bot_id) / "wiki" / "pages"
    if not d.is_dir():
        raise FileNotFoundError(f"위키 페이지 없음: {d}")

    pages: list[WikiPage] = []
    for path in sorted(d.glob("*.md")):
        m = _FRONT.match(path.read_text(encoding="utf-8"))
        if not m:
            logger.warning("프론트매터 없음, 건너뜀: %s", path.name)
            continue
        head, body = m.group(1), m.group(2)
        fields = dict(re.findall(r"^(\w+):\s*(.+)$", head, re.M))
        raw_sources = fields.get("sources", "").strip().strip("[]")
        pages.append(
            WikiPage(
                slug=fields.get("slug", path.stem),
                title=fields.get("title", path.stem),
                summary=_section(body, "요약"),
                facts=_section(body, "사실"),
                sources=[s.strip() for s in raw_sources.split(",") if s.strip()],
            )
        )
    return pages


def load_units(bot_id: int) -> dict[str, SourceUnit]:
    """봇 manifest 가 가리키는 원문 조각을 src_id → 유닛으로 읽는다."""
    manifest_path = WIKI_ROOT / "bots" / str(bot_id) / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    units: dict[str, SourceUnit] = {}
    for sha8 in manifest.get("sources", manifest.get("docs", [])):
        sha = sha8 if isinstance(sha8, str) else sha8.get("sha8")
        for path in sorted((WIKI_ROOT / "sources" / sha).glob("*.md")):
            m = _FRONT.match(path.read_text(encoding="utf-8"))
            if not m:
                continue
            head = dict(re.findall(r"^(\w+):\s*(.+)$", m.group(1), re.M))
            units[head["src_id"]] = SourceUnit(
                src_id=head["src_id"],
                doc=head["doc"],
                locator=head["locator"],
                text=m.group(2).rstrip(),
            )
    return units


# 임베딩 무료 티어에는 **두 개의 상한**이 있다. 분당만 보고 있다가 하루치에 걸렸다.
#
#   분당  약 100회        → 아래 페이싱으로 피한다
#   하루  1,000회         → 페이싱으로 못 피한다. 쓸 수 있는 총량이다
#                          (quotaId: EmbedContentRequestsPerDayPerUserPerProjectPerModel-FreeTier)
#
# 하루 1,000회는 이 코퍼스에서 빠듯하다 — 사실문장 971개를 dense 로 넣으면 그날은 질문 임베딩
# 45회조차 못 쓴다. 그래서 스케일별로 dense 를 켜고 끌 수 있게 했다(`dense_scales`).
_EMBED_INTERVAL = 0.7  # 초. 약 85회/분.
_last_embed = 0.0


async def _embed_paced(text: str, retries: int = 4) -> list[float]:
    """분당 한도에 맞춰 간격을 두고, 429 는 물러섰다 다시 시도한다."""
    global _last_embed
    for attempt in range(retries):
        gap = _EMBED_INTERVAL - (time.monotonic() - _last_embed)
        if gap > 0:
            await asyncio.sleep(gap)
        _last_embed = time.monotonic()
        try:
            return await get_embedding(text)
        except RuntimeError as e:
            if "429" not in str(e) or attempt == retries - 1:
                raise
            backoff = 15 * (attempt + 1)
            logger.warning("임베딩 429 — %d초 후 재시도 (%d/%d)", backoff, attempt + 1, retries)
            await asyncio.sleep(backoff)
    raise RuntimeError("임베딩 재시도 소진")


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _cosine(a: list[float], b: list[float], nb: float | None = None) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = _norm(a)
    nb = _norm(b) if nb is None else nb
    return dot / (na * nb) if na and nb else 0.0


# 조각 하나가 너무 길면 BM25 의 길이정규화가 무너진다. 원문 250건 중 12건이 2,000자를 넘고
# `reg-100`(부록 덤프)은 29,775자다 — 이 한 건이 거의 모든 질의에 걸린다.
_CHUNK_CHARS = 1500
# 리스트당 후보 깊이. top_k 가 아니다 — 융합에 쓸 후보 풀만 넓힌다.
DEPTH = 50

_SRC_TAG = re.compile(r"\[\[src:\s*([\w-]+)\]\]")


def _chunk(text: str, limit: int = _CHUNK_CHARS) -> list[str]:
    """줄바꿈 경계로 자른다. 조문 안의 항(①②) 이 통째로 쪼개지는 걸 줄인다."""
    if len(text) <= limit:
        return [text]
    out, buf = [], ""
    for line in text.split("\n"):
        if buf and len(buf) + len(line) + 1 > limit:
            out.append(buf)
            buf = ""
        # 한 줄 자체가 limit 을 넘으면 그 줄만 강제로 썬다
        while len(line) > limit:
            out.append(line[:limit])
            line = line[limit:]
        buf = f"{buf}\n{line}" if buf else line
    if buf:
        out.append(buf)
    return out


@dataclass
class Scale:
    """한 입도(粒度)의 인덱스. dense 와 BM25 가 같은 문서 목록을 본다.

    `ids` 는 중복될 수 있다 — 긴 원문은 여러 청크로 들어가지만 모두 같은 `src_id` 를 가리킨다.
    RRF 가 같은 id 의 첫 등수만 세므로 중복 가산은 나지 않는다.
    """

    name: str
    ids: list[str]
    texts: list[str]
    vectors: list[list[float]] = field(default_factory=list)
    norms: list[float] = field(default_factory=list)
    bm25: BM25 | None = None
    # 하루 1,000회 상한 때문에 dense 를 못 켜는 스케일이 생긴다. 그때도 BM25 로는 검색된다.
    dense_enabled: bool = True

    @property
    def hash(self) -> str:
        """임베딩 텍스트의 해시. 캐시 검증을 여기에 건다.

        예전 캐시는 페이지 슬러그 목록만 봤다. 위키를 재생성해 요약 내용만 바뀌면
        캐시가 안 깨져서 옛 벡터로 검색하는 사고가 났다.
        """
        h = hashlib.sha256()
        for t in self.texts:
            h.update(t.encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()

    def dense(self, qv: list[float], depth: int = DEPTH) -> list[tuple[str, float]]:
        if not (self.vectors and qv):
            return []
        scored = sorted(
            zip(self.ids, (_cosine(qv, v, n) for v, n in zip(self.vectors, self.norms))),
            key=lambda t: t[1],
            reverse=True,
        )
        return scored[:depth]

    def lexical(self, question: str, depth: int = DEPTH) -> list[tuple[str, float]]:
        return self.bm25.search(question, depth) if self.bm25 else []


class WikiIndex:
    """하이브리드 멀티스케일 인덱스. 봇 하나당 하나."""

    CACHE_VERSION = 2

    def __init__(
        self,
        bot_id: int,
        dense_scales: set[str] | None = None,
        pages: list[WikiPage] | None = None,
        units: dict[str, SourceUnit] | None = None,
    ) -> None:
        """`pages`·`units` 를 주입하면 파일시스템을 읽지 않는다.

        `__init__` 이 동기라 async 로더(DB)를 안에서 부를 수 없다. 그래서 `get_index` 가
        먼저 읽어 넣어 준다. 주입이 없으면 예전처럼 파일시스템에서 읽는다.
        """
        self.bot_id = bot_id
        self.pages = load_pages(bot_id) if pages is None else pages
        self.units = load_units(bot_id) if units is None else units
        self.by_slug = {p.slug: p for p in self.pages}
        self._qcache: dict[str, list[float]] | None = None

        # 사실 문장 → 소속 페이지 / 근거 원문. 매핑이 있어야 스케일 간 융합이 된다.
        self.fact_page: dict[str, str] = {}
        self.fact_src: dict[str, str] = {}
        # 원문 → 그 원문을 인용하는 페이지들 (역방향)
        self.citing: dict[str, list[str]] = {}
        for page in self.pages:
            for src in page.sources:
                self.citing.setdefault(src, []).append(page.slug)

        # 어떤 스케일에 dense 를 걸지. 하루 임베딩 상한(1,000회) 때문에 선택지가 필요하다.
        # 뺀 스케일은 BM25 로만 검색된다 — 빠지는 게 아니라 어휘 순위표 하나로 남는다.
        # 기본값은 **BM25 전용**이다(빈 문자열). dense 를 우리 쪽에서 만드는 것 자체가 복제였다 —
        # 의미 검색은 file_search 가 이미 하고, 우리 dense 는 file_search 와 **같은 방식으로 같이**
        # 틀렸다(「가정회비 → 유아회비」). 역할을 가르면 결과 해석도 깨끗해진다.
        # 실무적으로도 켜 두면 안 된다: 첫 요청에서 1,401건을 임베딩해 하루 상한(1,000회)을 넘긴다.
        if dense_scales is None:
            env = os.getenv("WIKI_DENSE_SCALES", "")
            dense_scales = {s.strip() for s in env.split(",") if s.strip()}

        self.scales: dict[str, Scale] = {
            "page": self._scale_page(),
            "unit": self._scale_unit(),
            "fact": self._scale_fact(),
        }
        for name, scale in self.scales.items():
            scale.dense_enabled = name in dense_scales

    # ---- 스케일 구성 -------------------------------------------------------

    def _scale_page(self) -> Scale:
        """제목을 함께 실는다 — 요약에 제목 단어가 안 나오는 쪽이 검색에서 밀린다."""
        ids = [p.slug for p in self.pages]
        texts = [f"{p.title}\n{p.summary}" for p in self.pages]
        return Scale("page", ids, texts)

    def _scale_unit(self) -> Scale:
        ids, texts = [], []
        for src_id, u in self.units.items():
            for chunk in _chunk(u.text):
                ids.append(src_id)
                texts.append(f"{u.doc} {u.locator}\n{chunk}")
        return Scale("unit", ids, texts)

    def _scale_fact(self) -> Scale:
        """`## 사실` 의 항목 하나가 문서 하나다.

        항목에 딸린 `> 원문 인용` 줄까지 함께 싣는다 — 정리 문장은 말을 다듬어 놓아서
        원문의 표현(숫자·조문 번호)이 빠져 있는 경우가 있고, 어휘 검색은 거기서 걸린다.
        """
        ids, texts = [], []
        for page in self.pages:
            cur: list[str] = []
            idx = 0

            def flush() -> None:
                nonlocal cur, idx
                if not cur:
                    return
                body = "\n".join(cur)
                m = _SRC_TAG.search(body)
                fid = f"{page.slug}#{idx}"
                self.fact_page[fid] = page.slug
                if m:
                    self.fact_src[fid] = m.group(1)
                ids.append(fid)
                texts.append(f"{page.title} — {_SRC_TAG.sub('', body).strip()}")
                idx += 1
                cur = []

            for line in page.facts.split("\n"):
                if line.startswith("- "):
                    flush()
                    cur = [line[2:]]
                elif cur:
                    cur.append(line.strip())
            flush()
        return Scale("fact", ids, texts)

    # ---- 캐시 --------------------------------------------------------------

    @property
    def cache_path(self) -> Path:
        return WIKI_ROOT / "bots" / str(self.bot_id) / "_index.json"

    def _load_cache(self) -> dict[str, list[list[float]]]:
        """쓸 수 있는 벡터만 스케일별로 돌려준다. 하나가 상해도 나머지는 산다."""
        if not self.cache_path.exists():
            return {}
        cached = json.loads(self.cache_path.read_text(encoding="utf-8"))

        # v1 캐시(페이지만, 슬러그 검증)에서 페이지 벡터를 이관한다 — 임베딩 138회를 아낀다.
        if cached.get("version") != self.CACHE_VERSION:
            page = self.scales["page"]
            if cached.get("slugs") == page.ids and len(cached.get("vectors", [])) == len(page.ids):
                logger.info("v1 캐시에서 페이지 벡터 %d개 이관", len(page.ids))
                return {"page": cached["vectors"]}
            return {}

        out = {}
        for name, scale in self.scales.items():
            blob = cached.get("scales", {}).get(name)
            if blob and blob.get("hash") == scale.hash and len(blob.get("vectors", [])) == len(scale.ids):
                out[name] = blob["vectors"]
            elif blob:
                logger.info("스케일 %s 캐시 무효 — 내용이 바뀌었다", name)
        return out

    def _save_cache(self) -> None:
        self.cache_path.write_text(
            json.dumps(
                {
                    "version": self.CACHE_VERSION,
                    "scales": {
                        name: {"ids": s.ids, "hash": s.hash, "vectors": s.vectors}
                        for name, s in self.scales.items()
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    async def build(self, force: bool = False) -> int:
        """빠진 벡터만 만들어 캐시에 쓴다. BM25 는 API 호출이 없으므로 항상 새로 만든다."""
        cache = {} if force else self._load_cache()
        made = 0
        for name, scale in self.scales.items():
            scale.bm25 = BM25(list(zip(scale.ids, scale.texts)))
            hit = cache.get(name)
            if not scale.dense_enabled:
                scale.vectors, scale.norms = [], []
                logger.info("스케일 %s — BM25 전용(dense 끔). 어휘 순위표로만 융합에 들어간다", name)
                continue
            if hit:
                scale.vectors = hit
                logger.info("스케일 %s 캐시 적중 — %d건", name, len(hit))
            else:
                logger.info("스케일 %s 임베딩 %d건 시작 (약 %.0f분)", name, len(scale.texts),
                            len(scale.texts) * _EMBED_INTERVAL / 60)
                scale.vectors = []
                for i, text in enumerate(scale.texts):
                    scale.vectors.append(await _embed_paced(text))
                    if i and i % 50 == 0:
                        logger.info("  %s %d/%d", name, i, len(scale.texts))
                made += len(scale.vectors)
                # 스케일 하나가 끝날 때마다 쓴다. 1,200회 중반에 끊기면 15분을 다시 태운다.
                self._save_cache()
            scale.norms = [_norm(v) for v in scale.vectors]

        if made:
            logger.info("위키 인덱스 저장 — 신규 임베딩 %d건", made)
        return made

    # ---- 질문 임베딩 캐시 ----------------------------------------------------

    @property
    def query_cache_path(self) -> Path:
        return WIKI_ROOT / "bots" / str(self.bot_id) / "_query_cache.json"

    async def query_vector(self, question: str) -> list[float]:
        """같은 질문은 다시 임베딩하지 않는다.

        측정 하네스는 한 질문을 팔 B·B′·C 세 번 검색한다. 벡터는 셋이 같은데
        예전에는 세 번 다 API 를 불렀다 — 45문항이면 135회, 하루 상한 1,000회의 13%다.
        재실행까지 생각하면 이 캐시가 상한을 지키는 유일한 방법이다.
        """
        cache = self._qcache
        if cache is None:
            cache = (
                json.loads(self.query_cache_path.read_text(encoding="utf-8"))
                if self.query_cache_path.exists()
                else {}
            )
            self._qcache = cache
        key = hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]
        if key in cache:
            return cache[key]

        cache[key] = await _embed_paced(question)
        self.query_cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        return cache[key]

    # ---- 검색 --------------------------------------------------------------

    async def search(self, question: str, top_k: int = 3) -> Retrieved:
        """세 스케일 × 두 검색기 = 6개 순위표를 RRF 로 두 공간에 융합한다.

        페이지 공간과 유닛 공간을 따로 낸다. 무엇을 주입하느냐가 팔마다 다르기 때문이다.

        **page 스케일은 유닛 공간에 넣지 않는다.** 페이지 하나가 sources 22건을 같은 등수로
        쏟아부어, 팔 B 를 최하위로 만든 "원문 통짜 주입"을 그대로 재현한다. 강한 페이지는
        어차피 자기 사실 문장으로 올라온다 — 971개가 138쪽 전부를 덮는다.
        """
        if self.scales["page"].bm25 is None:
            await self.build()

        # dense 를 쓰는 스케일이 하나도 없으면 질문 임베딩도 부르지 않는다.
        # 안 그러면 문서 벡터는 안 만들면서 질문 벡터로만 하루 상한을 태운다.
        qv = (
            await self.query_vector(question)
            if any(s.dense_enabled for s in self.scales.values())
            else []
        )
        ranked = {
            f"{name}.{kind}": [i for i, _ in lst]
            for name, scale in self.scales.items()
            for kind, lst in (("dense", scale.dense(qv)), ("bm25", scale.lexical(question)))
            if lst
        }

        to_page, to_unit = [], []
        for key, ids in ranked.items():
            scale = key.split(".")[0]
            if scale == "page":
                to_page.append(ids)
            elif scale == "fact":
                to_page.append([self.fact_page[i] for i in ids])
                to_unit.append([self.fact_src[i] for i in ids if i in self.fact_src])
            else:  # unit
                to_unit.append(ids)
                to_page.append([slug for i in ids for slug in self.citing.get(i, [])])

        page_scores = rrf(to_page)
        unit_scores = rrf(to_unit)

        scored = [
            (self.by_slug[s], sc)
            for s, sc in sorted(page_scores.items(), key=lambda kv: kv[1], reverse=True)
            if s in self.by_slug
        ][:top_k]

        # 팔 B — 기존 정책 그대로. 상위 페이지가 인용하는 원문 전부를 페이지 순서대로.
        seen: list[str] = []
        for page, _ in scored:
            for src in page.sources:
                if src not in seen:
                    seen.append(src)

        # 팔 B′ — 유닛에 직접 매긴 순위. 페이지를 거치지 않으므로 부풀지 않는다.
        ranked_units = [
            (self.units[s], sc)
            for s, sc in sorted(unit_scores.items(), key=lambda kv: kv[1], reverse=True)
            if s in self.units
        ]

        page_scale = self.scales["page"]
        return Retrieved(
            pages=scored,
            units=[self.units[s] for s in seen if s in self.units],
            ranked_units=ranked_units,
            debug={
                "page_dense": [(i, round(v, 3)) for i, v in page_scale.dense(qv, 5)],
                "page_bm25": [(i, round(v, 2)) for i, v in page_scale.lexical(question, 5)],
                "unit_top": [(u.src_id, round(sc, 4)) for u, sc in ranked_units[:5]],
                # 어떤 순위표가 실제로 융합에 들어갔는지. dense 를 끈 스케일이 있으면 여기서 드러난다.
                "lists": sorted(ranked),
            },
        )


_INDEX_CACHE: dict[int, WikiIndex] = {}


async def _from_db(bot_id: int) -> tuple[list[WikiPage], dict[str, SourceUnit]] | None:
    """DB 에서 페이지·원문을 읽는다. 적재 전이거나 DB 를 못 붙으면 None.

    폴백을 남기는 이유는 측정 하네스(`exports/wiki_eval/`)가 DB 없이도 돌아야 하기 때문이다.

    **페이지도 함께 읽는다.** 답변 본문으로 쓰려는 게 아니라 fact 스케일(971건)과 페이지
    역매핑을 만드는 검색 신호다. 빼고 45문항을 재보니 실제 주입 원문이 43/45 에서 달라졌고
    reg-100(29,774자)이 1/45 → 19/45 로 늘어 예산을 통째로 먹었다.
    """
    try:
        from app.core.database import async_session
        from app.crud import crud_wiki_source

        async with async_session() as session:
            unit_rows = await crud_wiki_source.get_units_for_bot(session, bot_id)
            page_rows = await crud_wiki_source.get_pages_for_bot(session, bot_id)
    except Exception as e:  # DB 미기동·미마이그레이션 등
        logger.warning("위키 DB 조회 실패 — 파일시스템으로 폴백한다: %s", e)
        return None
    if not unit_rows:
        return None
    units = {
        r.src_id: SourceUnit(src_id=r.src_id, doc=r.doc, locator=r.locator, text=r.text)
        for r in unit_rows
    }
    pages = [
        WikiPage(slug=p.slug, title=p.title, summary=p.summary, facts=p.facts,
                 sources=list(p.sources or []))
        for p in page_rows
    ]
    if not pages:
        logger.warning(
            "bot=%s 위키 페이지가 DB 에 0쪽이다 — fact 스케일이 비어 검색 품질이 떨어진다 "
            "(scripts/import_wiki_sources.py 로 적재할 것)", bot_id)
    return pages, units


class WikiCorpusUnavailable(RuntimeError):
    """이 봇의 원문을 DB 에서도 파일시스템에서도 못 찾았다.

    호출자가 잡아서 다른 조달 방식으로 되돌리라고 있는 예외다. 그냥 새어 나가면
    배포 환경(= `exports/wiki_2026-08/` 가 없는 이미지)에서 500 이 된다.
    """


async def get_index(bot_id: int) -> WikiIndex:
    """봇별 인덱스 싱글턴. DB 우선, 없으면 파일시스템, 둘 다 없으면 예외."""
    idx = _INDEX_CACHE.get(bot_id)
    if idx is not None:
        return idx

    loaded = await _from_db(bot_id)
    if loaded is not None:
        pages, units = loaded
        source = "DB"
    else:
        # 배포 이미지에는 exports/ 가 없다. 여기서 FileNotFoundError 가 그대로 새면
        # 사용자에게 500 이 나가므로, 되돌릴 수 있는 예외로 바꿔서 올린다.
        try:
            pages, units, source = load_pages(bot_id), load_units(bot_id), "파일시스템"
        except (FileNotFoundError, OSError, KeyError, ValueError) as e:
            raise WikiCorpusUnavailable(
                f"bot={bot_id} 원문을 DB·파일시스템 어디에서도 못 읽었다 "
                f"(scripts/import_wiki_sources.py 로 적재할 것): {e}"
            ) from e

    if not units:
        raise WikiCorpusUnavailable(f"bot={bot_id} 원문이 0건이다")

    logger.info("위키 인덱스 구성 bot=%s 원문=%d 페이지=%d (%s)",
                bot_id, len(units), len(pages), source)
    idx = WikiIndex(bot_id, pages=pages, units=units)
    await idx.build()
    _INDEX_CACHE[bot_id] = idx
    return idx


def clear_index_cache(bot_id: int | None = None) -> None:
    """인덱스 싱글턴을 버린다. 원문을 다시 적재한 뒤 부르지 않으면 재시작 전까지 옛 원문으로 답한다."""
    if bot_id is None:
        _INDEX_CACHE.clear()
    else:
        _INDEX_CACHE.pop(bot_id, None)
