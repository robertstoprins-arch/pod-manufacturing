"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. organizations
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    # 2. library_versions
    op.create_table(
        "library_versions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("version", sa.String(50), nullable=False, unique=True),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text),
    )

    # 3. jurisdiction_profiles
    op.create_table(
        "jurisdiction_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("country", sa.String(10), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("u_value_wall", sa.Float, nullable=False),
        sa.Column("u_value_roof", sa.Float, nullable=False),
        sa.Column("u_value_floor", sa.Float, nullable=False),
        sa.Column("u_value_window", sa.Float, nullable=False),
        sa.Column("airtightness_target", sa.Float, nullable=False),
        sa.Column("climate_data", JSONB),
        sa.Column("snow_zone", sa.String(20)),
        sa.Column("wind_zone", sa.String(20)),
        sa.Column("radon_zone_source", sa.String(50)),
        sa.Column("daylighting_wfr_min", sa.Float),
        sa.Column("arch_constraints", JSONB),
    )

    # 4. material_library (self-ref superseded_by added after table creation)
    op.create_table(
        "material_library",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("library_version_id", sa.Integer, sa.ForeignKey("library_versions.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("manufacturer", sa.String(255)),
        sa.Column("spec_ref", sa.String(255)),
        sa.Column("lambda_W_mK", sa.Float, nullable=False),
        sa.Column("density_kg_m3", sa.Float),
        sa.Column("cp_J_kgK", sa.Float),
        sa.Column("fire_euroclass", sa.String(10)),
        sa.Column("embodied_carbon_kgCO2e_per_kg", sa.Float),
        sa.Column("price_per_unit", sa.Float),
        sa.Column("unit", sa.String(20)),
        sa.Column("currency", sa.String(3)),
        sa.Column("supplier_ref", sa.String(255)),
        sa.Column("superseded_by", sa.Integer, sa.ForeignKey("material_library.id"), nullable=True),
    )

    # 5. junction_detail_library
    op.create_table(
        "junction_detail_library",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("library_version_id", sa.Integer, sa.ForeignKey("library_versions.id"), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("build_up_type", sa.String(50)),
        sa.Column("insulation_continuity", sa.Boolean),
        sa.Column("thermal_break_present", sa.Boolean),
        sa.Column("min_outboard_insulation_mm", sa.Float),
        sa.Column("psi_value_W_mK", sa.Float, nullable=False),
        sa.Column("psi_source", sa.String(30), nullable=False),
        sa.Column("cert_ref", sa.String(255)),
        sa.Column("passivhaus_flag", sa.Boolean),
    )

    # 6. projects
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text),
        sa.Column("jurisdiction_profile_id", sa.Integer, sa.ForeignKey("jurisdiction_profiles.id"), nullable=False),
        sa.Column("library_version_id", sa.Integer, sa.ForeignKey("library_versions.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # 7. pods — structural_load_set_id FK added as ALTER after structural_load_sets is created
    op.create_table(
        "pods",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("geometry_2d", JSONB),
        sa.Column("structural_load_set_id", sa.Integer, nullable=True),  # FK added below
    )

    # 8. structural_load_sets (references pods — pods must exist first)
    op.create_table(
        "structural_load_sets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("pod_id", UUID(as_uuid=True), sa.ForeignKey("pods.id"), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("se_reference", sa.String(255)),
        sa.Column("se_name", sa.String(255)),
        sa.Column("se_certification", sa.String(255)),
        sa.Column("wind_pressure_kNm2", sa.Float),
        sa.Column("floor_imposed_kNm2", sa.Float),
        sa.Column("roof_snow_kNm2", sa.Float),
        sa.Column("roof_imposed_kNm2", sa.Float),
        sa.Column("party_wall_load_kNm", sa.Float),
        sa.Column("ground_bearing_kNm2", sa.Float),
        sa.Column("point_loads", JSONB),
    )

    # Resolve the circular FK: pods.structural_load_set_id → structural_load_sets.id
    op.create_foreign_key(
        "fk_pod_structural_load_set",
        "pods",
        "structural_load_sets",
        ["structural_load_set_id"],
        ["id"],
    )

    # 9. elements
    op.create_table(
        "elements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pod_id", UUID(as_uuid=True), sa.ForeignKey("pods.id"), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("geometry", JSONB),
        sa.Column("exposure", sa.String(30)),
        sa.Column("adjacencies", JSONB),
        sa.Column("area_gross_m2", sa.Float),
        sa.Column("area_net_m2", sa.Float),
        sa.Column("perimeter_m", sa.Float),
    )

    # 10. build_ups
    op.create_table(
        "build_ups",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("element_id", UUID(as_uuid=True), sa.ForeignKey("elements.id"), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("build_up_type", sa.String(50)),
    )

    # 11. build_up_layers
    op.create_table(
        "build_up_layers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("build_up_id", sa.Integer, sa.ForeignKey("build_ups.id"), nullable=False),
        sa.Column("material_id", sa.Integer, sa.ForeignKey("material_library.id"), nullable=False),
        sa.Column("thickness_mm", sa.Float, nullable=False),
        sa.Column("position_order", sa.Integer, nullable=False),
        sa.Column("properties", JSONB),
    )

    # 12. junctions
    op.create_table(
        "junctions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("pod_id", UUID(as_uuid=True), sa.ForeignKey("pods.id"), nullable=False),
        sa.Column("type", sa.String(50)),
        sa.Column("element_ids", JSONB),
        sa.Column("psi_value_W_mK", sa.Float),
        sa.Column("psi_source", sa.String(30)),
        sa.Column("linear_metres_m", sa.Float),
        sa.Column("delta_u_W_m2K", sa.Float),
        sa.Column("detail_ref", sa.String(255)),
        sa.Column("detail_id", sa.Integer, sa.ForeignKey("junction_detail_library.id"), nullable=True),
    )

    # 13. compliance_runs
    op.create_table(
        "compliance_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("pod_id", UUID(as_uuid=True), sa.ForeignKey("pods.id"), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("override_user_id", sa.String(255)),
        sa.Column("override_reason", sa.Text),
        sa.Column("override_at", sa.DateTime(timezone=True)),
        sa.Column("results", JSONB),
    )

    # 14. production_runs
    op.create_table(
        "production_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("pod_id", UUID(as_uuid=True), sa.ForeignKey("pods.id"), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True)),
        sa.Column("gated_on_compliance_run_id", sa.Integer, sa.ForeignKey("compliance_runs.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
    )

    # 15. drawings
    op.create_table(
        "drawings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("element_id", UUID(as_uuid=True), sa.ForeignKey("elements.id"), nullable=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("type", sa.String(50)),
        sa.Column("rev", sa.String(10)),
        sa.Column("suitability_code", sa.String(5)),
        sa.Column("status", sa.String(20)),
        sa.Column("hash", sa.String(64)),
        sa.Column("s3_key", sa.String(1000)),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("superseded_by", UUID(as_uuid=True), sa.ForeignKey("drawings.id"), nullable=True),
    )

    # 16. offcut_register
    op.create_table(
        "offcut_register",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("piece_id", sa.String(100), nullable=False),
        sa.Column("material_id", sa.Integer, sa.ForeignKey("material_library.id"), nullable=False),
        sa.Column("length_mm", sa.Float, nullable=False),
        sa.Column("width_mm", sa.Float),
        sa.Column("available", sa.Boolean),
        sa.Column("reserved_for_project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_constraint("fk_pod_structural_load_set", "pods", type_="foreignkey")
    op.drop_table("offcut_register")
    op.drop_table("drawings")
    op.drop_table("production_runs")
    op.drop_table("compliance_runs")
    op.drop_table("junctions")
    op.drop_table("build_up_layers")
    op.drop_table("build_ups")
    op.drop_table("elements")
    op.drop_table("structural_load_sets")
    op.drop_table("pods")
    op.drop_table("projects")
    op.drop_table("junction_detail_library")
    op.drop_table("material_library")
    op.drop_table("jurisdiction_profiles")
    op.drop_table("library_versions")
    op.drop_table("organizations")
