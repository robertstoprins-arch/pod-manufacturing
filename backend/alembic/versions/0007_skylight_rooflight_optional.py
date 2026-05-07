"""Move ENV_ROOFLIGHT to optional_addons phase and off by default

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE provisional_allowances "
            "SET cost_phase = 'optional_addons', is_included_by_default = FALSE "
            "WHERE code = 'ENV_ROOFLIGHT'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE provisional_allowances "
            "SET cost_phase = 'base_envelope', is_included_by_default = TRUE "
            "WHERE code = 'ENV_ROOFLIGHT'"
        )
    )
