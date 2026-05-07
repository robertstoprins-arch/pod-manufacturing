"""Material evidence fields — supplier links, datasheets, DoP, evidence_status

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("material_library", sa.Column("supplier_name",    sa.String(255), nullable=True))
    op.add_column("material_library", sa.Column("supplier_url",     sa.Text(),      nullable=True))
    op.add_column("material_library", sa.Column("datasheet_url",    sa.Text(),      nullable=True))
    op.add_column("material_library", sa.Column("dop_url",          sa.Text(),      nullable=True))
    op.add_column("material_library", sa.Column("price_source_url", sa.Text(),      nullable=True))
    op.add_column("material_library", sa.Column("price_checked_at", sa.Date(),      nullable=True))
    op.add_column("material_library", sa.Column(
        "evidence_status",
        sa.String(20),
        nullable=False,
        server_default="missing",
    ))


def downgrade() -> None:
    for col in ["supplier_name", "supplier_url", "datasheet_url", "dop_url",
                "price_source_url", "price_checked_at", "evidence_status"]:
        op.drop_column("material_library", col)
