from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.endpoints import clarification_preview
from app.core.database import get_session
from app.main import app
from app.models.bot import Bot


async def _preview_user_override():
    return SimpleNamespace(id=1)


async def _session_override():
    yield SimpleNamespace()


def test_preview_is_closed_outside_the_explicit_prototype_environment(monkeypatch):
    monkeypatch.setattr(
        clarification_preview,
        "get_settings",
        lambda: SimpleNamespace(
            CLARIFICATION_PROTOTYPE_ENABLED=False,
            CLARIFICATION_PROTOTYPE_DEV_AUTH_BYPASS=False,
        ),
    )
    app.dependency_overrides[clarification_preview.get_preview_user] = _preview_user_override
    app.dependency_overrides[get_session] = _session_override
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clarification-preview",
                json={
                    "bot_id": 7,
                    "message": "우리 서비스에 예약 기능을 넣고 싶어요.",
                    "mode": "fixture",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "활성화" in response.json()["message"]


def test_fixture_preview_is_authenticated_and_does_not_use_chat_persistence(monkeypatch):
    calls = []

    async def fake_get_active_bot(session, bot_id):
        calls.append((session, bot_id))
        return Bot(id=bot_id, name="파일럿", description="test")

    monkeypatch.setattr(clarification_preview.crud_bot, "get_active_bot", fake_get_active_bot)
    monkeypatch.setattr(
        clarification_preview,
        "get_settings",
        lambda: SimpleNamespace(
            CLARIFICATION_PROTOTYPE_ENABLED=True,
            CLARIFICATION_PROTOTYPE_DEV_AUTH_BYPASS=False,
        ),
    )
    app.dependency_overrides[clarification_preview.get_preview_user] = _preview_user_override
    app.dependency_overrides[get_session] = _session_override
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clarification-preview",
                json={
                    "bot_id": 7,
                    "message": "우리 서비스에 예약 기능을 넣고 싶어요.",
                    "mode": "fixture",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ask"
    assert len(response.json()["questions"]) == 3
    assert calls and calls[0][1] == 7


def test_live_preview_requires_the_per_bot_pilot_toggle(monkeypatch):
    async def fake_get_active_bot(_session, bot_id):
        return Bot(id=bot_id, name="일반 봇", description="test", clarify_enabled=False)

    monkeypatch.setattr(clarification_preview.crud_bot, "get_active_bot", fake_get_active_bot)
    monkeypatch.setattr(
        clarification_preview,
        "get_settings",
        lambda: SimpleNamespace(
            CLARIFICATION_PROTOTYPE_ENABLED=True,
            CLARIFICATION_PROTOTYPE_DEV_AUTH_BYPASS=False,
        ),
    )
    app.dependency_overrides[clarification_preview.get_preview_user] = _preview_user_override
    app.dependency_overrides[get_session] = _session_override
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clarification-preview",
                json={
                    "bot_id": 7,
                    "message": "우리 서비스에 예약 기능을 넣고 싶어요.",
                    "mode": "live",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "파일럿" in response.json()["message"]


def test_dev_bypass_allows_the_fixed_bot_and_active_local_test_bots_without_a_login(monkeypatch):
    async def fake_get_active_bot(_session, bot_id):
        return Bot(id=bot_id, name="로컬 테스트 봇", description="test")

    monkeypatch.setattr(clarification_preview.crud_bot, "get_active_bot", fake_get_active_bot)
    monkeypatch.setattr(
        clarification_preview,
        "get_settings",
        lambda: SimpleNamespace(
            CLARIFICATION_PROTOTYPE_ENABLED=True,
            CLARIFICATION_PROTOTYPE_DEV_AUTH_BYPASS=True,
        ),
    )
    app.dependency_overrides[get_session] = _session_override
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clarification-preview",
                json={
                    "bot_id": 0,
                    "message": "우리 서비스에 예약 기능을 넣고 싶어요.",
                    "mode": "fixture",
                },
            )
            local_bot_response = client.post(
                "/api/v1/clarification-preview",
                json={
                    "bot_id": 7,
                    "message": "우리 서비스에 예약 기능을 넣고 싶어요.",
                    "mode": "fixture",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["source"] == "fixture"
    assert local_bot_response.status_code == 200
    assert local_bot_response.json()["source"] == "fixture"


def test_rag_answer_uses_the_selected_bot_without_creating_a_chat(monkeypatch):
    calls = []

    async def fake_get_active_bot(_session, bot_id):
        return Bot(
            id=bot_id,
            name="RAG 테스트 봇",
            description="test",
            use_rag=True,
            llm_model="gemini-3.1-flash-lite",
            system_prompt="문서를 근거로 답하세요.",
        )

    class FakeRAG:
        async def generate_with_rag(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                answer="문서 기반 테스트 답변입니다.",
                citations=[],
                followups=["관련 조건도 확인할까요?"],
            )

    monkeypatch.setattr(clarification_preview.crud_bot, "get_active_bot", fake_get_active_bot)
    monkeypatch.setattr(clarification_preview, "get_rag_service", lambda **_kwargs: FakeRAG())
    monkeypatch.setattr(
        clarification_preview,
        "get_settings",
        lambda: SimpleNamespace(
            CLARIFICATION_PROTOTYPE_ENABLED=True,
            CLARIFICATION_PROTOTYPE_DEV_AUTH_BYPASS=True,
        ),
    )
    app.dependency_overrides[get_session] = _session_override
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clarification-preview/answer",
                json={
                    "bot_id": 7,
                    "message": (
                        "[요청 요약]\n"
                        "- 최초 요청: 축복 신청 서류가 뭔가요\n"
                        "- 어떤 축복인가요: 2세 축복"
                    ),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["source"] == "rag"
    assert response.json()["content"] == "문서 기반 테스트 답변입니다."
    assert len(calls) == 1
    assert calls[0]["bot_id"] == 7
    # 검색 질의는 원질문 + 고른 값이다. 「[요청 요약]」 형식어를 그대로 검색어로 넣으면
    # 되물어 받은 정보가 검색에 반영되기는커녕 형식어가 질의를 오염시킨다(§8 병목).
    assert calls[0]["prompt"] == "축복 신청 서류가 뭔가요 2세 축복"


def _answer_settings():
    return SimpleNamespace(
        CLARIFICATION_PROTOTYPE_ENABLED=True,
        CLARIFICATION_PROTOTYPE_DEV_AUTH_BYPASS=True,
    )


def test_rag_answer_follows_the_bots_retrieval_mode(monkeypatch):
    """라운드0이 어휘 검색을 탔으면 재답변도 어휘 검색을 타야 한다.

    file_search 로 하드코딩돼 있으면 되물어 받은 값이 다른 코퍼스로 조회돼
    지어냄율이 어휘팔 3.4% 가 아니라 file_search 14.2% 쪽으로 되돌아간다.
    """
    calls = []

    async def fake_get_active_bot(_session, bot_id):
        return Bot(
            id=bot_id,
            name="어휘 봇",
            description="test",
            use_rag=True,
            llm_model="gemini-3.5-flash-lite",
            system_prompt="문서를 근거로 답하세요.",
            retrieval_mode="lexical",
        )

    async def fake_answer_with_wiki(**kwargs):
        calls.append(kwargs)
        return (
            SimpleNamespace(answer="어휘 검색 답변", citations=[], followups=[]),
            SimpleNamespace(pages=[], units=[]),
        )

    monkeypatch.setattr(clarification_preview.crud_bot, "get_active_bot", fake_get_active_bot)
    monkeypatch.setattr(clarification_preview, "answer_with_wiki", fake_answer_with_wiki)
    monkeypatch.setattr(clarification_preview, "get_settings", _answer_settings)
    app.dependency_overrides[get_session] = _session_override
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clarification-preview/answer",
                json={
                    "bot_id": 11,
                    "message": "[요청 요약]\n- 최초 요청: 3일행사가 중단됐어요\n- 어디까지: 3일행사 중 중단",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["content"] == "어휘 검색 답변"
    assert len(calls) == 1
    assert calls[0]["context_mode"] == "raw_budget"
    assert calls[0]["question"] == "3일행사가 중단됐어요 3일행사 중 중단"


def test_rag_answer_keeps_the_strict_evidence_gate(monkeypatch):
    """strict 봇은 재답변에서도 직접 인용이 없으면 막혀야 한다."""

    async def fake_get_active_bot(_session, bot_id):
        return Bot(
            id=bot_id,
            name="strict 봇",
            description="test",
            use_rag=True,
            llm_model="gemini-3.5-flash-lite",
            system_prompt="문서를 근거로 답하세요.",
            evidence_policy_mode="strict",
        )

    class FakeRAG:
        async def generate_with_rag(self, **_kwargs):
            return SimpleNamespace(answer="근거 없는 답변", citations=[], followups=["추가 질문"])

    monkeypatch.setattr(clarification_preview.crud_bot, "get_active_bot", fake_get_active_bot)
    monkeypatch.setattr(clarification_preview, "get_rag_service", lambda **_kwargs: FakeRAG())
    monkeypatch.setattr(clarification_preview, "get_settings", _answer_settings)
    app.dependency_overrides[get_session] = _session_override
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clarification-preview/answer",
                json={"bot_id": 7, "message": "[요청 요약]\n- 최초 요청: 서류가 뭔가요"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["content"] == clarification_preview.STRICT_EVIDENCE_MESSAGE
    assert response.json()["followups"] == []
