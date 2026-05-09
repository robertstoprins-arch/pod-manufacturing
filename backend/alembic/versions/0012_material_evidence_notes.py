"""add evidence_notes to material_library

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "material_library",
        sa.Column("evidence_notes", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column("material_library", "evidence_notes")
