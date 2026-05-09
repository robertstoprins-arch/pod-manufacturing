"""add account_settings table

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "account_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("default_markup_percent", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("vat_rate_percent", sa.Float(), nullable=False, server_default="21.0"),
        sa.Column("vat_mode", sa.String(20), nullable=False, server_default="excluded"),
        sa.Column("round_to_nearest", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Insert the single default row so _get_or_create always finds one
    op.execute(
        "INSERT INTO account_settings (default_markup_percent, currency, vat_rate_percent, "
        "vat_mode, round_to_nearest) VALUES (50.0, 'EUR', 21.0, 'excluded', 100)"
    )


def downgrade():
    op.drop_table("account_settings")
