# BaseRAGService.replace_document 안전 교체 로직 유닛 테스트 (Gemini API 불요, 인메모리 페이크)
import pytest

from app.schemas.rag import DocumentInfo, RAGResponse
from app.services.rag.base import BaseRAGService


class FakeRAG(BaseRAGService):
    """list/upload/delete 만 인메모리로 구현한 페이크. replace_document 는 base 상속분을 검증."""

    def __init__(self) -> None:
        self._docs: list[dict] = []  # {"file_id", "display_name"}
        self._counter = 0
        self._fail_upload = False
        self._fail_delete_ids: set[str] = set()

    async def ensure_store(self, bot_id: int | None = None) -> str:
        return "fake-store"

    async def upload_document(self, bot_id, file_data, filename, display_name, mime_type=None) -> str:
        if self._fail_upload:
            raise RuntimeError("업로드 실패(인덱싱 에러 시뮬레이션)")
        self._counter += 1
        self._docs.append({"file_id": f"f{self._counter}", "display_name": display_name})
        return display_name

    async def list_documents(self, bot_id) -> list[DocumentInfo]:
        return [DocumentInfo(file_id=d["file_id"], display_name=d["display_name"]) for d in self._docs]

    async def delete_document(self, bot_id, file_id) -> None:
        if file_id in self._fail_delete_ids:
            raise RuntimeError("삭제 실패 시뮬레이션")
        before = len(self._docs)
        self._docs = [d for d in self._docs if d["file_id"] != file_id]
        if len(self._docs) == before:
            raise ValueError(f"문서 없음: {file_id}")

    async def generate_with_rag(self, *a, **k) -> RAGResponse:
        return RAGResponse(answer="")

    async def generate_stream_with_rag(self, *a, **k):
        yield ""


async def test_replace_collapses_duplicates_to_one():
    """8배 중복(동일 이름 N건)을 replace 1회로 1건으로 수렴."""
    rag = FakeRAG()
    for _ in range(8):  # 8배 중복 재현
        await rag.upload_document(bot_id=5, file_data=b"v1", filename="규정.md", display_name="규정.md")
    assert len(await rag.list_documents(5)) == 8

    await rag.replace_document(bot_id=5, file_data=b"v2", filename="규정.md", display_name="규정.md")
    docs = await rag.list_documents(5)
    assert len(docs) == 1
    assert docs[0].display_name == "규정.md"


async def test_replace_preserves_old_on_upload_failure():
    """업로드 실패 시 구버전 삭제 안 됨 → 라이브 문서 소실 방지(codex P1)."""
    rag = FakeRAG()
    await rag.upload_document(bot_id=5, file_data=b"v1", filename="규정.md", display_name="규정.md")
    rag._fail_upload = True

    with pytest.raises(RuntimeError):
        await rag.replace_document(bot_id=5, file_data=b"v2", filename="규정.md", display_name="규정.md")

    docs = await rag.list_documents(5)
    assert len(docs) == 1  # 구버전 그대로 보존


async def test_replace_only_targets_same_display_name():
    """다른 이름 문서는 건드리지 않는다."""
    rag = FakeRAG()
    await rag.upload_document(bot_id=5, file_data=b"a", filename="A.md", display_name="A.md")
    await rag.upload_document(bot_id=5, file_data=b"b", filename="B.md", display_name="B.md")

    await rag.replace_document(bot_id=5, file_data=b"a2", filename="A.md", display_name="A.md")
    docs = await rag.list_documents(5)
    assert sorted(d.display_name for d in docs) == ["A.md", "B.md"]
    assert sum(1 for d in docs if d.display_name == "A.md") == 1


async def test_replace_with_no_existing_just_adds():
    """기존 동일 이름이 없으면 그냥 추가(삭제 시도 없음)."""
    rag = FakeRAG()
    await rag.replace_document(bot_id=5, file_data=b"v1", filename="새문서.md", display_name="새문서.md")
    assert len(await rag.list_documents(5)) == 1


async def test_replace_survives_delete_failure():
    """구버전 삭제 실패는 치명 아님(예외 없이 완료, 중복 잔존 가능)."""
    rag = FakeRAG()
    await rag.upload_document(bot_id=5, file_data=b"v1", filename="규정.md", display_name="규정.md")  # f1
    rag._fail_delete_ids = {"f1"}

    await rag.replace_document(bot_id=5, file_data=b"v2", filename="규정.md", display_name="규정.md")
    docs = await rag.list_documents(5)
    assert len(docs) == 2  # f1 삭제 실패 → 신규 + f1 잔존(예외 없음)
