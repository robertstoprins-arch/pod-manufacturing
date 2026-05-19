"""Link material_library to preferred supplier

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "material_library",
        sa.Column("preferred_supplier_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_material_preferred_supplier",
        "material_library", "suppliers",
        ["preferred_supplier_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_material_preferred_supplier", "material_library", type_="foreignkey")
    op.drop_column("material_library", "preferred_supplier_id")
