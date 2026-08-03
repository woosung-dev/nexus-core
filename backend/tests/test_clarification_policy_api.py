from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.endpoints.admin import bots as admin_bots
from app.core.database import get_session
from app.main import app
from app.schemas.clarification import (
    ClarificationDiagnostics,
    ClarificationPreviewResponse,
    ClarificationQuestion,
)


async def _session_override():
    yield SimpleNamespace()


def _policy_payload():
    return {
        "enabled": True,
        "rules": [
            {
                "id": "refund",
                "name": "환불 확인",
                "enabled": True,
                "priority": 100,
                "request_examples": ["환불 가능한가요?", "환불이 되나요?"],
                "why_ask": "유형에 따라 기준이 달라집니다.",
                "document_refs": [{"document_id": "doc-1", "label": "규정집 p.52"}],
                "required_slots": [
                    {
                        "id": "type",
                        "label": "유형",
                        "question": "어떤 유형인가요?",
                        "selection_mode": "single",
                        "options": [
                            {"id": "first", "label": "1세"},
                            {"id": "second", "label": "2세"},
                        ],
                        "allow_custom": False,
                    }
                ],
                "when_unknown": "ask",
            }
        ],
    }


def test_admin_policy_test_evaluates_unsaved_policy_without_persisting(monkeypatch):
    calls = []

    async def fake_get_bot(_session, bot_id):
        return SimpleNamespace(id=bot_id, llm_model="gemini-3.5-flash-lite")

    async def fake_validate(bot, policy):
        calls.append((bot.id, policy))

    async def fake_live_decision(*_args, **kwargs):
        assert kwargs["policy_override"].enabled is True
        return ClarificationPreviewResponse(
            status="ask",
            source="live",
            questions=[
                ClarificationQuestion(
                    id="type",
                    question="어떤 유형인가요?",
                    options=["1세", "2세"],
                    required=True,
                    policy=True,
                )
            ],
            diagnostics=ClarificationDiagnostics(
                applied_rule_id="refund",
                policy_match_status="matched",
                missing_slot_ids=["type"],
                document_ref_ids=["doc-1"],
            ),
        )

    monkeypatch.setattr(admin_bots.crud_bot, "get_bot", fake_get_bot)
    monkeypatch.setattr(admin_bots, "_validate_clarification_policy", fake_validate)
    monkeypatch.setattr(admin_bots, "live_decision", fake_live_decision)
    app.dependency_overrides[get_session] = _session_override
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/admin/bots/7/clarification-policy/test",
                json={"clarification_policy": _policy_payload(), "message": "환불이 되나요?"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["matched"] is True
    assert body["applied_rule_name"] == "환불 확인"
    assert body["missing_slots"] == ["type"]
    assert body["questions"][0]["question"] == "어떤 유형인가요?"
    assert body["document_refs"] == [{"document_id": "doc-1", "label": "규정집 p.52"}]
    assert calls and calls[0][0] == 7
