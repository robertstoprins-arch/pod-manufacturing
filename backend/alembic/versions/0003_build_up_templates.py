"""Build-up template fields — nullable element_id, scope/status/notes, material properties

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-02

Changes
───────
  build_ups.element_id       → nullable (free-standing library templates)
  build_ups.element_type     VARCHAR(30)  ExternalWall | Floor | Roof
  build_ups.scope            VARCHAR(20)  library | project
  build_ups.status           VARCHAR(20)  draft | approved | superseded
  build_ups.notes            TEXT
  build_ups.created_at       TIMESTAMP TZ
  build_ups.updated_at       TIMESTAMP TZ
  material_library.properties  JSONB      default_role, default_thickness_mm, etc.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # build_ups: make element_id nullable
    op.alter_column("build_ups", "element_id", nullable=True)

    # build_ups: add template management fields
    op.add_column("build_ups", sa.Column("element_type", sa.String(30)))
    op.add_column("build_ups", sa.Column("scope", sa.String(20), server_default="library"))
    op.add_column("build_ups", sa.Column("status", sa.String(20), server_default="draft"))
    op.add_column("build_ups", sa.Column("notes", sa.Text))
    op.add_column("build_ups", sa.Column("created_at", sa.DateTime(timezone=True)))
    op.add_column("build_ups", sa.Column("updated_at", sa.DateTime(timezone=True)))

    # material_library: add extra metadata column
    op.add_column("material_library", sa.Column("properties", JSONB))


def downgrade() -> None:
    op.drop_column("material_library", "properties")
    op.drop_column("build_ups", "updated_at")
    op.drop_column("build_ups", "created_at")
    op.drop_column("build_ups", "notes")
    op.drop_column("build_ups", "status")
    op.drop_column("build_ups", "scope")
    op.drop_column("build_ups", "element_type")
    op.alter_column("build_ups", "element_id", nullable=False)
