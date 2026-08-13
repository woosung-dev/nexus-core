"""되묻기(clarification) 걷어내기 — 컬럼 3개 삭제

되묻기 기능을 사용자 화면·관리자 화면·런타임에서 전부 제거했다. 그 기능만 쓰던 컬럼도
같이 내린다.

**되돌리려면 데이터가 아니라 구조만 돌아온다.** downgrade 는 컬럼을 다시 만들지만 내용은
비어 있다. 삭제 시점 라이브 실측:

    messages.clarification 이 채워진 행   2   (봇 11 테스트 대화, 실사용자 아님)
    bots.clarify_enabled = true          1   (봇 11)
    규칙이 든 bots.clarification_policy   1   (봇 11)

`unanswered_questions` 는 남긴다 — 되묻기 판정기(`judge_clarify`) 말고도 이유코드가 넷 더
있고 그쪽 배선은 그대로다. 기존 `judge_clarify` 행 1건은 이유코드가 사라진 채 남는데,
화면이 모르는 코드를 그냥 안 그리므로 지우지 않는다(과거 관측 기록으로 둔다).

Revision ID: c5b1e7a09d42
Revises: a1c7d3e9f204
Create Date: 2026-08-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c5b1e7a09d42"
down_revision = "a1c7d3e9f204"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("messages", "clarification")
    op.drop_column("bots", "clarification_policy")
    op.drop_column("bots", "clarify_enabled")


def downgrade() -> None:
    # 구조만 되돌린다. 지워진 내용은 복구되지 않는다.
    op.add_column(
        "bots",
        sa.Column("clarify_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "bots",
        sa.Column(
            "clarification_policy",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{\"enabled\": false, \"rules\": []}'::json"),
        ),
    )
    op.add_column(
        "messages",
        sa.Column("clarification", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
