"""Add awarded_at and awarded_by to rfq_requests

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rfq_requests", sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rfq_requests", sa.Column("awarded_by", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("rfq_requests", "awarded_by")
    op.drop_column("rfq_requests", "awarded_at")
