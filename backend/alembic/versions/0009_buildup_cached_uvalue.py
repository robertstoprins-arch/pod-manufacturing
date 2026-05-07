"""Add cached u_value to build_ups for fast list queries

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("build_ups", sa.Column("u_value", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("build_ups", "u_value")
