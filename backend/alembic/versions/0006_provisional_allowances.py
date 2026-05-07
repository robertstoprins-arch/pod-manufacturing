"""Provisional allowances table — configurable provisional sums for cost summary

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-04

Changes
───────
  provisional_allowances  new table; seeded with 17 standard items
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_NOW = datetime.now(timezone.utc)

SEED = [
    # ── Envelope openings ──────────────────────────────────────────────────────
    dict(code="ENV_WINDOW",      name="Opening window ~1000×1000 (openable)",
         category="envelope",   unit="each",  default_unit_rate=250.0,
         quantity_source="opening_count_window",  default_quantity=0,
         is_included_by_default=True,  is_client_discretion=False,
         cost_phase="base_envelope",   sort_order=10,
         notes="Provisional. Openable PVC window. Replace with supplier quote."),
    dict(code="ENV_EXT_DOOR",   name="Standard external door",
         category="envelope",   unit="each",  default_unit_rate=300.0,
         quantity_source="opening_count_door",    default_quantity=0,
         is_included_by_default=True,  is_client_discretion=False,
         cost_phase="base_envelope",   sort_order=20,
         notes="Basic external entrance door allowance."),
    dict(code="ENV_FRENCH_DOOR", name="French / patio door",
         category="envelope",   unit="each",  default_unit_rate=1200.0,
         quantity_source="manual",               default_quantity=0,
         is_included_by_default=False, is_client_discretion=False,
         cost_phase="base_envelope",   sort_order=30,
         notes="Larger glazed external door allowance."),
    dict(code="ENV_ROOFLIGHT",  name="Rooflight / skylight ~600×800",
         category="roof",       unit="each",  default_unit_rate=250.0,
         quantity_source="opening_count_rooflight", default_quantity=0,
         is_included_by_default=True,  is_client_discretion=False,
         cost_phase="base_envelope",   sort_order=40,
         notes="Provisional small rooflight allowance. Replace with supplier quote."),

    # ── Finishes ───────────────────────────────────────────────────────────────
    dict(code="FIN_FLOORING",   name="Flooring finish (laminate/vinyl)",
         category="finishes",   unit="m2",   default_unit_rate=18.0,
         quantity_source="floor_area",           default_quantity=0,
         is_included_by_default=False, is_client_discretion=False,
         cost_phase="interior_finish",  sort_order=50,
         notes="Budget-standard laminate/vinyl allowance."),
    dict(code="FIN_UNDERLAY",   name="Floor underlay / trims / thresholds",
         category="finishes",   unit="m2",   default_unit_rate=5.0,
         quantity_source="floor_area",           default_quantity=0,
         is_included_by_default=False, is_client_discretion=False,
         cost_phase="interior_finish",  sort_order=60,
         notes="Underlay, trims, thresholds."),
    dict(code="FIN_PAINT",      name="Paint / primer / decorating material",
         category="finishes",   unit="m2",   default_unit_rate=6.0,
         quantity_source="wall_ceiling_area",     default_quantity=0,
         is_included_by_default=False, is_client_discretion=False,
         cost_phase="interior_finish",  sort_order=70,
         notes="Material allowance only, wall + ceiling board area."),
    dict(code="FIN_LIGHT_INT",  name="Internal light fitting",
         category="electrical", unit="each", default_unit_rate=35.0,
         quantity_source="manual",               default_quantity=2,
         is_included_by_default=False, is_client_discretion=False,
         cost_phase="interior_finish",  sort_order=80,
         notes="Basic internal fitting allowance."),
    dict(code="FIN_LIGHT_EXT",  name="External light fitting",
         category="electrical", unit="each", default_unit_rate=45.0,
         quantity_source="manual",               default_quantity=2,
         is_included_by_default=False, is_client_discretion=False,
         cost_phase="interior_finish",  sort_order=90,
         notes="Basic external fitting allowance."),
    dict(code="FIN_SKIRTING",   name="Skirting board",
         category="finishes",   unit="lm",   default_unit_rate=4.0,
         quantity_source="manual",               default_quantity=15,
         is_included_by_default=False, is_client_discretion=False,
         cost_phase="interior_finish",  sort_order=100,
         notes="Material allowance."),
    dict(code="FIN_ARCHITRAVE", name="Architrave",
         category="finishes",   unit="lm",   default_unit_rate=4.0,
         quantity_source="manual",               default_quantity=10,
         is_included_by_default=False, is_client_discretion=False,
         cost_phase="interior_finish",  sort_order=110,
         notes="Material allowance."),
    dict(code="FIN_INT_DOOR",   name="Internal door set",
         category="finishes",   unit="each", default_unit_rate=180.0,
         quantity_source="manual",               default_quantity=1,
         is_included_by_default=False, is_client_discretion=False,
         cost_phase="interior_finish",  sort_order=120,
         notes="Door leaf / frame / ironmongery allowance."),

    # ── Furniture / client discretion ──────────────────────────────────────────
    dict(code="FURN_KITCHENETTE", name="Kitchenette",
         category="furniture",  unit="each", default_unit_rate=600.0,
         quantity_source="manual",               default_quantity=0,
         is_included_by_default=False, is_client_discretion=True,
         cost_phase="optional_addons",  sort_order=200,
         notes="Small kitchenette allowance."),
    dict(code="FURN_SINGLE_BED", name="Single bed (frame + mattress)",
         category="furniture",  unit="each", default_unit_rate=270.0,
         quantity_source="manual",               default_quantity=0,
         is_included_by_default=False, is_client_discretion=True,
         cost_phase="optional_addons",  sort_order=210,
         notes="Basic bed frame + mattress allowance."),
    dict(code="FURN_DOUBLE_BED", name="Double bed (frame + mattress)",
         category="furniture",  unit="each", default_unit_rate=370.0,
         quantity_source="manual",               default_quantity=0,
         is_included_by_default=False, is_client_discretion=True,
         cost_phase="optional_addons",  sort_order=220,
         notes="Basic double bed allowance."),
    dict(code="FURN_DESK_CHAIR", name="Office desk + chair",
         category="furniture",  unit="set",  default_unit_rate=370.0,
         quantity_source="manual",               default_quantity=0,
         is_included_by_default=False, is_client_discretion=True,
         cost_phase="optional_addons",  sort_order=230,
         notes="Desk and chair bundle allowance."),
    dict(code="SANIT_VANITY",   name="Vanity unit",
         category="sanitary",   unit="each", default_unit_rate=150.0,
         quantity_source="manual",               default_quantity=0,
         is_included_by_default=False, is_client_discretion=True,
         cost_phase="optional_addons",  sort_order=240,
         notes="Basic vanity/washstand allowance. Client discretion."),
]


def upgrade() -> None:
    op.create_table(
        "provisional_allowances",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("default_unit_rate", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("quantity_source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("default_quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_included_by_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_client_discretion", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cost_phase", sa.String(50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.bulk_insert(
        sa.table(
            "provisional_allowances",
            sa.column("code"), sa.column("name"), sa.column("category"),
            sa.column("unit"), sa.column("default_unit_rate"), sa.column("currency"),
            sa.column("quantity_source"), sa.column("default_quantity"),
            sa.column("is_included_by_default"), sa.column("is_client_discretion"),
            sa.column("cost_phase"), sa.column("notes"), sa.column("sort_order"),
        ),
        [
            {**{k: v for k, v in row.items()}, "currency": "EUR"}
            for row in SEED
        ],
    )


def downgrade() -> None:
    op.drop_table("provisional_allowances")
