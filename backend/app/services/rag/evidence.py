"""인용 청크에서 '실제 근거가 된 구절'을 뽑아 형광펜 대상으로 채우는 서비스.

왜 LLM 을 한 번 더 부르는가 — 어휘 매칭으로는 안 되기 때문이다. 답변은 규정 원문을
존댓말·요약으로 바꿔 쓰므로 겹침이 낮다. 2026-07-25 D-1 실측에서 세그먼트↔청크 포함도는
평균 36% 였고, 문장 단위 하이라이트가 하나라도 생기는 카드가 25% 뿐이었다(임계 0.4~0.6 전부).
같은 데이터로 LLM 추출 + 원문 검증은 카드 95%, 제안 34개 중 33개 통과였다.

환각이 원리적으로 불가능한 이유 — 모델이 낸 문자열을 그대로 쓰지 않는다. 반환 구절은
청크 원문 위의 위치를 찾는 데만 쓰고, 저장·표시되는 것은 **항상 청크 자신의 문자**다.
실측에서 모델이 '산모'를 '산母'로 한 글자 바꿔 낸 적이 있는데, 스냅이 이를 원문 쪽 표기로
되돌린다(되돌릴 수 없으면 버린다).
"""

import asyncio
import difflib
import json
import logging
import re

from app.schemas.rag import RAGCitation

logger = logging.getLogger(__name__)

# 동시 호출 상한 — 인용 카드가 많은 답변에서 외부 API 를 몰아치지 않도록 제한.
_MAX_CONCURRENCY = 4
# 스냅 허용 하한. 이보다 덜 겹치면 모델이 엉뚱한 걸 냈다고 보고 버린다.
_SNAP_RATIO = 0.8
# 카드 하나에 칠할 구절 수 상한 — 전부 노랗게 칠하면 강조가 아니라 배경이 된다.
_MAX_SPANS = 3
_MIN_SPAN_LEN = 10

_PROMPT = """다음은 챗봇 답변의 일부 구간과, 그 구간이 근거로 삼은 자료 원문이다.

[답변 구간]
{segments}

[자료 원문]
{chunk}

자료 원문에서 위 답변 구간의 근거가 된 부분을 찾아 **원문을 한 글자도 바꾸지 말고 그대로** 복사해 내라.

규칙:
- 원문에 없는 문장을 지어내지 말 것. 반드시 원문에서 복사할 것.
- 근거가 되는 최소 단위로 자를 것(문장 또는 조항 한 개).
- 최대 {max_spans}개까지.
- 근거가 될 만한 부분이 없으면 빈 배열을 반환할 것.

출력은 아래 JSON 형식만:
{{"spans": ["원문 그대로1", "원문 그대로2"]}}"""


def _squash(s: str) -> str:
    """공백을 모두 제거한다. PDF 청크는 줄바꿈이 단어 중간에 들어가 있어 공백 기준 비교가 불가능하다."""
    return re.sub(r"\s+", "", s or "")


def snap_to_source(span: str, content: str) -> str | None:
    """모델이 낸 구절을 청크 원문 위의 실제 문자열로 되돌린다. 못 찾으면 None.

    3단계로 내려간다 — ① 원문 그대로 존재 ② 공백 제거 후 존재(줄바꿈만 다른 경우)
    ③ 문자 정렬로 최선 구간 탐색(오타·표기 흔들림). 어느 경우든 반환값은 content 의 부분문자열이다.
    """
    span = (span or "").strip()
    if len(span) < _MIN_SPAN_LEN or not content:
        return None

    if span in content:
        return span

    # 공백 제거본에서의 위치를 원문 인덱스로 되돌리기 위한 대응표.
    positions = [i for i, ch in enumerate(content) if not ch.isspace()]
    squashed = "".join(content[i] for i in positions)
    target = _squash(span)
    if not target:
        return None

    at = squashed.find(target)
    if at >= 0:
        return content[positions[at]: positions[at + len(target) - 1] + 1]

    # 오타·표기 흔들림 — 정렬해서 겹치는 구간을 찾고, 충분히 겹칠 때만 원문 쪽을 잘라 쓴다.
    matcher = difflib.SequenceMatcher(None, squashed, target, autojunk=False)
    blocks = [b for b in matcher.get_matching_blocks() if b.size > 0]
    if not blocks:
        return None
    matched = sum(b.size for b in blocks)
    if matched / len(target) < _SNAP_RATIO:
        return None
    start, end = blocks[0].a, blocks[-1].a + blocks[-1].size - 1
    if end < start:
        return None
    return content[positions[start]: positions[end] + 1]


def _parse_spans(raw: str) -> list[str]:
    """모델 응답에서 spans 배열을 꺼낸다. 형식이 흔들려도(배열만 오는 등) 견디게 한다."""
    data = json.loads(raw)
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("spans") or []
    else:
        return []
    return [s for s in items if isinstance(s, str)]


async def _extract_one(client, model_name: str, citation: RAGCitation, answer: str) -> None:
    """청크 하나의 근거 구절을 채운다. 실패는 조용히 건너뛴다(인용 표시 자체는 살아 있어야 한다)."""
    from google.genai import types

    content = citation.content or ""
    if not content:
        return
    # 정확 인용이면 그 청크가 뒷받침한 구간만, 근사 인용이면 답변 전체를 질의 대상으로 삼는다.
    query = "\n".join(f"- {s}" for s in citation.segments) or (answer or "")[:1500]
    if not query.strip():
        return

    try:
        resp = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=model_name,
                contents=_PROMPT.format(segments=query, chunk=content, max_spans=_MAX_SPANS),
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=1024,
                    response_mime_type="application/json",
                ),
            ),
            timeout=30,
        )
        spans = _parse_spans(resp.text or "")
    except Exception as e:
        logger.warning("근거 추출 실패 title=%s: %s", citation.title, e)
        return

    snapped: list[str] = []
    for s in spans[:_MAX_SPANS]:
        hit = snap_to_source(s, content)
        if hit and hit not in snapped:
            snapped.append(hit)
    citation.evidence = snapped


async def fill_evidence(
    client, model_name: str, citations: list[RAGCitation], answer: str
) -> int:
    """citations 를 제자리에서 채우고, 근거 구절이 하나라도 붙은 청크 수를 돌려준다."""
    targets = [c for c in citations if c.content]
    if not targets:
        return 0

    sem = asyncio.Semaphore(_MAX_CONCURRENCY)

    async def guarded(c: RAGCitation) -> None:
        async with sem:
            await _extract_one(client, model_name, c, answer)

    await asyncio.gather(*(guarded(c) for c in targets))
    return sum(1 for c in targets if c.evidence)
