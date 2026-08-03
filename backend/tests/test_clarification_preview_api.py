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
                    "message": "[요청 요약]\\n- 예약은 회원과 비회원 모두 가능합니다.",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["source"] == "rag"
    assert response.json()["content"] == "문서 기반 테스트 답변입니다."
    assert len(calls) == 1
    assert calls[0]["bot_id"] == 7
    assert calls[0]["prompt"].startswith("[요청 요약]")
