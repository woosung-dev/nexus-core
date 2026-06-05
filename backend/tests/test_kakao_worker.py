# 워커 fallback 경로 유닛 테스트 (DB 없이 _build_answer 모킹)
import pytest

from app.core.config import get_settings
from app.services import kakao_worker


@pytest.mark.asyncio
async def test_fallback_sent_once_on_failure(monkeypatch):
    monkeypatch.setattr(get_settings(), "KAKAO_CALLBACK_ALLOWED_HOSTS", ".kakao.com")

    async def boom(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(kakao_worker, "_build_answer", boom)

    sent = []

    async def fake_send(url, payload, timeout=5.0):
        sent.append((url, payload))
        return True

    monkeypatch.setattr(kakao_worker.kakao_service, "send_callback", fake_send)

    await kakao_worker.process_kakao_callback("b1", "u1", "안녕", "https://x.kakao.com/cb")

    assert len(sent) == 1
    assert sent[0][0] == "https://x.kakao.com/cb"
    # fallback 은 simpleText 하나
    assert sent[0][1]["template"]["outputs"][0]["simpleText"]["text"]


@pytest.mark.asyncio
async def test_fallback_blocked_when_host_not_allowed(monkeypatch):
    monkeypatch.setattr(get_settings(), "KAKAO_CALLBACK_ALLOWED_HOSTS", ".kakao.com")

    async def boom(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(kakao_worker, "_build_answer", boom)

    sent = []

    async def fake_send(url, payload, timeout=5.0):
        sent.append((url, payload))
        return True

    monkeypatch.setattr(kakao_worker.kakao_service, "send_callback", fake_send)

    await kakao_worker.process_kakao_callback("b1", "u1", "안녕", "https://evil.example.com/cb")

    assert sent == []  # SSRF 차단 → fallback 도 전송 안 함
