# followups 파서(_split_answer_and_followups) 견고화 단위 테스트 — 내부 마커 노출 0건 검증
from app.services.rag.gemini import _split_answer_and_followups


def _no_marker_leak(body: str) -> bool:
    low = body.lower()
    return ("followups" not in low) and ("[followup_instruction]" not in low)


def test_wellformed_block_extracts_three_and_cleans_body():
    raw = "본문 답변입니다.\n\n<followups>\n질문1 알려줘\n질문2 뭐야?\n질문3 어떻게 해?\n</followups>"
    body, fu = _split_answer_and_followups(raw)
    assert body == "본문 답변입니다."
    assert fu == ["질문1 알려줘", "질문2 뭐야?", "질문3 어떻게 해?"]
    assert _no_marker_leak(body)


def test_missing_closing_tag_does_not_leak():
    # 닫는 태그 누락 — 기존 정규식이면 본문에 <followups> 가 그대로 노출되던 케이스
    raw = "본문이다.\n\n<followups>\n축복 절차 알려줘\n매칭 방법 뭐야?\n서류 어떻게 준비해?"
    body, fu = _split_answer_and_followups(raw)
    assert _no_marker_leak(body)
    assert body.startswith("본문이다.")
    assert len(fu) == 3


def test_tag_whitespace_and_variant_handled():
    for tag_open, tag_close in [("< followups >", "</ followups >"), ("<follow_ups>", "</follow_ups>"), ("<follow-ups>", "</follow-ups>")]:
        raw = f"답변.\n{tag_open}\n첫째 질문\n둘째 질문\n{tag_close}"
        body, fu = _split_answer_and_followups(raw)
        assert _no_marker_leak(body), f"노출됨: {tag_open}"
        assert "첫째 질문" in fu


def test_code_fence_wrapped_block_no_backtick_followups():
    raw = "답변.\n\n<followups>\n```\n질문 하나\n질문 둘\n질문 셋\n```\n</followups>"
    body, fu = _split_answer_and_followups(raw)
    assert _no_marker_leak(body)
    assert "```" not in "".join(fu)  # 코드펜스가 followup 으로 새어들지 않음
    assert fu == ["질문 하나", "질문 둘", "질문 셋"]


def test_list_markers_stripped_but_number_in_word_preserved():
    raw = "답변.\n<followups>\n1. 축복 절차 알려줘\n- 매칭 방법 뭐야?\n• 3일 행사가 뭐야\n</followups>"
    body, fu = _split_answer_and_followups(raw)
    assert fu == ["축복 절차 알려줘", "매칭 방법 뭐야?", "3일 행사가 뭐야"]  # "3일" 의 3 보존


def test_no_block_leaves_body_and_strips_citation_markers():
    raw = "축복 절차는 다음과 같습니다 [1.2, 1.5]. 자세한 내용입니다."
    body, fu = _split_answer_and_followups(raw)
    assert fu == []
    assert "[1.2, 1.5]" not in body
    assert body.startswith("축복 절차는 다음과 같습니다")


def test_residue_safety_net_strips_stray_marker():
    # 모델이 지시문을 일부 echo 한 케이스 — 잔여 토큰이라도 노출 금지
    raw = "본문.\n[FOLLOWUP_INSTRUCTION]\n<followups>\n질문 하나만\n</followups>"
    body, fu = _split_answer_and_followups(raw)
    assert _no_marker_leak(body)
    assert fu == ["질문 하나만"]


def test_empty_input():
    assert _split_answer_and_followups("") == ("", [])
