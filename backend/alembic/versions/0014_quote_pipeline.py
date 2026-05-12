"""Quote pipeline — clients, quotes, quote_events

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "clients",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("client_type", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "quotes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("pod_spec_id", sa.Integer, sa.ForeignKey("pod_specs.id"), nullable=True),
        sa.Column("client_id", sa.Uuid(as_uuid=True), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("quote_number", sa.String(50), unique=True, nullable=True),
        sa.Column("revision", sa.String(20), nullable=False, server_default="Rev 1"),
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("client_email", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("lead_source", sa.String(100), nullable=True),
        sa.Column("lost_reason", sa.String(100), nullable=True),
        sa.Column("total_ex_vat", sa.Numeric(10, 2), nullable=True),
        sa.Column("total_inc_vat", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="EUR"),
        sa.Column("deposit_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("deposit_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("payment_status", sa.String(30), nullable=True),
        sa.Column("payment_link", sa.Text, nullable=True),
        sa.Column("spec_snapshot", sa.JSON, nullable=True),
        sa.Column("pricing_snapshot", sa.JSON, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lost_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_to_job_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_followed_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_revision_locked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "quote_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("quote_id", sa.Uuid(as_uuid=True), sa.ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("old_status", sa.String(30), nullable=True),
        sa.Column("new_status", sa.String(30), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("quote_events")
    op.drop_table("quotes")
    op.drop_table("clients")
