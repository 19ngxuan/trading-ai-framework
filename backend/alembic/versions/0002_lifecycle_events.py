"""Add documented lifecycle event enum values.

Revision ID: 0002_lifecycle_events
Revises: 0001_initial_schema
Create Date: 2026-05-22 00:30:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision = "0002_lifecycle_events"
down_revision = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE system_event_type ADD VALUE IF NOT EXISTS 'EXPERIMENT_RESUMED'"
    )
    op.execute(
        "ALTER TYPE system_event_type ADD VALUE IF NOT EXISTS 'EXPERIMENT_FAILED'"
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values in-place.
    pass
