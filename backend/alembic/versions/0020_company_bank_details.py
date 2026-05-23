"""Add company and bank details to account_settings for deposit invoices

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("account_settings", sa.Column("company_name", sa.String(255), nullable=True))
    op.add_column("account_settings", sa.Column("company_address", sa.Text, nullable=True))
    op.add_column("account_settings", sa.Column("company_email", sa.String(255), nullable=True))
    op.add_column("account_settings", sa.Column("company_phone", sa.String(50), nullable=True))
    op.add_column("account_settings", sa.Column("vat_number", sa.String(50), nullable=True))
    op.add_column("account_settings", sa.Column("bank_name", sa.String(255), nullable=True))
    op.add_column("account_settings", sa.Column("bank_account_name", sa.String(255), nullable=True))
    op.add_column("account_settings", sa.Column("bank_iban", sa.String(50), nullable=True))
    op.add_column("account_settings", sa.Column("bank_bic", sa.String(20), nullable=True))
    op.add_column("account_settings", sa.Column("payment_terms_days", sa.Integer, nullable=True, server_default="7"))


def downgrade():
    op.drop_column("account_settings", "payment_terms_days")
    op.drop_column("account_settings", "bank_bic")
    op.drop_column("account_settings", "bank_iban")
    op.drop_column("account_settings", "bank_account_name")
    op.drop_column("account_settings", "bank_name")
    op.drop_column("account_settings", "vat_number")
    op.drop_column("account_settings", "company_phone")
    op.drop_column("account_settings", "company_email")
    op.drop_column("account_settings", "company_address")
    op.drop_column("account_settings", "company_name")
