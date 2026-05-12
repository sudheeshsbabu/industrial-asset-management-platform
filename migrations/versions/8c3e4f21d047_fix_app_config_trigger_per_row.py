"""fix app_config trigger to FOR EACH ROW

Revision ID: 8c3e4f21d047
Revises: 7b6d2c10e931
Create Date: 2026-05-12 22:45:00.000000

Change the trg_app_config_change trigger from FOR EACH STATEMENT to
FOR EACH ROW so that NOTIFY is only sent when a row is actually
inserted or updated with a new value.

With the previous FOR EACH STATEMENT trigger, every call to upsert_config()
emitted a NOTIFY — even when the ON CONFLICT WHERE clause suppressed the
write because the incoming value equalled the stored value. This caused
spurious config reloads on startup (one per key, even with zero changes).

With FOR EACH ROW:
  - New key inserted          → INSERT row trigger fires  → NOTIFY ✓
  - Existing key, new value   → UPDATE row trigger fires  → NOTIFY ✓
  - Existing key, same value  → WHERE blocks write        → no trigger → no NOTIFY ✓
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8c3e4f21d047'
down_revision: Union[str, Sequence[str], None] = '7b6d2c10e931'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace the statement-level trigger with a row-level trigger."""
    # Drop the old statement-level trigger (function is reused, no need to recreate it).
    op.execute("DROP TRIGGER IF EXISTS trg_app_config_change ON app_config;")

    # Create a row-level trigger so NOTIFY only fires when a row is actually written.
    op.execute(
        """
        CREATE TRIGGER trg_app_config_change
        AFTER INSERT OR UPDATE OR DELETE ON app_config
        FOR EACH ROW
        EXECUTE FUNCTION notify_app_config_change();
        """
    )


def downgrade() -> None:
    """Restore the original statement-level trigger."""
    op.execute("DROP TRIGGER IF EXISTS trg_app_config_change ON app_config;")

    op.execute(
        """
        CREATE TRIGGER trg_app_config_change
        AFTER INSERT OR UPDATE OR DELETE ON app_config
        FOR EACH STATEMENT
        EXECUTE FUNCTION notify_app_config_change();
        """
    )
