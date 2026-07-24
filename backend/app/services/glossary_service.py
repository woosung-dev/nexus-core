"""
용어집 프롬프트 보강 서비스.
용어 정의를 매칭해 반환할 뿐, 답변을 생성하거나 대체하지 않는다.
"""

import re
import time
import unicodedata
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_glossary
from app.models.bot import Bot

GLOSSARY_MAX_TERMS = 8
GLOSSARY_DEF_CHAR_CAP = 300
_CACHE_TTL = 60.0
# 봇별 캐시. 전역 용어를 포함한 결과를 각 봇 키에 저장한다.
_GLOSSARY_CACHE: dict[int, tuple[list, float]] = {}


@dataclass
class GlossaryMatch:
    """매칭된 용어 정의"""
    term: str
    definition: str
    source: str  # "lexical" | "semantic"
    priority: int
    matched_surface: str | None = None


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFKC", s).casefold()


def _is_ascii_word(surface: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9 _-]*", surface))


async def _load_terms(session: AsyncSession, bot_id: int) -> list:
    now = time.monotonic()
    cached = _GLOSSARY_CACHE.get(bot_id)
    if cached and now - cached[1] < _CACHE_TTL:
        return cached[0]
    rows = await crud_glossary.get_active_glossary_for_bot(session, bot_id)
    terms = list(rows)
    _GLOSSARY_CACHE[bot_id] = (terms, now)
    return terms


def _lexical_detect(query: str, rows: list) -> list[GlossaryMatch]:
    q = _normalize(query)
    hits = []  # (surface_norm, GlossaryMatch, bot_specific)
    seen_terms = set()
    for row in rows:
        surfaces = [row.term] + list(row.aliases or [])
        matched_surface = None
        for surf in surfaces:
            if not surf or len(surf.strip()) < 2:
                continue
            sn = _normalize(surf)
            if not sn:
                continue
            found = False
            if _is_ascii_word(sn):
                if re.search(r"\b" + re.escape(sn) + r"\b", q):
                    found = True
            elif sn in q:
                found = True
            if found:
                matched_surface = sn
                break
        if matched_surface is not None:
            key = _normalize(row.term)
            if key in seen_terms:
                continue
            seen_terms.add(key)
            hits.append((
                matched_surface,
                GlossaryMatch(
                    term=row.term,
                    definition=row.definition,
                    source="lexical",
                    priority=row.priority,
                    matched_surface=matched_surface,
                ),
                row.bot_id is not None,
            ))

    # 가장 긴 표면형을 우선해 부분 포함되는 짧은 매치를 제거한다.
    surfaces_all = [hit[0] for hit in hits]
    filtered = [
        hit for hit in hits
        if not any(hit[0] != other and hit[0] in other for other in surfaces_all)
    ]
    filtered.sort(key=lambda hit: (not hit[2], -hit[1].priority))
    return [hit[1] for hit in filtered][:GLOSSARY_MAX_TERMS]


async def search_glossary_terms(
    session: AsyncSession,
    bot: Bot,
    query_text: str,
) -> list[GlossaryMatch]:
    """봇의 용어집이 활성화된 경우에만 매칭하며, 실패는 빈 목록으로 처리한다."""
    try:
        if not getattr(bot, "glossary_enabled", False):
            return []
        rows = await _load_terms(session, bot.id)
        if not rows:
            return []
        return _lexical_detect(query_text, rows)
    except Exception:
        return []


def format_glossary_block(matches: list[GlossaryMatch]) -> str:
    """프롬프트에 추가할 용어 정의 블록 생성"""
    if not matches:
        return ""
    lines = [
        "\n\n---\n[도메인 용어 정의]",
        "아래는 이 질문에 등장한 전문 용어의 공식 정의다. 답변 시 이 정의를 권위 있는 근거로",
        "우선 사용하되, 정의에 없는 내용은 지어내지 말고 전체 문맥(검색된 문서 포함)에 근거해 답하라.",
        "이 정의만으로 곧바로 답을 끝내지 말 것. 관련 없는 용어는 무시하라.",
    ]
    for match in matches[:GLOSSARY_MAX_TERMS]:
        definition = (match.definition or "")[:GLOSSARY_DEF_CHAR_CAP]
        lines.append(f"- {match.term}: {definition}")
    return "\n".join(lines)


def invalidate_glossary_cache(bot_id: int | None = None) -> None:
    """봇별 또는 전체 용어집 캐시 무효화"""
    if bot_id is None:
        _GLOSSARY_CACHE.clear()
    else:
        _GLOSSARY_CACHE.pop(bot_id, None)


async def create_glossary_with_embedding(session, data: dict) -> "Glossary":
    """용어와 동의어 임베딩을 생성해 용어집을 저장한다."""
    from app.crud import crud_glossary
    from app.utils.embeddings import get_embedding

    surface = (data.get("term", "") + " " + " ".join(data.get("aliases") or [])).strip()
    try:
        data["term_vector"] = await get_embedding(surface) if surface else None
    except Exception:
        data["term_vector"] = None
    glossary = await crud_glossary.create_glossary(session, data)
    invalidate_glossary_cache(glossary.bot_id)
    return glossary


async def update_glossary_with_embedding(session, glossary, update_data: dict) -> "Glossary":
    """용어 또는 동의어 변경 시 임베딩을 갱신한다."""
    from app.crud import crud_glossary
    from app.utils.embeddings import get_embedding

    if "term" in update_data or "aliases" in update_data:
        term = update_data.get("term", glossary.term)
        aliases = update_data.get("aliases", glossary.aliases) or []
        surface = (term + " " + " ".join(aliases)).strip()
        try:
            update_data["term_vector"] = await get_embedding(surface) if surface else None
        except Exception:
            pass
    updated = await crud_glossary.update_glossary(session, glossary, update_data)
    invalidate_glossary_cache(updated.bot_id)
    return updated
