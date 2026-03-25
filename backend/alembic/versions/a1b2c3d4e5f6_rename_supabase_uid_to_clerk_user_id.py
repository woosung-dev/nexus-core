"""rename_supabase_uid_to_clerk_user_id

Revision ID: a1b2c3d4e5f6
Revises: 412b6cf3c1e1
Create Date: 2026-03-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '412b6cf3c1e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'supabase_uid', new_column_name='clerk_user_id')


def downgrade() -> None:
    op.alter_column('users', 'clerk_user_id', new_column_name='supabase_uid')
