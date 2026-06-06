<!-- 카카오톡 채널 챗봇 연동 구현 계획서 (writing-plans 산출물) -->

# 카카오톡 채널 챗봇 연동 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 nexus-core 봇을 카카오톡 채널 친구추가만으로 Q&A 가능하게 한다. 카카오 i 오픈빌더 스킬 서버 + 콜백 비동기 방식.

**Architecture:** 핸들러가 5초 안에 `useCallback:true`만 반환하고, 백그라운드 워커가 새 DB 세션에서 `ChatService.process_chat_request(stream=False)`로 답변을 만들어 1분 유효 콜백 URL로 1회 POST한다. 봇 식별은 요청 본문 `bot.id`. 카카오 사용자는 JIT 생성, 사용자당 1개 지속 세션. 인바운드 헤더 시크릿 + 아웃바운드 callbackUrl host allowlist로 보안.

**Tech Stack:** FastAPI · SQLModel · asyncpg · Alembic · pydantic-settings · httpx · pytest/pytest-asyncio(uv) · Gemini LLM · (프론트) Next.js + React Query + shadcn/ui

**Spec:** `docs/superpowers/specs/2026-06-05-kakao-channel-chatbot-design.md`

**테스트 전략(확정):** 최소 인프라 + 핵심 유닛. `kakao_service` 순수함수와 핸들러(즉시응답·인증)는 자동 테스트. DB CRUD·워커 통합은 curl + 실채널 수동 검증.

> 모든 명령은 `backend/` 디렉토리에서 실행하며 `.env`가 존재해야 한다(`uv run`이 자동 로드). 프론트는 `frontend-admin/`.

---

## Task 0: pytest 테스트 인프라 부트스트랩

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: dev 의존성 설치**

Run: `cd backend && uv sync`
Expected: pytest, pytest-asyncio, httpx 설치됨.

- [ ] **Step 2: pyproject.toml에 pytest 설정 추가**

`backend/pyproject.toml` 끝에 추가:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 3: 테스트 패키지 생성**

`backend/tests/__init__.py` (빈 파일):

```python
```

`backend/tests/conftest.py`:

```python
# pytest 공용 설정 — 테스트는 backend/ 에서 실행하며 .env 를 로드한다.
```

- [ ] **Step 4: pytest 동작 확인**

Run: `cd backend && uv run pytest --version`
Expected: `pytest 8.x.x` 출력.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/tests/__init__.py backend/tests/conftest.py
git commit -m "test(kakao): pytest 테스트 인프라 부트스트랩"
```

---

## Task 1: 카카오 설정값 추가

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Settings에 카카오 필드 + 허용 host 리스트 추가**

`backend/app/core/config.py`의 `Settings` 클래스에서 `cors_origins_list` computed_field 위에 필드 추가:

```python
    # --- 카카오 채널 챗봇 ---
    KAKAO_SKILL_SECRET: str | None = None
    KAKAO_SKILL_SECRET_HEADER: str = "X-Kakao-Skill-Secret"
    KAKAO_CALLBACK_ALLOWED_HOSTS: str = ".kakao.com"
```

그리고 `cors_origins_list` 아래에 computed_field 추가:

```python
    @computed_field
    @property
    def kakao_callback_allowed_hosts_list(self) -> list[str]:
        """콤마 구분 또는 JSON 배열 → 허용 host suffix 리스트."""
        raw = self.KAKAO_CALLBACK_ALLOWED_HOSTS.strip()
        if raw.startswith("["):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return [h.strip() for h in raw.split(",") if h.strip()]
```

- [ ] **Step 2: import 확인**

`config.py` 상단에 `import json` 이 이미 있음(확인만).

- [ ] **Step 3: 동작 확인**

Run: `cd backend && uv run python -c "from app.core.config import get_settings; print(get_settings().kakao_callback_allowed_hosts_list)"`
Expected: `['.kakao.com']`

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/config.py
git commit -m "feat(kakao): 스킬 시크릿·콜백 host allowlist 설정 추가"
```

---

## Task 2: kakao_service — callbackUrl host 검증 (TDD)

**Files:**
- Create: `backend/app/services/kakao_service.py`
- Create: `backend/tests/test_kakao_service.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_kakao_service.py`:

```python
# kakao_service 순수함수 유닛 테스트
from app.services.kakao_service import is_allowed_callback_host

ALLOWED = [".kakao.com"]


def test_allows_kakao_subdomain():
    assert is_allowed_callback_host("https://bot-api.kakao.com/callback/xyz", ALLOWED) is True


def test_allows_apex_kakao():
    assert is_allowed_callback_host("https://kakao.com/cb", ALLOWED) is True


def test_blocks_other_hosts():
    assert is_allowed_callback_host("https://evil.example.com/x", ALLOWED) is False
    assert is_allowed_callback_host("http://169.254.169.254/latest/meta-data", ALLOWED) is False
    assert is_allowed_callback_host("https://kakao.com.evil.com/x", ALLOWED) is False
    assert is_allowed_callback_host("https://fakekakao.com/x", ALLOWED) is False
    assert is_allowed_callback_host("not a url", ALLOWED) is False
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_kakao_service.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.kakao_service`

- [ ] **Step 3: 최소 구현**

`backend/app/services/kakao_service.py`:

