"""Ensure preferred_supplier FK constraint exists (repair broken 0016 deploy)

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # Add column if it somehow doesn't exist (paranoia)
    existing_cols = [c["name"] for c in insp.get_columns("material_library")]
    if "preferred_supplier_id" not in existing_cols:
        op.add_column(
            "material_library",
            sa.Column("preferred_supplier_id", sa.Uuid(as_uuid=True), nullable=True),
        )

    # Add FK constraint if it doesn't exist
    existing_fks = [fk["name"] for fk in insp.get_foreign_keys("material_library")]
    if "fk_material_preferred_supplier" not in existing_fks:
        op.create_foreign_key(
            "fk_material_preferred_supplier",
            "material_library", "suppliers",
            ["preferred_supplier_id"], ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    existing_fks = [fk["name"] for fk in insp.get_foreign_keys("material_library")]
    if "fk_material_preferred_supplier" in existing_fks:
        op.drop_constraint("fk_material_preferred_supplier", "material_library", type_="foreignkey")
