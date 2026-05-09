"""add evidence_category to material_library

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "material_library",
        sa.Column(
            "evidence_category",
            sa.String(40),
            nullable=False,
            server_default="manufactured_product",
        ),
    )


def downgrade():
    op.drop_column("material_library", "evidence_category")
