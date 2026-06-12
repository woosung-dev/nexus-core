# 위기 신호 감지·per-turn 지시문 주입·차단 고정문 — 위기 대응 4원칙의 코드 레벨 구현 (P0)
"""
위기·민감 대응의 코드 레벨 안전장치.

설계 원칙 (exports/crisis_rule_2026-06-12 검증 + 2026-06-12 사용자 확정):
- 키워드는 "후보 신호"일 뿐 — 자동 차단/고정문 전환에 쓰지 않는다.
  감지 시 해당 턴에만 CRISIS_DIRECTIVE 를 시스템 프롬프트에 덧붙여
  LLM 이 확인 단계를 거친 생성형 응답을 유지하게 한다.
  (영구 프롬프트 append 는 3회 A/B 검증 모두 불합격 — 지시 부하·범위 침범)
- 구체 전화번호·기관명·URL 은 어느 경로에서도 제시하지 않는다 (사용자 결정).
  지시문 금지만으로는 환각 번호를 막을 수 없어 strip_phone_sentences 가
  코드 단에서 번호 포함 문장을 제거한다 (일본 사례: 잘못된 핫라인 안내가 더 위험).
- 검수 고정문(BLOCKED_FALLBACK_MESSAGE)은 시스템 실패(세이프티 차단) 시에만 사용.
"""

import logging
import re

logger = logging.getLogger(__name__)

# 위기 "후보 신호" 키워드 — 단순 substring 매칭, recall 우선.
# 오탐 비용은 지시문 1회 주입 + 해당 턴 스트림 버퍼링뿐이므로 허용
# (예: "네 말이 맞았어"의 "맞았", 일반 명사로서의 "폭력").
CRISIS_KEYWORDS: tuple[str, ...] = (
    # 자살·자해
    "자살",
    "자해",
    "죽고 싶",
    "죽고싶",
    "죽을래",
    "죽어버리",
    "목숨을 끊",
    "살기 싫",
    "살기싫",
    "살고 싶지 않",
    "극단적 선택",
    "극단적선택",
    "유서",
    # 폭력·학대
    "폭행",
    "폭력",
    "학대",
    "맞았",
    "때렸",
    "감금",
    "협박",
    "스토킹",
    "가정폭력",
    "데이트폭력",
    "괴롭힘",
    # 성폭력
    "성폭행",
    "성폭력",
    "강간",
    "성추행",
    "성희롱",
    "몰카",
    "불법촬영",
    "불법 촬영",
)


def detect_crisis_signal(message: str) -> str | None:
    """위기 후보 신호 키워드를 찾는다. 매칭된 첫 키워드(로깅용) 또는 None.

    자동 차단/고정문 전환에 쓰지 말 것 — per-turn 지시문 주입 트리거 전용.
    """
    for keyword in CRISIS_KEYWORDS:
        if keyword in message:
            return keyword
    return None


# 위기 대응 지시는 2026-06-12 결정으로 코드 per-turn 주입에서 **봇 시스템 프롬프트 본문**으로 이관됨
# (관리자 페이지 편집 대상). 위기(급성)는 각 봇 '위기 — 안전 최우선' 섹션, 관계·일상 갈등의 제3자 절제는
# Edit A(관계 응답 본문)에 통합. 코드는 감지(detect)·번호 필터(strip)·차단 폴백만 담당한다.

# 세이프티 차단(시스템 실패) 시에만 사용하는 검수 고정문 — 일반 content 로 전달·저장.
# 차단은 자살·강간 등 급성 위기 질문에서 자주 발생하므로, 사용자 결정(2026-06-12: 급성 위기는
# 검증된 고정 번호 유지)에 따라 검증 핫라인을 포함한다. strip 은 고정문에 적용되지 않는다.
BLOCKED_FALLBACK_MESSAGE = """방금 주신 말씀에는 자동으로 답변을 만들어 드리기가 어려워요. 불편을 드려 죄송합니다.

혹시 지금 많이 힘들거나 위험한 상황이시라면, 혼자 견디지 마세요. 24시간 언제든 도움받을 수 있는 곳이 있어요 \
— 자살예방 상담전화 109, 정신건강 위기상담 1577-0199로 지금 연락하실 수 있고, 당장 위험이 임박했다면 \
112(경찰)·119(구급)로 즉시 도움을 요청해 주세요. 곁에 믿을 수 있는 분이 있다면 지금 함께 있어 달라고 해주세요.

급한 상황이 아니시라면, 표현을 조금 바꿔 다시 질문해 주셔도 좋아요."""