```python
# 카카오 응답 변환 + 콜백 전송을 담당하는 어댑터 서비스 (순수 변환 + httpx)
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _host_matches(host: str, suffix: str) -> bool:
    suffix = suffix.lstrip(".").lower()
    return host == suffix or host.endswith("." + suffix)


def is_allowed_callback_host(url: str, allowed_suffixes: list[str]) -> bool:
    """callbackUrl host 가 허용 도메인(suffix)인지. SSRF 차단용."""
    try:
        host = urlparse(url).hostname
    except ValueError:
        return False
    if not host:
        return False
    host = host.lower()
    return any(_host_matches(host, s) for s in allowed_suffixes)
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_kakao_service.py -v`
Expected: PASS (5 asserts)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/kakao_service.py backend/tests/test_kakao_service.py
git commit -m "feat(kakao): callbackUrl host allowlist 검증(SSRF 차단)"
```

---

## Task 3: kakao_service — 긴 답변 ≤3 말풍선 분할 (TDD)

**Files:**
- Modify: `backend/app/services/kakao_service.py`
- Modify: `backend/tests/test_kakao_service.py`

- [ ] **Step 1: 실패 테스트 추가**

`backend/tests/test_kakao_service.py`에 추가:

```python
from app.services.kakao_service import to_simple_text_outputs


def test_short_text_single_bubble():
    assert to_simple_text_outputs("안녕하세요") == [{"simpleText": {"text": "안녕하세요"}}]


def test_blank_text_fallbacks():
    out = to_simple_text_outputs("   ")
    assert out[0]["simpleText"]["text"] == "응답을 생성하지 못했습니다."


def test_long_text_splits_max_3_and_under_limit():
    long = "이것은 한 문장입니다. " * 400  # 약 4800자
    out = to_simple_text_outputs(long)
    assert 1 <= len(out) <= 3
    for o in out:
        assert len(o["simpleText"]["text"]) <= 1000


def test_unbreakable_overflow_truncates_last_with_ellipsis():
    out = to_simple_text_outputs("가" * 5000)  # 공백 없음 → 3청크, 마지막 …
    assert len(out) == 3
    assert out[-1]["simpleText"]["text"].endswith("…")
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_kakao_service.py -k simple_text -v`
Expected: FAIL — `cannot import name 'to_simple_text_outputs'`

- [ ] **Step 3: 구현 추가**

`backend/app/services/kakao_service.py`에 추가 (상단 import에 `import re` 추가):

```python
import re

KAKAO_SIMPLE_TEXT_LIMIT = 1000
KAKAO_MAX_OUTPUTS = 3


def _find_break(text: str, limit: int) -> int:
    """limit 이내에서 자연스러운 분할 지점(문단/줄/문장/공백)을 찾는다. 없으면 limit."""
    window = text[:limit]
    for sep in ("\n\n", "\n"):
        idx = window.rfind(sep)
        if idx > limit * 0.5:
            return idx + len(sep)
    last_end = -1
    for match in re.finditer(r"[.!?。！？]\s", window):
        last_end = match.end()
    if last_end > limit * 0.5:
        return last_end
    idx = window.rfind(" ")
    if idx > limit * 0.5:
        return idx + 1
    return limit


