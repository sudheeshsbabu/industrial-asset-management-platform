"""add notify trigger to app_config

Revision ID: 7b6d2c10e931
Revises: 6a5c1b09f820
Create Date: 2026-05-12 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b6d2c10e931'
down_revision: Union[str, Sequence[str], None] = '6a5c1b09f820'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_app_config_change()
        RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify('app_config_changed', '');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_app_config_change
        AFTER INSERT OR UPDATE OR DELETE ON app_config
        FOR EACH STATEMENT
        EXECUTE FUNCTION notify_app_config_change();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS trg_app_config_change ON app_config;")
    op.execute("DROP FUNCTION IF EXISTS notify_app_config_change();")
