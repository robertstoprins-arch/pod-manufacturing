"""Add Clerk auth fields

Adds:
  organizations.clerk_org_id  — links a row to a Clerk org (unique)
  projects.created_by         — Clerk user_id of the creator

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("clerk_org_id", sa.String(255), nullable=True, unique=True),
    )
    op.add_column(
        "projects",
        sa.Column("created_by", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "created_by")
    op.drop_column("organizations", "clerk_org_id")
