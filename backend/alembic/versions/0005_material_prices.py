"""Material prices table — multiple prices per material, one default

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-03

Changes
───────
  material_prices  new table; one-to-many from material_library
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "material_prices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "material_id", sa.Integer(),
            sa.ForeignKey("material_library.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price_type", sa.String(30), nullable=False),
        sa.Column("price_per_unit", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("supplier_ref", sa.String(255), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_index("ix_material_prices_material_id", "material_prices", ["material_id"])


def downgrade() -> None:
    op.drop_index("ix_material_prices_material_id", "material_prices")
    op.drop_table("material_prices")
