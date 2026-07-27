# 문서 업로드의 50MB 경계값을 검증한다.
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile

from app.api.v1.endpoints.admin import bots
from app.core.exceptions import ValidationError


@pytest.mark.asyncio
async def test_document_upload_accepts_50mb_and_rejects_larger(monkeypatch):
    """50MB까지는 업로드하고, 그보다 큰 파일은 RAG 호출 전에 거부한다."""
    storage = SimpleNamespace(upload=AsyncMock())
    rag = SimpleNamespace(upload_document=AsyncMock(return_value="document-id"))

    monkeypatch.setattr(bots.crud_bot, "get_bot", AsyncMock(return_value=SimpleNamespace(llm_model="gemini-2.5-flash")))
    monkeypatch.setattr(bots, "get_settings", lambda: SimpleNamespace(MAX_UPLOAD_SIZE_MB=50))
    monkeypatch.setattr(bots, "get_rag_service", lambda provider: rag)

    accepted = UploadFile(filename="accepted.pdf", file=io.BytesIO(b"a" * 50 * 1024 * 1024))
    response = await bots.upload_bot_document(bot_id=11, file=accepted, session=None, storage=storage)

    assert response.file_name == "accepted.pdf"
    storage.upload.assert_awaited_once()
    rag.upload_document.assert_awaited_once()

    rejected = UploadFile(filename="rejected.pdf", file=io.BytesIO(b"a" * (50 * 1024 * 1024 + 1)))
    with pytest.raises(ValidationError, match="파일 크기가 50MB를 초과합니다"):
        await bots.upload_bot_document(bot_id=11, file=rejected, session=None, storage=storage)

