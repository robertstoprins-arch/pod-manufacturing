"""Add client_last_viewed_at and client_view_count to quotes

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("quotes", sa.Column("client_last_viewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quotes", sa.Column("client_view_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("quotes", "client_view_count")
    op.drop_column("quotes", "client_last_viewed_at")
