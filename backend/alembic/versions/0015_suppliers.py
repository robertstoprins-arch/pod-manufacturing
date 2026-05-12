"""Supplier directory

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("website", sa.Text, nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("lead_time_days", sa.Integer, nullable=True),
        sa.Column("payment_terms", sa.String(255), nullable=True),
        sa.Column("delivery_terms", sa.String(255), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="EUR"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("suppliers")