def _split_text(text: str, limit: int, max_chunks: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining and len(chunks) < max_chunks:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        if len(chunks) == max_chunks - 1:  # 마지막 칸인데 아직 넘침 → 잘라서 …
            chunks.append(remaining[: limit - 1].rstrip() + "…")
            break
        cut = _find_break(remaining, limit)
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return chunks


def to_simple_text_outputs(content: str) -> list[dict]:
    """답변 텍스트를 카카오 outputs(simpleText ≤3개, 각 ≤1000자)로 변환."""
    text = (content or "").strip() or "응답을 생성하지 못했습니다."
    return [{"simpleText": {"text": c}} for c in _split_text(text, KAKAO_SIMPLE_TEXT_LIMIT, KAKAO_MAX_OUTPUTS)]
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_kakao_service.py -v`
Expected: PASS (전체)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/kakao_service.py backend/tests/test_kakao_service.py
git commit -m "feat(kakao): 긴 답변 ≤3 말풍선 분할 변환"
```

---

## Task 4: kakao_service — quickReplies + 페이로드 빌더 (TDD)

**Files:**
- Modify: `backend/app/services/kakao_service.py`
- Modify: `backend/tests/test_kakao_service.py`

- [ ] **Step 1: 실패 테스트 추가**

```python
from app.services.kakao_service import to_quick_replies, build_callback_payload, fallback_payload


def test_quick_replies_cap_10():
    qr = to_quick_replies([f"질문{i}" for i in range(15)])
    assert len(qr) == 10
    assert qr[0] == {"label": "질문0", "action": "message", "messageText": "질문0"}


def test_quick_replies_empty():
    assert to_quick_replies(None) == []
    assert to_quick_replies([]) == []


def test_build_payload_structure():
    payload = build_callback_payload("안녕", ["다시 질문"])
    assert payload["version"] == "2.0"
    assert payload["template"]["outputs"][0]["simpleText"]["text"] == "안녕"
    assert payload["template"]["quickReplies"][0]["messageText"] == "다시 질문"


def test_build_payload_no_quick_replies_key_when_empty():
    payload = build_callback_payload("안녕", [])
    assert "quickReplies" not in payload["template"]


def test_fallback_payload():
    p = fallback_payload()
    assert p["version"] == "2.0"
    assert p["template"]["outputs"][0]["simpleText"]["text"]
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_kakao_service.py -k "quick or payload or fallback" -v`
Expected: FAIL — import 에러.

- [ ] **Step 3: 구현 추가**

`backend/app/services/kakao_service.py`에 추가:

```python
KAKAO_MAX_QUICK_REPLIES = 10
KAKAO_QUICK_REPLY_LABEL_LIMIT = 14  # 라벨 표시 한도(대략) — messageText 는 전체 유지


def to_quick_replies(followups: list[str] | None) -> list[dict]:
    """후속질문 리스트를 quickReplies(≤10)로 변환. messageText 는 전체, label 은 표시용으로 절단."""
    if not followups:
        return []
    replies: list[dict] = []
    for raw in followups[:KAKAO_MAX_QUICK_REPLIES]:
        text = (raw or "").strip()
        if not text:
            continue
        label = text if len(text) <= KAKAO_QUICK_REPLY_LABEL_LIMIT else text[: KAKAO_QUICK_REPLY_LABEL_LIMIT - 1] + "…"
        replies.append({"label": label, "action": "message", "messageText": text})
    return replies


def build_callback_payload(content: str, followups: list[str] | None = None) -> dict:
    """LLM 응답 → 카카오 콜백 응답 JSON."""
    template: dict = {"outputs": to_simple_text_outputs(content)}
    quick = to_quick_replies(followups)
    if quick:
        template["quickReplies"] = quick
    return {"version": "2.0", "template": template}


def fallback_payload(text: str = "죄송합니다. 일시적인 오류로 답변을 가져오지 못했어요. 잠시 후 다시 시도해 주세요.") -> dict:
    return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": text}}]}}
```

> 주의: `test_quick_replies_cap_10`의 `"질문0"`은 14자 이하라 label==messageText. 절단 로직은 긴 후속질문에서만 동작.

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_kakao_service.py -v`
Expected: PASS (전체)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/kakao_service.py backend/tests/test_kakao_service.py
git commit -m "feat(kakao): quickReplies + 콜백 페이로드/폴백 빌더"
```

---

## Task 5: kakao_service — 콜백 전송 (httpx)

**Files:**
- Modify: `backend/app/services/kakao_service.py`

- [ ] **Step 1: send_callback 구현 추가**

`backend/app/services/kakao_service.py`에 추가 (상단에 `import httpx`):

```python
import httpx


async def send_callback(url: str, payload: dict, timeout: float = 5.0) -> bool:
    """콜백 URL 로 응답 POST. 성공 True. 1회성이므로 실패해도 재시도 안 함(로깅만)."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("카카오 콜백 전송 실패: %s", e)
        return False
```

- [ ] **Step 2: import 정상 확인**

Run: `cd backend && uv run python -c "from app.services import kakao_service; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/kakao_service.py
git commit -m "feat(kakao): httpx 콜백 전송 함수"
```

---

## Task 6: 요청/응답 스키마 재작성 (TDD — 422 회귀 차단)

**Files:**
- Modify: `backend/app/schemas/kakao.py`
- Create: `backend/tests/test_kakao_schema.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_kakao_schema.py`:

```python
# 실제 카카오 페이로드 구조 파싱 — 현 스키마(최상위 user 필수)는 여기서 실패한다.
from app.schemas.kakao import KakaoCallbackRequest


def test_parses_real_payload_shape():
    payload = {
        "userRequest": {
            "utterance": "안녕",
            "user": {"id": "abc123", "type": "botUserKey"},
            "callbackUrl": "https://bot-api.kakao.com/callback/xyz",
        },
        "bot": {"id": "bot-123", "name": "테스트봇"},
        "action": {"params": {}},
    }
    req = KakaoCallbackRequest.model_validate(payload)
    assert req.userRequest.user.id == "abc123"
    assert req.userRequest.callbackUrl.endswith("/xyz")
    assert req.bot.id == "bot-123"


def test_callback_url_optional():
    payload = {
        "userRequest": {"utterance": "안녕", "user": {"id": "u1"}},
        "bot": {"id": "b1"},
    }
    req = KakaoCallbackRequest.model_validate(payload)
    assert req.userRequest.callbackUrl is None
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_kakao_schema.py -v`
Expected: FAIL — ValidationError (현 스키마는 최상위 `user` 필수).

- [ ] **Step 3: 스키마 재작성**

`backend/app/schemas/kakao.py` 전체 교체:

```python
"""
카카오톡 i 오픈빌더 스킬 콜백 스키마.
요청은 userRequest 안에 user/callbackUrl 이 들어온다(공식 페이로드 구조).
"""

from pydantic import BaseModel


# --- 요청 ---
class KakaoUser(BaseModel):
    id: str
    type: str | None = None
    properties: dict | None = None


class KakaoUserRequest(BaseModel):
    utterance: str
    user: KakaoUser
    callbackUrl: str | None = None
    lang: str | None = None
    timezone: str | None = None


class KakaoBot(BaseModel):
    id: str
    name: str | None = None


class KakaoCallbackRequest(BaseModel):
    userRequest: KakaoUserRequest
    bot: KakaoBot
    intent: dict | None = None
    action: dict | None = None


# --- 응답(스키마 문서화용; 핸들러/워커는 dict 를 직접 만든다) ---
class KakaoSimpleText(BaseModel):
    text: str


class KakaoOutput(BaseModel):
    simpleText: KakaoSimpleText


class KakaoQuickReply(BaseModel):
    label: str
    action: str = "message"
    messageText: str


class KakaoTemplate(BaseModel):
    outputs: list[KakaoOutput]
    quickReplies: list[KakaoQuickReply] | None = None


class KakaoCallbackResponse(BaseModel):
    version: str = "2.0"
    useCallback: bool | None = None
    template: KakaoTemplate | None = None
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_kakao_schema.py -v`
Expected: PASS (2)

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/kakao.py backend/tests/test_kakao_schema.py
git commit -m "fix(kakao): 요청 스키마를 실제 페이로드 구조로 교정(422 차단)"
```

---

## Task 7: 봇↔카카오봇 매핑 모델

**Files:**
- Create: `backend/app/models/bot_kakao_channel.py`

- [ ] **Step 1: 모델 작성**

`backend/app/models/bot_kakao_channel.py`:

```python
# 오픈빌더 봇(요청 본문 bot.id) ↔ 내부 봇 매핑 모델
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, DateTime, func


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BotKakaoChannel(SQLModel, table=True):
    __tablename__ = "bot_kakao_channels"

    id: int | None = Field(default=None, primary_key=True)
    bot_id: int = Field(foreign_key="bots.id", index=True)
    kakao_bot_id: str = Field(unique=True, index=True, max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        default_factory=get_utc_now,
    )
```

- [ ] **Step 2: import 확인**

Run: `cd backend && uv run python -c "from app.models.bot_kakao_channel import BotKakaoChannel; print(BotKakaoChannel.__tablename__)"`
Expected: `bot_kakao_channels`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/bot_kakao_channel.py
git commit -m "feat(kakao): BotKakaoChannel 매핑 모델"
```

---

## Task 8: Alembic 마이그레이션 (bot_kakao_channels)

**Files:**
- Create: `backend/alembic/versions/<gen>_add_bot_kakao_channels.py` (revision 자동 생성 후 본문 작성)

- [ ] **Step 1: 빈 리비전 생성(올바른 down_revision 확보)**

Run: `cd backend && uv run alembic revision -m "add bot_kakao_channels"`
Expected: `backend/alembic/versions/<hash>_add_bot_kakao_channels.py` 생성. (autogenerate 아님 — 빈 upgrade/downgrade)

- [ ] **Step 2: 생성된 파일의 upgrade/downgrade 작성**

생성된 파일에서 `upgrade()`/`downgrade()`를 아래로 교체. 파일 상단의 `revision`/`down_revision`은 건드리지 않는다. 상단 import에 `import sqlalchemy as sa`, `from alembic import op`가 있는지 확인(없으면 추가).

```python
def upgrade() -> None:
    op.create_table(
        "bot_kakao_channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bots.id"), nullable=False),
        sa.Column("kakao_bot_id", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_bot_kakao_channels_bot_id", "bot_kakao_channels", ["bot_id"])
    op.create_index(
        "ix_bot_kakao_channels_kakao_bot_id",
        "bot_kakao_channels",
        ["kakao_bot_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_bot_kakao_channels_kakao_bot_id", table_name="bot_kakao_channels")
    op.drop_index("ix_bot_kakao_channels_bot_id", table_name="bot_kakao_channels")
    op.drop_table("bot_kakao_channels")
```

- [ ] **Step 3: 마이그레이션 적용**

Run: `cd backend && uv run alembic upgrade head`
Expected: 에러 없이 적용. `bot_kakao_channels` 테이블 생성.

- [ ] **Step 4: 테이블 확인**

Run:
```bash
cd backend && uv run python -c "
import asyncio
from sqlalchemy import text
from app.core.database import async_session
async def main():
    async with async_session() as s:
        r = await s.execute(text(\"SELECT to_regclass('public.bot_kakao_channels')\"))
        print(r.scalar())
asyncio.run(main())
"
```
Expected: `bot_kakao_channels` 출력(테이블 존재). 또는 DB 클라이언트로 `\d bot_kakao_channels`.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(kakao): bot_kakao_channels 마이그레이션"
```

---

## Task 9: 매핑 CRUD

**Files:**
- Create: `backend/app/crud/crud_bot_kakao_channel.py`

- [ ] **Step 1: CRUD 작성**

`backend/app/crud/crud_bot_kakao_channel.py`:

```python
# BotKakaoChannel(오픈빌더 봇 ↔ 내부 봇) CRUD
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.bot_kakao_channel import BotKakaoChannel


async def get_by_kakao_bot_id(session: AsyncSession, kakao_bot_id: str) -> BotKakaoChannel | None:
    result = await session.execute(
        select(BotKakaoChannel).where(BotKakaoChannel.kakao_bot_id == kakao_bot_id)
    )
    return result.scalar_one_or_none()


async def list_by_bot(session: AsyncSession, bot_id: int) -> Sequence[BotKakaoChannel]:
    result = await session.execute(
        select(BotKakaoChannel).where(BotKakaoChannel.bot_id == bot_id)
    )
    return result.scalars().all()


async def create(session: AsyncSession, bot_id: int, kakao_bot_id: str) -> BotKakaoChannel:
    channel = BotKakaoChannel(bot_id=bot_id, kakao_bot_id=kakao_bot_id)
    session.add(channel)
    await session.flush()
    await session.refresh(channel)
    return channel


async def delete(session: AsyncSession, channel: BotKakaoChannel) -> None:
    await session.delete(channel)
    await session.flush()
```

- [ ] **Step 2: import 확인**

Run: `cd backend && uv run python -c "from app.crud import crud_bot_kakao_channel as c; print(hasattr(c,'get_by_kakao_bot_id'))"`
Expected: `True`

- [ ] **Step 3: Commit**

```bash
git add backend/app/crud/crud_bot_kakao_channel.py
git commit -m "feat(kakao): BotKakaoChannel CRUD"
```

---

## Task 10: 카카오 사용자 JIT 생성 (race 처리)

**Files:**
- Modify: `backend/app/crud/crud_user.py`

- [ ] **Step 1: get_or_create_kakao_user 추가**

`backend/app/crud/crud_user.py` 상단 import에 추가: `from sqlalchemy.exc import IntegrityError`. 파일 끝에 함수 추가:

```python
async def get_or_create_kakao_user(
    session: AsyncSession, kakao_bot_id: str, bot_user_key: str
) -> User:
    """
    카카오 사용자를 JIT 생성. 동일 사용자도 봇이 다르면 다른 키이므로 봇 namespace 포함.
    email 은 필수·unique 라 synthetic 값을 만든다. 동시 최초 요청 race 는 재조회로 처리.
    """
    clerk_user_id = f"kakao:{kakao_bot_id}:{bot_user_key}"
    result = await session.execute(select(User).where(User.clerk_user_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        clerk_user_id=clerk_user_id,
        email=f"kakao_{kakao_bot_id}_{bot_user_key}@kakao.local",
        provider="kakao",
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        result = await session.execute(select(User).where(User.clerk_user_id == clerk_user_id))
        user = result.scalar_one()
    return user
```

- [ ] **Step 2: import 확인**

Run: `cd backend && uv run python -c "from app.crud import crud_user; print(hasattr(crud_user,'get_or_create_kakao_user'))"`
Expected: `True`

- [ ] **Step 3: Commit**

```bash
git add backend/app/crud/crud_user.py
git commit -m "feat(kakao): 카카오 사용자 JIT 생성(synthetic email + race)"
```

---

## Task 11: 카카오 지속 세션 get-or-create

**Files:**
- Modify: `backend/app/crud/crud_chat.py`

- [ ] **Step 1: get_or_create_kakao_session 추가**

`backend/app/crud/crud_chat.py` 파일 끝에 추가(`select`, `desc`는 이미 import됨):

```python
async def get_or_create_kakao_session(
    session: AsyncSession, user_id: int, bot_id: int
) -> ChatSession:
    """카카오 사용자당 1개 지속 세션. (user_id, bot_id) 의 최근 세션 재사용, 없으면 생성."""
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .where(ChatSession.bot_id == bot_id)
        .order_by(desc(ChatSession.created_at))
        .limit(1)
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing
    return await create_chat_session(session, user_id=user_id, bot_id=bot_id, title="카카오 대화")
```

- [ ] **Step 2: import 확인**

Run: `cd backend && uv run python -c "from app.crud import crud_chat; print(hasattr(crud_chat,'get_or_create_kakao_session'))"`
Expected: `True`

- [ ] **Step 3: Commit**

```bash
git add backend/app/crud/crud_chat.py
git commit -m "feat(kakao): 카카오 지속 세션 get-or-create"
```

---

## Task 12: 백그라운드 워커

**Files:**
- Create: `backend/app/services/kakao_worker.py`

- [ ] **Step 1: 워커 작성**

`backend/app/services/kakao_worker.py`:

```python
# 카카오 콜백 백그라운드 처리: 새 DB 세션에서 LLM 응답 생성 후 콜백 URL로 1회 전송
import asyncio
import logging

from app.core.config import get_settings
from app.core.database import async_session
from app.crud import crud_bot, crud_bot_kakao_channel, crud_chat, crud_user
from app.models.enums import MessageRole
from app.schemas.chat import ChatCompletionRequest
from app.services import kakao_service
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

WORKER_DEADLINE_SECONDS = 50.0


async def process_kakao_callback(
    kakao_bot_id: str, bot_user_key: str, utterance: str, callback_url: str
) -> None:
    """5초 즉시응답 이후 백그라운드에서 호출됨. 절대 deadline 안에 콜백 전송, 실패 시 fallback."""
    settings = get_settings()
    try:
        await asyncio.wait_for(
            _process(kakao_bot_id, bot_user_key, utterance, callback_url),
            timeout=WORKER_DEADLINE_SECONDS,
        )
    except Exception as e:
        logger.error("카카오 워커 실패(fallback 시도): %s", e)
        if kakao_service.is_allowed_callback_host(
            callback_url, settings.kakao_callback_allowed_hosts_list
        ):
            await kakao_service.send_callback(callback_url, kakao_service.fallback_payload())


async def _process(kakao_bot_id: str, bot_user_key: str, utterance: str, callback_url: str) -> None:
    settings = get_settings()
    async with async_session() as session:
        channel = await crud_bot_kakao_channel.get_by_kakao_bot_id(session, kakao_bot_id)
        if channel is None or not channel.is_active:
            raise ValueError(f"미등록/비활성 카카오 봇: {kakao_bot_id}")

        bot = await crud_bot.get_active_bot(session, channel.bot_id)
        if bot is None:
            raise ValueError(f"비활성 봇: {channel.bot_id}")

        user = await crud_user.get_or_create_kakao_user(session, kakao_bot_id, bot_user_key)
        chat_session = await crud_chat.get_or_create_kakao_session(session, user.id, bot.id)

        # 사용자 메시지 직접 저장(ChatService 는 assistant 만 저장). ChatService 내부 commit 으로 함께 영속화.
        await crud_chat.create_message(
            session=session, session_id=chat_session.id, role=MessageRole.USER, content=utterance
        )

        chat_request = ChatCompletionRequest(
            bot_id=bot.id, message=utterance, session_id=chat_session.id, stream=False, use_rag=True
        )
        response = await ChatService(session=session).process_chat_request(
            request=chat_request, bot=bot, chat_session=chat_session
        )

        if not kakao_service.is_allowed_callback_host(
            callback_url, settings.kakao_callback_allowed_hosts_list
        ):
            logger.error("허용되지 않은 callbackUrl host, 전송 중단: %s", callback_url)
            return

        payload = kakao_service.build_callback_payload(response.content, response.followups)
        await kakao_service.send_callback(callback_url, payload)
```

- [ ] **Step 2: import 확인**

Run: `cd backend && uv run python -c "from app.services import kakao_worker; print(hasattr(kakao_worker,'process_kakao_callback'))"`
Expected: `True`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/kakao_worker.py
git commit -m "feat(kakao): 콜백 백그라운드 워커(새 세션·50초 deadline·fallback)"
```

---

## Task 13: 콜백 핸들러 재작성 (TDD — TestClient)

**Files:**
- Modify: `backend/app/api/v1/endpoints/kakao.py`
- Create: `backend/tests/test_kakao_callback.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_kakao_callback.py`:

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_kakao_callback.py -v`
Expected: FAIL — 현 핸들러는 echo 반환(useCallback 없음, 인증 없음).

- [ ] **Step 3: 핸들러 재작성**

`backend/app/api/v1/endpoints/kakao.py` 전체 교체:

```python
"""
카카오톡 i 오픈빌더 스킬 콜백 엔드포인트.
5초 안에 useCallback:true 만 반환하고, 실제 답변은 백그라운드 워커가 콜백 URL로 전송한다.
"""

import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.schemas.kakao import KakaoCallbackRequest
from app.services import kakao_worker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kakao", tags=["카카오"])


def _waiting_response() -> dict:
    return {"version": "2.0", "useCallback": True, "data": {"text": "답변을 준비하고 있어요 🙏"}}


def _simple_text_response(text: str) -> dict:
    return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": text}}]}}


@router.post("/callback")
async def kakao_callback(
    request: KakaoCallbackRequest,
    background_tasks: BackgroundTasks,
    raw_request: Request,
):
    settings = get_settings()

    # 1. 인바운드 인증 (헤더 시크릿). 미설정 환경(로컬)에서는 스킵.
    if settings.KAKAO_SKILL_SECRET:
        provided = raw_request.headers.get(settings.KAKAO_SKILL_SECRET_HEADER, "")
        if not hmac.compare_digest(provided, settings.KAKAO_SKILL_SECRET):
            logger.warning("카카오 콜백 인증 실패")
            return JSONResponse(status_code=401, content={"message": "unauthorized"})

    # 2. callbackUrl 없으면 비동기 불가 → 동기 안내(블록 미설정/콜백 미승인)
    callback_url = request.userRequest.callbackUrl
    if not callback_url:
        return _simple_text_response("콜백이 설정되지 않았습니다. 관리자에게 문의해 주세요.")

    # 3. 백그라운드 작업 예약 + 즉시 useCallback 반환
    background_tasks.add_task(
        kakao_worker.process_kakao_callback,
        kakao_bot_id=request.bot.id,
        bot_user_key=request.userRequest.user.id,
        utterance=request.userRequest.utterance,
        callback_url=callback_url,
    )
    return _waiting_response()
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_kakao_callback.py -v`
Expected: PASS (4)

- [ ] **Step 5: 전체 테스트 재확인**

Run: `cd backend && uv run pytest -v`
Expected: 전체 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/endpoints/kakao.py backend/tests/test_kakao_callback.py
git commit -m "feat(kakao): 콜백 핸들러 재작성(헤더 인증·즉시 useCallback·작업 예약)"
```

---

## Task 14: 어드민 카카오 채널 API

**Files:**
- Create: `backend/app/schemas/bot_kakao_channel.py`
- Modify: `backend/app/api/v1/endpoints/admin/bots.py`

- [ ] **Step 1: 어드민 스키마 작성**

`backend/app/schemas/bot_kakao_channel.py`:

```python
# 어드민 카카오 채널 등록/조회 스키마
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KakaoChannelCreateRequest(BaseModel):
    kakao_bot_id: str


class KakaoChannelResponse(BaseModel):
    id: int
    bot_id: int
    kakao_bot_id: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KakaoChannelListResponse(BaseModel):
    items: list[KakaoChannelResponse]
    total: int
```

- [ ] **Step 2: 어드민 엔드포인트 추가**

`backend/app/api/v1/endpoints/admin/bots.py` 상단 import에 추가:

```python
from sqlalchemy.exc import IntegrityError

from app.crud import crud_bot_kakao_channel
from app.schemas.bot_kakao_channel import (
    KakaoChannelCreateRequest,
    KakaoChannelListResponse,
    KakaoChannelResponse,
)
```

파일 끝(봇 문서 관리 섹션 뒤)에 추가:

```python
# ── 카카오 채널 매핑 ───────────────────────────────────────────────────


@router.get("/bots/{bot_id}/kakao", response_model=KakaoChannelListResponse, tags=["Admin - 봇 관리"])
async def list_kakao_channels(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
) -> KakaoChannelListResponse:
    """봇에 등록된 카카오 채널(오픈빌더 bot.id) 목록."""
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()
    channels = await crud_bot_kakao_channel.list_by_bot(session, bot_id)
    return KakaoChannelListResponse(
        items=[KakaoChannelResponse.model_validate(c) for c in channels],
        total=len(channels),
    )


@router.post(
    "/bots/{bot_id}/kakao",
    response_model=KakaoChannelResponse,
    status_code=201,
    tags=["Admin - 봇 관리"],
)
async def create_kakao_channel(
    bot_id: int,
    request: KakaoChannelCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> KakaoChannelResponse:
    """봇에 카카오 채널(오픈빌더 bot.id) 등록."""
    bot = await crud_bot.get_bot(session, bot_id)
    if not bot:
        raise BotNotFoundError()
    try:
        channel = await crud_bot_kakao_channel.create(session, bot_id, request.kakao_bot_id.strip())
    except IntegrityError:
        await session.rollback()
        raise ValidationError("이미 등록된 카카오 봇 ID 입니다.")
    logger.info("카카오 채널 등록: bot_id=%s kakao_bot_id=%s", bot_id, request.kakao_bot_id)
    return KakaoChannelResponse.model_validate(channel)


@router.delete("/bots/{bot_id}/kakao/{channel_id}", status_code=204, tags=["Admin - 봇 관리"])
async def delete_kakao_channel(
    bot_id: int,
    channel_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """카카오 채널 매핑 삭제."""
    channels = await crud_bot_kakao_channel.list_by_bot(session, bot_id)
    target = next((c for c in channels if c.id == channel_id), None)
    if target is None:
        raise NotFoundError("카카오 채널을 찾을 수 없습니다.")
    await crud_bot_kakao_channel.delete(session, target)
    logger.info("카카오 채널 삭제: id=%s", channel_id)
```

> `BotNotFoundError`, `NotFoundError`, `ValidationError`는 이 파일에 이미 import 되어 있음(확인).

- [ ] **Step 3: 서버 기동 + 스모크 확인**

Run: `cd backend && uv run uvicorn app.main:app --port 8000 &` (별도 셸) 후
`curl -s -X POST localhost:8000/api/v1/admin/bots/1/kakao -H "Content-Type: application/json" -d '{"kakao_bot_id":"test-bot-1"}'`
Expected: 201 + `{"id":...,"kakao_bot_id":"test-bot-1",...}` (bot_id=1 이 존재할 때). 목록: `curl -s localhost:8000/api/v1/admin/bots/1/kakao`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/bot_kakao_channel.py backend/app/api/v1/endpoints/admin/bots.py
git commit -m "feat(kakao): 어드민 카카오 채널 등록/목록/삭제 API"
```

---

## Task 15: 프론트 어드민 — 카카오 채널 섹션

**Files:**
- Modify: `frontend-admin/src/features/bots/types.ts`
- Modify: `frontend-admin/src/features/bots/api.ts`
- Modify: `frontend-admin/src/features/bots/hooks.ts`
- Create: `frontend-admin/src/features/bots/components/kakao-channel-section.tsx`
- Modify: `frontend-admin/src/features/bots/components/bot-edit-form.tsx`

- [ ] **Step 1: 타입 추가**

`frontend-admin/src/features/bots/types.ts` 끝에 추가:

```typescript
export interface KakaoChannelResponse {
  id: number
  bot_id: number
  kakao_bot_id: string
  is_active: boolean
  created_at: string
}

export interface KakaoChannelListResponse {
  items: KakaoChannelResponse[]
  total: number
}
```

- [ ] **Step 2: API 함수 + Query Key 추가**

`frontend-admin/src/features/bots/api.ts`의 `botKeys`에 추가:

```typescript
  kakao: (botId: number) => [...botKeys.detail(botId), "kakao"] as const,
```

import 타입에 `KakaoChannelListResponse, KakaoChannelResponse` 추가하고 파일 끝에:

```typescript
/** 봇의 카카오 채널 목록 */
export async function fetchKakaoChannels(
  botId: number
): Promise<KakaoChannelListResponse> {
  const { data } = await apiClient.get<KakaoChannelListResponse>(
    `/api/v1/admin/bots/${botId}/kakao`
  )
  return data
}

/** 카카오 채널 등록 */
export async function createKakaoChannel(
  botId: number,
  kakaoBotId: string
): Promise<KakaoChannelResponse> {
  const { data } = await apiClient.post<KakaoChannelResponse>(
    `/api/v1/admin/bots/${botId}/kakao`,
    { kakao_bot_id: kakaoBotId }
  )
  return data
}

/** 카카오 채널 삭제 */
export async function deleteKakaoChannel(
  botId: number,
  channelId: number
): Promise<void> {
  await apiClient.delete(`/api/v1/admin/bots/${botId}/kakao/${channelId}`)
}
```

- [ ] **Step 3: 훅 추가**

`frontend-admin/src/features/bots/hooks.ts`의 import에 `botKeys, createKakaoChannel, deleteKakaoChannel, fetchKakaoChannels` 보강 후 파일 끝에:

```typescript
/** 카카오 채널 목록 훅 */
export function useKakaoChannels(botId: number) {
  return useQuery({
    queryKey: botKeys.kakao(botId),
    queryFn: () => fetchKakaoChannels(botId),
    enabled: !!botId,
  })
}

/** 카카오 채널 등록 훅 */
export function useCreateKakaoChannel(botId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (kakaoBotId: string) => createKakaoChannel(botId, kakaoBotId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: botKeys.kakao(botId) }),
  })
}

