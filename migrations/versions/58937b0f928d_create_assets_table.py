"""create assets table

Revision ID: 58937b0f928d
Revises: 
Create Date: 2026-05-11 22:57:57.394669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58937b0f928d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("site", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("assets")
