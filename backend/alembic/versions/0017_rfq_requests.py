"""rfq_requests and rfq_response_lines

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rfq_requests",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("quote_id", sa.Uuid(as_uuid=True), sa.ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", sa.Uuid(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supplier_name", sa.String(255), nullable=False),
        sa.Column("supplier_email", sa.String(255), nullable=True),
        sa.Column("token", sa.Uuid(as_uuid=True), nullable=False, unique=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("items_json", sa.JSON, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rfq_requests_token", "rfq_requests", ["token"], unique=True)
    op.create_index("ix_rfq_requests_quote_id", "rfq_requests", ["quote_id"])

    op.create_table(
        "rfq_response_lines",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("rfq_request_id", sa.Uuid(as_uuid=True), sa.ForeignKey("rfq_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_id", sa.String(20), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("unit_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=True),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("lead_time_days", sa.Integer, nullable=True),
        sa.Column("availability", sa.String(50), nullable=True),
        sa.Column("substitute_offered", sa.Boolean, server_default="false"),
        sa.Column("substitute_description", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rfq_response_lines_request_id", "rfq_response_lines", ["rfq_request_id"])

    # overall response metadata stored on rfq_requests (notes/currency/valid_until added below)
    op.add_column("rfq_requests", sa.Column("response_notes", sa.Text, nullable=True))
    op.add_column("rfq_requests", sa.Column("response_currency", sa.String(10), nullable=True))
    op.add_column("rfq_requests", sa.Column("response_valid_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rfq_requests", sa.Column("response_total", sa.Numeric(12, 2), nullable=True))


def downgrade():
    op.drop_table("rfq_response_lines")
    op.drop_table("rfq_requests")
