"""되묻기 규칙 v2 가 표적 문항에 걸리는지 — LLM 호출 0.

`match_policy_rule` 만 돌린다. 규칙 매칭은 「질문 대 관리자 예시질문」이라는 어휘 비교라
모델이 필요 없다. 이 파일이 지키는 것은 **배선이 실제로 쓰는 그 함수**다 — 관리자 화면의
「테스트하기」는 `live_decision` 이라 LLM 이 규칙을 고르는 다른 경로다.

표적은 45문항 실측(`exports/clarify_eval/results.json`)에서 판정기가 켜진 6건이다.
exports/ 는 gitignore 라 질문 원문을 여기 박아 둔다.

`MIN_SCORE` 를 왜 15 로 두는지는 `docs/architecture/clarification-policy-v2-2026-08-10.json`
의 `_note` 에 스윕 표가 있다. 요지: 0 이면 #39(축복정리)가 자격 규칙에 10.94 로 잘못 걸리고,
15 면 6/6 이다. n=6 스윕이라 판정을 다시 돌리면 재스윕해야 한다.
"""

import json
from pathlib import Path

import pytest

from app.schemas.clarification_policy import (
    ClarificationPolicy,
    ClarificationPolicyDocumentRef,
    validate_active_policy,
)
from app.services.clarification_trigger import match_policy_rule

POLICY_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "architecture"
    / "clarification-policy-v2-2026-08-10.json"
)

MIN_SCORE = 15.0

# 판정 양성 6건. None 은 「걸리는 규칙이 없어야 한다」 = handoff 가 맞는 문항이다.
TARGETS = [
    (33, "2세 가정 12일 가정출발의식 절차가 뭐야?", "family-start-12day"),
    (34, "2세도 가정출발 하기전에 해야되는 의식이 있어?", "family-start-pre-rite"),
    (
        18,
        "저는 축복자녀이고 1세 식구와 교제 중입니다. 둘 다 순결을 지켜왔다면 "
        "2세-1세 축복으로 준비할 수 있나요?",
        "child-first-gen-eligibility",
    ),
    (45, "B4U 등업 기준이 뭐야?", "b4u-tier"),
    (36, "축복정리 과정은 어떻게 되나요?", None),
    (
        39,
        "축복 받고 1년도 안되었는데 상대가 성화했습니다. 축복정리 후 재축복 받을 수 "
        "있을가요? 자녀도 없습니다.",
        None,
    ),
]


@pytest.fixture(scope="module")
def policy() -> ClarificationPolicy:
    return ClarificationPolicy.model_validate(json.loads(POLICY_PATH.read_text(encoding="utf-8")))


@pytest.mark.parametrize(("number", "question", "expected"), TARGETS, ids=lambda v: str(v))
def test_target_question_matches_its_rule(policy, number, question, expected):
    rule, score = match_policy_rule(question, policy, min_score=MIN_SCORE)
    matched = rule.id if rule else None
    assert matched == expected, f"#{number} → {matched} (BM25 {score:.2f}), 기대 {expected}"


def test_rules_would_pass_admin_validation_except_document_refs(policy):
    """관리자 저장 규칙(예시 2~5개·슬롯 1~3개·선택지 2~5개)을 지키는지.

    `document_refs` 만 비어 있다 — 대상 봇이 `lexical` 이라 File Search 스토어가 없고,
    어휘 경로의 `decide()` 는 이 필드를 읽지 않는다. 그 한 가지만 빼고 검사한다.
    """
    for rule in policy.rules:
        assert not rule.document_refs, "document_refs 를 채웠다면 이 테스트를 갱신하라"
        rule.document_refs = [ClarificationPolicyDocumentRef(document_id="stub", label="stub")]
    validate_active_policy(policy, {"stub"})
