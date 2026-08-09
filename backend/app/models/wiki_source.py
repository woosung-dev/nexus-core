"""위키 원문(source unit) 모델 — 규정집·대사전을 조문 단위로 담는다.

## 왜 DB 로 옮기나

`app/services/wiki/store.py` 가 `exports/wiki_2026-08/` 를 파일시스템에서 직접 읽고 있었다.
그 디렉터리는 7.9MB 이고 `/exports` 는 gitignore 라 **배포 이미지에 아예 실리지 않는다.**
어휘 검색(`retrieval_mode="lexical"`)을 라이브에 붙이려면 원문이 DB 에 있어야 한다.

## 왜 두 테이블인가

디스크에서 `sources/<sha8>/` 는 **봇과 무관하게 문서 단위로 공유**된다
(`exports/wiki_2026-08/_split.py:11-13` — 같은 규정집을 여러 봇이 함께 쓴다).
봇별 구분은 `bots/<id>/manifest.json` 이 한다. 그 구조를 그대로 옮긴다.

한 테이블에 `bot_id` 를 넣으면 봇마다 250행이 복제되고, 무엇보다 `src_id` 만으로는
유일하지 않다 — 규정집이 v20 에서 v21 로 올라가면 `reg-33` 이 둘이 된다.
판본을 구분하는 것은 문서 해시(`sha8`)뿐이므로 유일키는 `(sha8, src_id)` 다.

## 담는 것

원문 250건(142KB) **과** 위키 페이지 138쪽을 담는다.

페이지를 담는 이유는 「위키 본문으로 답하기 위해서」가 **아니다** — 그 팔(C)은 45문항 측정
세 회차 모두 최하위권이라 기각됐다(§2-5). 페이지는 **검색 신호**로만 쓴다. 페이지의
`## 사실` 문장 971개가 `fact` 스케일이 되고, 그것이 RRF 융합의 세 순위표 중 하나다.

빼고 재봤더니 검색이 실질적으로 다른 것이 됐다(45문항 · `raw_budget` 실제 주입 비교):

    주입 목록 완전 동일        2/45 (4%)
    자카드 평균               0.47
    reg-100(29,774자 부칙)    1/45 → 19/45

reg-100 은 3,000자 예산을 통째로 먹는 유닛이라 42% 의 질문에서 진짜 근거가 밀려난다.

`WIKI_DENSE_SCALES=""` 가 기본이라 벡터는 저장하지 않는다. BM25 역색인은 기동 시
메모리에 0.01초면 선다.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlmodel import Field, SQLModel


def get_utc_now():
    """파이썬 레벨의 UTC 현재 시간 — default_factory용"""
    return datetime.now(timezone.utc)


class WikiSourceUnit(SQLModel, table=True):
    """원문 조각 1건 — wiki_source_units 테이블. 문서 단위로 공유되며 봇에 매이지 않는다."""

    __tablename__ = "wiki_source_units"
    __table_args__ = (
        UniqueConstraint("sha8", "src_id", name="uq_wiki_source_unit_sha8_src_id"),
    )

    id: int | None = Field(default=None, primary_key=True)

    # 원본 문서의 sha256 앞 8자리. 판본을 가르는 유일한 값이다.
    sha8: str = Field(sa_column=Column(String(16), nullable=False, index=True))

    # 'reg-33' · 'glo-47'. 판본이 다르면 같은 값이 또 나온다 — 단독으로는 유일하지 않다.
    src_id: str = Field(sa_column=Column(String(32), nullable=False, index=True))

    # '규정집v20' · '대사전v4'
    doc: str = Field(sa_column=Column(String(64), nullable=False, server_default=""))

    # '제33조(금식정성의 기준)' · '행정 47 미납 정산'
    locator: str = Field(sa_column=Column(String(255), nullable=False, server_default=""))

    # 조문 본문. reg-100(부칙 모음)이 29,775자라 String 이 아니라 Text 여야 한다.
    text: str = Field(sa_column=Column(Text, nullable=False))

    chars: int = Field(sa_column=Column(Integer, nullable=False, server_default="0"))

    created_at: datetime = Field(
        default_factory=get_utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )


class WikiPageRow(SQLModel, table=True):
    """위키 페이지 1쪽 — wiki_pages 테이블. **검색 신호**로만 쓴다(답변 본문으로 쓰지 않는다).

    `## 사실` 의 문장들이 fact 스케일(971건)이 되고, `sources` 가 페이지↔원문 역방향 매핑을
    만든다. 이 둘이 빠지면 RRF 융합이 unit 순위표 하나로 줄어 검색이 실질적으로 나빠진다.
    """

    __tablename__ = "wiki_pages"
    __table_args__ = (
        UniqueConstraint("bot_id", "slug", name="uq_wiki_page_bot_slug"),
    )

    id: int | None = Field(default=None, primary_key=True)

    # 페이지는 원문과 달리 **봇별**이다 — 같은 규정집에서 봇마다 다른 위키를 컴파일한다.
    bot_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("bots.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    slug: str = Field(sa_column=Column(String(255), nullable=False, index=True))
    title: str = Field(sa_column=Column(String(255), nullable=False, server_default=""))
    summary: str = Field(sa_column=Column(Text, nullable=False, server_default=""))
    # `## 사실` 절 전문. 줄 단위로 쪼개 fact 스케일이 된다.
    facts: str = Field(sa_column=Column(Text, nullable=False, server_default=""))
    # 이 페이지가 인용하는 원문 src_id 목록 — ['reg-45', 'reg-46']
    sources: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )

    created_at: datetime = Field(
        default_factory=get_utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )


class WikiBotSource(SQLModel, table=True):
    """봇 ↔ 문서 연결 1건 — wiki_bot_sources 테이블. `manifest.json` 의 sources 항목과 1:1."""

    __tablename__ = "wiki_bot_sources"
    __table_args__ = (
        UniqueConstraint("bot_id", "sha8", name="uq_wiki_bot_source_bot_sha8"),
    )

    id: int | None = Field(default=None, primary_key=True)

    bot_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("bots.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    sha8: str = Field(sa_column=Column(String(16), nullable=False, index=True))

    # 'reg' · 'glo'. src_id 접두사와 같다.
    prefix: str = Field(sa_column=Column(String(16), nullable=False, server_default=""))

    doc: str = Field(sa_column=Column(String(64), nullable=False, server_default=""))

    # 업로드 원본 파일명. 어느 PDF 에서 나왔는지 추적용이다.
    display_name: str = Field(sa_column=Column(String(512), nullable=False, server_default=""))

    count: int = Field(sa_column=Column(Integer, nullable=False, server_default="0"))

    created_at: datetime = Field(
        default_factory=get_utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
