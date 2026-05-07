"""Pod specs table — links pod geometry to build-up assignments

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-02

Changes
───────
  pod_specs  new table linking pod geometry JSON to wall/floor/roof build-up IDs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pod_specs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("geometry", JSONB, nullable=False),
        sa.Column(
            "wall_build_up_id", sa.Integer(),
            sa.ForeignKey("build_ups.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "floor_build_up_id", sa.Integer(),
            sa.ForeignKey("build_ups.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "roof_build_up_id", sa.Integer(),
            sa.ForeignKey("build_ups.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=True, server_default="draft"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("pod_specs")
