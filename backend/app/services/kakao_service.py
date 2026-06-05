# 카카오 응답 변환 + 콜백 전송을 담당하는 어댑터 서비스 (순수 변환 + httpx)
import logging
import re
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


def _host_matches(host: str, suffix: str) -> bool:
    suffix = suffix.lstrip(".").lower()
    return host == suffix or host.endswith("." + suffix)


def is_allowed_callback_host(url: str, allowed_suffixes: list[str]) -> bool:
    """callbackUrl host 가 허용 도메인(suffix)이고 http(s) 스킴인지. SSRF 차단용."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("https", "http"):
        return False
    host = parsed.hostname
    if not host:
        return False
    host = host.lower()
    return any(_host_matches(host, s) for s in allowed_suffixes)


KAKAO_SIMPLE_TEXT_LIMIT = 1000
KAKAO_MAX_OUTPUTS = 3


def _find_break(text: str, limit: int) -> int:
    """limit 이내에서 자연스러운 분할 지점(문단/줄/문장/공백)을 찾는다. 없으면 limit."""
    window = text[:limit]
    for sep in ("\n\n", "\n"):
        idx = window.rfind(sep)
        if idx > limit * 0.5:
            return idx + len(sep)
    last_end = -1
    for match in re.finditer(r"[.!?。！？]\s", window):
        last_end = match.end()
    if last_end > limit * 0.5:
        return last_end
    idx = window.rfind(" ")
    if idx > limit * 0.5:
        return idx + 1
    return limit


def _split_text(text: str, limit: int, max_chunks: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining and len(chunks) < max_chunks:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        if len(chunks) == max_chunks - 1:  # 마지막 칸인데 아직 넘침 → 잘라서 …
            chunks.append(remaining[: limit - 1].rstrip() + "…")
            break
        cut = _find_break(remaining, limit)
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return chunks


def to_simple_text_outputs(content: str) -> list[dict]:
    """답변 텍스트를 카카오 outputs(simpleText ≤3개, 각 ≤1000자)로 변환."""
    text = (content or "").strip() or "응답을 생성하지 못했습니다."
    return [{"simpleText": {"text": c}} for c in _split_text(text, KAKAO_SIMPLE_TEXT_LIMIT, KAKAO_MAX_OUTPUTS)]


KAKAO_MAX_QUICK_REPLIES = 10
KAKAO_QUICK_REPLY_LABEL_LIMIT = 14  # 라벨 표시 한도(대략) — messageText 는 전체 유지


def to_quick_replies(followups: list[str] | None) -> list[dict]:
    """후속질문 리스트를 quickReplies(≤10)로 변환. messageText 는 전체, label 은 표시용으로 절단."""
    if not followups:
        return []
    replies: list[dict] = []
    for raw in followups[:KAKAO_MAX_QUICK_REPLIES]:
        text = (raw or "").strip()
        if not text:
            continue
        label = text if len(text) <= KAKAO_QUICK_REPLY_LABEL_LIMIT else text[: KAKAO_QUICK_REPLY_LABEL_LIMIT - 1] + "…"
        replies.append({"label": label, "action": "message", "messageText": text})
    return replies


def build_callback_payload(content: str, followups: list[str] | None = None) -> dict:
    """LLM 응답 → 카카오 콜백 응답 JSON."""
    template: dict = {"outputs": to_simple_text_outputs(content)}
    quick = to_quick_replies(followups)
    if quick:
        template["quickReplies"] = quick
    return {"version": "2.0", "template": template}


def fallback_payload(text: str = "죄송합니다. 일시적인 오류로 답변을 가져오지 못했어요. 잠시 후 다시 시도해 주세요.") -> dict:
    return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": text}}]}}


async def send_callback(url: str, payload: dict, timeout: float = 5.0) -> bool:
    """콜백 URL 로 응답 POST. 성공 True. 1회성이므로 실패해도 재시도 안 함(로깅만)."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("카카오 콜백 전송 실패: %s", e)
        return False
