"""Add notify_name, notify_email, notify_phone to account_settings

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("account_settings", sa.Column("notify_name",  sa.String(255), nullable=True))
    op.add_column("account_settings", sa.Column("notify_email", sa.String(255), nullable=True))
    op.add_column("account_settings", sa.Column("notify_phone", sa.String(50),  nullable=True))


def downgrade():
    op.drop_column("account_settings", "notify_phone")
    op.drop_column("account_settings", "notify_email")
    op.drop_column("account_settings", "notify_name")
