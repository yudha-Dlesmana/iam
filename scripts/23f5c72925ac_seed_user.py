"""seed_user

Revision ID: 23f5c72925ac
Revises: 80b2e2faedd7
Create Date: 2026-04-25 17:05:26.030132

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa

from src.core.security import hash_password


# revision identifiers, used by Alembic.
revision: str = '23f5c72925ac'
down_revision: Union[str, None] = '80b2e2faedd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMAIL = "admin@starter.com"
PASSWORD = "!Qwer123"

def upgrade() -> None:
    users_table = sa.table(
        'users',
        sa.column('id', sa.String),
        sa.column('email', sa.String),
        sa.column('password', sa.String),
        sa.column('role_id', sa.Integer),
    )
    op.bulk_insert(users_table, [
        {
            'id': str(uuid.uuid4()),
            'email': EMAIL,
            'password': hash_password(PASSWORD),
            'role_id': 1,
        }
    ])


def downgrade() -> None:
    op.execute(f"DELETE FROM users WHERE email = '{EMAIL}'")
