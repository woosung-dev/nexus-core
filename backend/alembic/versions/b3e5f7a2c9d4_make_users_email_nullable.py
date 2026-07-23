"""make users.email nullable

하나로 SSO 는 개인정보를 반환하지 않아(규격서 8장) 이메일이 존재하지 않는다.
없는 값을 합성해 채우면 실제로 연락 가능한 주소처럼 보여 오해를 부르므로 NULL 을 허용한다.
Postgres 의 unique 인덱스는 NULL 을 중복으로 취급하지 않아 기존 제약과 공존한다.

Revision ID: b3e5f7a2c9d4
Revises: 8f3d7a1c9e5b
Create Date: 2026-07-23 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e5f7a2c9d4'
down_revision: Union[str, Sequence[str], None] = '8f3d7a1c9e5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'users',
        'email',
        existing_type=sa.String(length=255),
        nullable=True,
    )
    # 이미 생성된 하나로 계정의 합성 이메일(@hanaro.sso)을 비운다.
    op.execute("UPDATE users SET email = NULL WHERE email LIKE '%@hanaro.sso'")


def downgrade() -> None:
    # NULL 이 남아 있으면 NOT NULL 로 되돌릴 수 없으므로 자리표시자를 채운다.
    op.execute(
        "UPDATE users SET email = 'unknown-' || id::text || '@invalid.local' WHERE email IS NULL"
    )
    op.alter_column(
        'users',
        'email',
        existing_type=sa.String(length=255),
        nullable=False,
    )
