# 핸들러: 즉시 useCallback 반환 / 헤더 인증 / callbackUrl 누락 동기 안내
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services import kakao_worker

VALID = {
    "userRequest": {
        "utterance": "안녕",
        "user": {"id": "u1"},
        "callbackUrl": "https://bot-api.kakao.com/callback/x",
    },
    "bot": {"id": "b1"},
}


def _patch_worker(monkeypatch):
    captured = {}

    async def fake(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(kakao_worker, "process_kakao_callback", fake)
    return captured


def test_returns_use_callback_immediately(monkeypatch):
    monkeypatch.setattr(get_settings(), "KAKAO_SKILL_SECRET", None)
    captured = _patch_worker(monkeypatch)
    client = TestClient(app)
    resp = client.post("/api/v1/kakao/callback", json=VALID)
    assert resp.status_code == 200
    assert resp.json()["useCallback"] is True
    assert captured["kakao_bot_id"] == "b1"
    assert captured["bot_user_key"] == "u1"
    assert captured["callback_url"].endswith("/x")


def test_rejects_bad_secret(monkeypatch):
    monkeypatch.setattr(get_settings(), "KAKAO_SKILL_SECRET", "topsecret")
    _patch_worker(monkeypatch)
    client = TestClient(app)
    resp = client.post("/api/v1/kakao/callback", json=VALID)  # 헤더 없음
    assert resp.status_code == 401


def test_accepts_good_secret(monkeypatch):
    monkeypatch.setattr(get_settings(), "KAKAO_SKILL_SECRET", "topsecret")
    _patch_worker(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/api/v1/kakao/callback", json=VALID, headers={"X-Kakao-Skill-Secret": "topsecret"}
    )
    assert resp.status_code == 200
    assert resp.json()["useCallback"] is True


def test_missing_callback_url_returns_sync_text(monkeypatch):
    monkeypatch.setattr(get_settings(), "KAKAO_SKILL_SECRET", None)
    captured = _patch_worker(monkeypatch)
    client = TestClient(app)
    payload = {"userRequest": {"utterance": "안녕", "user": {"id": "u1"}}, "bot": {"id": "b1"}}
    resp = client.post("/api/v1/kakao/callback", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "useCallback" not in body
    assert body["template"]["outputs"][0]["simpleText"]["text"]
    assert captured == {}  # 워커 미호출