/** 카카오 채널 삭제 훅 */
export function useDeleteKakaoChannel(botId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (channelId: number) => deleteKakaoChannel(botId, channelId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: botKeys.kakao(botId) }),
  })
}
```

- [ ] **Step 4: 자체 완결 섹션 컴포넌트 작성**

`frontend-admin/src/features/bots/components/kakao-channel-section.tsx`:

```tsx
"use client"

// 봇 상세 — 카카오 채널(오픈빌더 bot.id) 등록/삭제 섹션 (자체 완결)
import * as React from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  useCreateKakaoChannel,
  useDeleteKakaoChannel,
  useKakaoChannels,
} from "../hooks"

export function KakaoChannelSection({ botId }: { botId: number }) {
  const { data } = useKakaoChannels(botId)
  const create = useCreateKakaoChannel(botId)
  const remove = useDeleteKakaoChannel(botId)
  const [value, setValue] = React.useState("")

  const onAdd = async () => {
    const v = value.trim()
    if (!v) return
    await create.mutateAsync(v)
    setValue("")
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>카카오톡 채널</CardTitle>
        <CardDescription>
          오픈빌더 콜백 요청 본문의 bot.id 를 등록하면 이 봇으로 카카오 메시지를 라우팅합니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Input
            placeholder="오픈빌더 bot.id (예: 5f1a2b3c...)"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
          <Button type="button" onClick={onAdd} disabled={create.isPending}>
            등록
          </Button>
        </div>
        <ul className="space-y-2">
          {data?.items.map((ch) => (
            <li
              key={ch.id}
              className="flex items-center justify-between rounded-md border px-3 py-2"
            >
              <span className="font-mono text-sm">{ch.kakao_bot_id}</span>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={() => remove.mutate(ch.id)}
                disabled={remove.isPending}
              >
                삭제
              </Button>
            </li>
          ))}
          {data && data.items.length === 0 && (
            <li className="text-sm text-muted-foreground">
              등록된 카카오 채널이 없습니다.
            </li>
          )}
        </ul>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 5: 폼에 섹션 삽입**

`frontend-admin/src/features/bots/components/bot-edit-form.tsx` 상단 import에 추가:

```tsx
import { KakaoChannelSection } from "./kakao-channel-section"
```

폼 본문에서 마지막 `</Card>` 다음(저장 버튼 직전)에 한 줄 삽입. 주변 JSX 들여쓰기에 맞춘다:

```tsx
        <KakaoChannelSection botId={bot.id} />
```

- [ ] **Step 6: 타입체크/빌드 확인**

Run: `cd frontend-admin && npm run build` (또는 프로젝트의 typecheck 스크립트)
Expected: 타입 에러 없이 빌드 성공.

- [ ] **Step 7: Commit**

```bash
git add frontend-admin/src/features/bots/
git commit -m "feat(kakao): 어드민 봇 상세에 카카오 채널 등록 섹션"
```

---

## Task 16: 수동 E2E 검증 (curl + 실채널)

> 자동 테스트로 못 덮는 DB·워커·실연동을 수동 확인한다. 사람이 직접 하는 콘솔 작업은 spec 8장(운영 런북) 참고.

- [ ] **Step 1: 로컬 서버 기동 + 마이그레이션 적용**

Run: `cd backend && uv run alembic upgrade head && uv run uvicorn app.main:app --port 8000`

- [ ] **Step 2: 봇에 카카오 채널 등록**

Run: `curl -s -X POST localhost:8000/api/v1/admin/bots/<BOT_ID>/kakao -H "Content-Type: application/json" -d '{"kakao_bot_id":"local-test-bot"}'`
Expected: 201.

- [ ] **Step 3: 콜백 페이로드 흉내 (즉시응답 확인)**

`.env`에 `KAKAO_SKILL_SECRET`이 비어있으면 헤더 없이, 설정돼 있으면 `-H "X-Kakao-Skill-Secret: <값>"` 추가.

Run:
```bash
curl -s -X POST localhost:8000/api/v1/kakao/callback \
  -H "Content-Type: application/json" \
  -d '{"userRequest":{"utterance":"안녕하세요","user":{"id":"tester1"},"callbackUrl":"https://bot-api.kakao.com/callback/REPLACE"},"bot":{"id":"local-test-bot"}}'
```
Expected: 즉시 `{"version":"2.0","useCallback":true,...}` (5초 이내) — 이게 핵심 검증 포인트. 백그라운드 워커는 LLM 응답까지 만든 뒤 가짜 URL 로 POST를 시도하므로 서버 로그에 "카카오 콜백 전송 실패"가 남는다(로컬엔 진짜 콜백 URL 이 없으니 정상). 호스트 차단 동작을 보려면 callbackUrl 을 비-카카오 도메인(예: `https://evil.example.com/x`)으로 바꿔 "허용되지 않은 callbackUrl host, 전송 중단" 로그를 확인한다.

- [ ] **Step 4: DB 적재 확인**

`chat_sessions`/`messages`에 `tester1` 세션 + user 메시지 + assistant 메시지(또는 워커가 LLM까지 수행했는지) 확인. 어드민 채팅 목록 UI에서도 노출되는지 확인.

- [ ] **Step 5: 실제 카카오 연동 검증 (spec 8장 운영 런북 수행 후)**

오픈빌더 콜백 승인 + 폴백 블록 설정 + 배포 완료 후, 실제 채널 친구추가 → 메시지 전송 → **30초 내 답변 + 후속질문 버튼** 도착 확인. `KAKAO_CALLBACK_ALLOWED_HOSTS`가 실제 callbackUrl host(서버 로그로 확인)를 허용하는지 점검.

- [ ] **Step 6: 회귀 — 전체 유닛 테스트**

Run: `cd backend && uv run pytest -v`
Expected: 전체 PASS.

---

## 부록: 빠른 참조

- 답변 흐름: `endpoints/kakao.py`(즉시 useCallback) → `services/kakao_worker.py`(새 세션) → `ChatService.process_chat_request(stream=False)` → `kakao_service.build_callback_payload` → `kakao_service.send_callback`.
- 봇 식별: 요청 `bot.id` → `BotKakaoChannel.kakao_bot_id` → `bot_id`.
- 사용자: `kakao:{kakao_bot_id}:{botUserKey}`, synthetic email `kakao_{kakao_bot_id}_{botUserKey}@kakao.local`.
- 보안: 인바운드 `KAKAO_SKILL_SECRET` 헤더, 아웃바운드 `KAKAO_CALLBACK_ALLOWED_HOSTS`(기본 `.kakao.com`).
- 제약: 콜백 1분·1회, simpleText ≤1000자×≤3, quickReplies ≤10, 워커 deadline 50초.
