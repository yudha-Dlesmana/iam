"""seed roles

Revision ID: 80b2e2faedd7
Revises: f2e5f89e4608
Create Date: 2026-04-15 21:21:59.825462

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80b2e2faedd7'
down_revision: Union[str, None] = 'f2e5f89e4608'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    roles_table = sa.table(
        'roles',
        sa.column('name', sa.String),
    )
    op.bulk_insert(roles_table, [
        {'name': 'admin'},
        {'name': 'user'}
    ])


def downgrade() -> None:
    op.execute("DELETE FORM roles WHERE name IN ('admin', 'user')")
