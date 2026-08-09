"""merge retrieval_mode and clarification heads

Revision ID: 2e7f2e0417ec
Revises: e6f9b2d4a8c3, e2f6a4b8c1d3
Create Date: 2026-08-09 09:56:19.243684

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e7f2e0417ec'
down_revision: Union[str, Sequence[str], None] = ('e6f9b2d4a8c3', 'e2f6a4b8c1d3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
