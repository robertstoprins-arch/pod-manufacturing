"""Add client token fields to quotes for customer portal

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("quotes", sa.Column("client_token", sa.Uuid(as_uuid=True), nullable=True, unique=True))
    op.add_column("quotes", sa.Column("client_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quotes", sa.Column("client_viewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quotes", sa.Column("client_responded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quotes", sa.Column("client_response", sa.String(30), nullable=True))
    op.add_column("quotes", sa.Column("client_response_note", sa.Text, nullable=True))
    op.create_index("ix_quotes_client_token", "quotes", ["client_token"], unique=True)


def downgrade():
    op.drop_index("ix_quotes_client_token", "quotes")
    op.drop_column("quotes", "client_response_note")
    op.drop_column("quotes", "client_response")
    op.drop_column("quotes", "client_responded_at")
    op.drop_column("quotes", "client_viewed_at")
    op.drop_column("quotes", "client_token_expires_at")
    op.drop_column("quotes", "client_token")