# 완전한 전화번호 — 0 으로 시작하는 국내 번호(구분자 유무 모두), 일반 대시 표기,
# 1577-0199 형 핫라인. 연도("2026년")·기간("3개월") 같은 일반 숫자는 비매칭.
_FULL_PHONE_RE = re.compile(
    r"(?<!\d)(?:"
    r"0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}"  # 010-1234-5678 / 02-345-6789 / 01012345678
    r"|\d{2,4}-\d{3,4}-\d{4}"  # 일반 대시 3그룹 표기
    r"|1[3-8]\d{2}-\d{4}"  # 1577-0199 형
    r")(?!\d)"
)
# 단축번호(112/109/119, 1366/1388 등). 1[3-8]xx 만 허용해 연도 19xx/20xx 와 충돌 방지.
# 한글 조사("1366으로")가 바로 붙는 경우가 많아 \b 대신 숫자 경계만 본다.
_SHORT_CODE_RE = re.compile(r"(?<!\d)1(?:\d{2}|[3-8]\d{2})(?!\d)")
# 단축번호는 같은 문장에 전화 문맥어가 있을 때만 번호로 간주 (오탐 억제).
_PHONE_CONTEXT_RE = re.compile(r"전화|신고|상담|긴급|연락|핫라인|콜센터")
# 문장 분리 — 종결부호 뒤 공백 기준 (줄 단위로 먼저 나눈 뒤 적용).
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")


# 급성 위기에 한해 노출이 허용되는 검증된 고정 핫라인 (2026-06-12 사용자 결정).
# strip 은 이 번호들은 통과시키고, 그 외(환각·미검증) 번호 문장만 제거한다.
_VERIFIED_CRISIS_NUMBERS = ("1577-0199", "109", "112", "119", "1366", "1388", "1577")


def _strip_verified(sentence: str) -> str:
    """검증된 핫라인 번호를 문장에서 제거(긴 표기 우선) — 남은 번호만 미검증으로 판정하기 위함."""
    for v in _VERIFIED_CRISIS_NUMBERS:
        sentence = sentence.replace(v, "")
    return sentence


def _contains_unverified_phone(sentence: str) -> bool:
    """검증 핫라인을 제외하고도 전화번호 패턴이 남으면 True(=환각/미검증 번호)."""
    cleaned = _strip_verified(sentence)
    if _FULL_PHONE_RE.search(cleaned):
        return True
    return bool(_SHORT_CODE_RE.search(cleaned) and _PHONE_CONTEXT_RE.search(cleaned))


def strip_phone_sentences(text: str) -> tuple[str, list[str]]:
    """미검증(환각) 전화번호가 든 문장을 제거한다. (필터된 텍스트, 제거된 문장 목록) 반환.

    위기 턴 응답 후처리 — 검증된 위기 핫라인(109·1577-0199·112·119 등)은 보존하고,
    봇이 지어낸 잘못된 번호만 사용자에게 도달하기 전에 코드 단에서 차단한다(일본 사례: 오안내가 더 위험).
    """
    removed: list[str] = []
    out_lines: list[str] = []
    for line in text.split("\n"):
        sentences = _SENTENCE_SPLIT_RE.split(line)
        flags = [_contains_unverified_phone(s) for s in sentences]
        if not any(flags):
            out_lines.append(line)  # 제거가 없으면 원문 그대로 (공백 보존)
            continue
        removed.extend(s.strip() for s, f in zip(sentences, flags) if f)
        kept = [s for s, f in zip(sentences, flags) if not f]
        out_lines.append(" ".join(kept).strip())
    if removed:
        logger.warning("crisis phone filter — removed=%d sentences=%s", len(removed), removed)
    return "\n".join(out_lines), removed
