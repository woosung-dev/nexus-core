"""merge_strict_mode_and_user_heads

Revision ID: c8e2a4d6f9b1
Revises: b3e5f7a2c9d4, b4c1d7e9f2a6
"""

from typing import Sequence, Union


revision: str = "c8e2a4d6f9b1"
down_revision: Union[str, Sequence[str], None] = ("b3e5f7a2c9d4", "b4c1d7e9f2a6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
