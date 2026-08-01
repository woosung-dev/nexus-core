"""봇별 strict 모드의 작은 정책 모음.

strict 모드는 답변의 최신성·공식성을 판정하지 않는다. 대신 일반 답변에는 이번
RAG 호출에서 받은 직접 인용을 요구하고, FAQ에는 운영자가 작성한 거절문만 허용한다.
"""

import re

from app.schemas.rag import RAGCitation


STRICT_EVIDENCE_MESSAGE = (
    "확인 가능한 직접 인용 근거가 없어 이 내용은 답변해 드릴 수 없습니다."
)

_REFUSAL_RE = re.compile(
    r"(?:답변|안내|도움).{0,16}(?:드리기|드릴|할).{0,16}(?:어렵|불가|않|못|없)|"
    r"답변할 수 없",
    re.IGNORECASE,
)


def has_direct_citation(citations: list[RAGCitation]) -> bool:
    """근사 백필이 아닌, 이번 RAG 응답의 식별 가능한 인용이 하나 이상인지 확인한다."""
    return any(
        not citation.approximate and bool(citation.title or citation.uri)
        for citation in citations
    )


def is_refusal_faq(answer: str) -> bool:
    """strict 봇에서 허용할 FAQ는 사용자를 안전하게 거절하는 안내문뿐이다."""
    return bool(_REFUSAL_RE.search(answer or ""))
