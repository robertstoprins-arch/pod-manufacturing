"""Ensure preferred_supplier FK constraint exists (repair broken 0016 deploy)

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Check if column exists
    col_exists = bind.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='material_library' AND column_name='preferred_supplier_id'"
    )).fetchone()

    if not col_exists:
        op.add_column(
            "material_library",
            sa.Column("preferred_supplier_id", sa.Uuid(as_uuid=True), nullable=True),
        )

    # Check if FK constraint exists
    fk_exists = bind.execute(sa.text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE table_name='material_library' AND constraint_name='fk_material_preferred_supplier'"
    )).fetchone()

    if not fk_exists:
        op.create_foreign_key(
            "fk_material_preferred_supplier",
            "material_library", "suppliers",
            ["preferred_supplier_id"], ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    bind = op.get_bind()
    fk_exists = bind.execute(sa.text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE table_name='material_library' AND constraint_name='fk_material_preferred_supplier'"
    )).fetchone()
    if fk_exists:
        op.drop_constraint("fk_material_preferred_supplier", "material_library", type_="foreignkey")
