"""Add client_project_id to pod_specs

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pod_specs", sa.Column("client_project_id", sa.String(50), nullable=True))


def downgrade():
    op.drop_column("pod_specs", "client_project_id")
