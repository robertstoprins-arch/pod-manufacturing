import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Integer, JSON, String, Text, Uuid,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_org_id = Column(String(255), unique=True, nullable=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    projects = relationship("Project", back_populates="organization")
    offcuts = relationship("OffcutRegister", back_populates="organization", foreign_keys="OffcutRegister.organization_id")


class LibraryVersion(Base):
    __tablename__ = "library_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(50), nullable=False, unique=True)
    released_at = Column(DateTime(timezone=True), default=_now)
    notes = Column(Text)

    materials = relationship("MaterialLibrary", back_populates="library_version")
    junctions = relationship("JunctionDetailLibrary", back_populates="library_version")


class JurisdictionProfile(Base):
    __tablename__ = "jurisdiction_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(50), nullable=False)
    country = Column(String(10), nullable=False)       # SE, NO, GB
    code = Column(String(20), nullable=False)           # BBR, TEK17, PARTL

    # Thermal targets
    u_value_wall = Column(Float, nullable=False)        # W/m²K
    u_value_roof = Column(Float, nullable=False)
    u_value_floor = Column(Float, nullable=False)
    u_value_window = Column(Float, nullable=False)
    airtightness_target = Column(Float, nullable=False) # ACH at 50Pa

    # Climate data for Glaser condensation checks (monthly mean temp + RH)
    climate_data = Column(JSON)

    # Structural zones — project-level override available
    snow_zone = Column(String(20))
    wind_zone = Column(String(20))
    radon_zone_source = Column(String(50))

    # Daylighting
    daylighting_wfr_min = Column(Float, default=0.10)   # window-to-floor ratio

    # Architectural constraints: ceiling heights, door widths, window sill heights, escape requirements
    # Stored as JSON so per-jurisdiction values are self-contained and easily readable in compliance skills
    arch_constraints = Column(JSON)

    projects = relationship("Project", back_populates="jurisdiction_profile")


class MaterialLibrary(Base):
    __tablename__ = "material_library"

    id = Column(Integer, primary_key=True, autoincrement=True)
    library_version_id = Column(Integer, ForeignKey("library_versions.id"), nullable=False)
    name = Column(String(255), nullable=False)
    manufacturer = Column(String(255))
    spec_ref = Column(String(255))

    # Thermal
    lambda_W_mK = Column(Float, nullable=False)         # thermal conductivity
    density_kg_m3 = Column(Float)
    cp_J_kgK = Column(Float)                            # specific heat capacity

    # Fire
    fire_euroclass = Column(String(10))                 # A1, A2, B, C, D, E, F

    # Carbon
    embodied_carbon_kgCO2e_per_kg = Column(Float)

    # Procurement
    price_per_unit = Column(Float)
    unit = Column(String(20))                           # m2, m3, kg, m, pcs
    currency = Column(String(3), default="EUR")
    supplier_ref = Column(String(255))

    # Evidence / supplier trust layer
    supplier_name    = Column(String(255))
    supplier_url     = Column(Text)
    datasheet_url    = Column(Text)
    dop_url          = Column(Text)
    price_source_url = Column(Text)
    price_checked_at = Column(Date)
    evidence_status   = Column(String(20), default="missing", nullable=False)
    evidence_notes    = Column(Text)
    evidence_category = Column(String(40), nullable=False, default="manufactured_product")

    # Extra metadata: default_role, default_thickness_mm, include_in_u_value, sd_value_m, category
    properties = Column(JSON)

    # Immutable versioning: new record per change, never update existing
    superseded_by = Column(Integer, ForeignKey("material_library.id"), nullable=True)

    library_version = relationship("LibraryVersion", back_populates="materials")
    layers = relationship("BuildUpLayer", back_populates="material")
    offcuts = relationship("OffcutRegister", back_populates="material")
    prices = relationship("MaterialPrice", back_populates="material", order_by="MaterialPrice.id")


class JunctionDetailLibrary(Base):
    __tablename__ = "junction_detail_library"

    id = Column(Integer, primary_key=True, autoincrement=True)
    library_version_id = Column(Integer, ForeignKey("library_versions.id"), nullable=False)
    code = Column(String(50), nullable=False)           # e.g. "EAVE-SE-001"
    type = Column(String(50), nullable=False)           # eave, corner, cill, party_wall, etc.
    build_up_type = Column(String(50))
    insulation_continuity = Column(Boolean, default=True)
    thermal_break_present = Column(Boolean, default=False)
    min_outboard_insulation_mm = Column(Float)
    psi_value_W_mK = Column(Float, nullable=False)
    psi_source = Column(String(30), nullable=False)     # EN_ISO_14683, SVEBY, SINTEF, FEA
    cert_ref = Column(String(255))
    passivhaus_flag = Column(Boolean, default=False)

    library_version = relationship("LibraryVersion", back_populates="junctions")
    junctions = relationship("Junction", back_populates="detail")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(Text)

    # Both pinned at project creation — never change after that
    jurisdiction_profile_id = Column(Integer, ForeignKey("jurisdiction_profiles.id"), nullable=False)
    library_version_id = Column(Integer, ForeignKey("library_versions.id"), nullable=False)

    created_by = Column(String(255), nullable=True)   # Clerk user_id
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    organization = relationship("Organization", back_populates="projects")
    jurisdiction_profile = relationship("JurisdictionProfile", back_populates="projects")
    pods = relationship("Pod", back_populates="project")
    drawings = relationship("Drawing", back_populates="project")


class Pod(Base):
    __tablename__ = "pods"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    geometry_2d = Column(JSON)

    # Points to the active load set (nullable — set after SE provides loads or software defaults)
    structural_load_set_id = Column(
        Integer,
        ForeignKey("structural_load_sets.id", use_alter=True, name="fk_pod_structural_load_set"),
        nullable=True,
    )

    project = relationship("Project", back_populates="pods")
    elements = relationship("Element", back_populates="pod")
    junctions = relationship("Junction", back_populates="pod")
    compliance_runs = relationship("ComplianceRun", back_populates="pod")
    production_runs = relationship("ProductionRun", back_populates="pod")
    load_sets = relationship(
        "StructuralLoadSet",
        back_populates="pod",
        foreign_keys="StructuralLoadSet.pod_id",
    )


class StructuralLoadSet(Base):
    __tablename__ = "structural_load_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pod_id = Column(Uuid(as_uuid=True), ForeignKey("pods.id"), nullable=False)

    # Source tells us whether these are SE-provided or software defaults
    source = Column(String(30), nullable=False)         # SE_PROVIDED, SOFTWARE_DEFAULT, SPAN_TABLE
    se_reference = Column(String(255))
    se_name = Column(String(255))
    se_certification = Column(String(255))              # e.g. Sentral Godkjenning number (NO)

    # Loads in kN/m² unless noted
    wind_pressure_kNm2 = Column(Float)
    floor_imposed_kNm2 = Column(Float)
    roof_snow_kNm2 = Column(Float)                     # from jurisdiction snow_zone default or SE override
    roof_imposed_kNm2 = Column(Float)
    party_wall_load_kNm = Column(Float)                 # kN/m (line load)
    ground_bearing_kNm2 = Column(Float)
    point_loads = Column(JSON)                         # list of {x, y, load_kN, description}

    pod = relationship("Pod", back_populates="load_sets", foreign_keys=[pod_id])


class Element(Base):
    __tablename__ = "elements"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pod_id = Column(Uuid(as_uuid=True), ForeignKey("pods.id"), nullable=False)
    type = Column(String(30), nullable=False)           # ExternalWall, Floor, Roof, Partition, Opening
    geometry = Column(JSON)
    exposure = Column(String(30))                       # exposed, semi-exposed, internal
    adjacencies = Column(JSON)
    area_gross_m2 = Column(Float)
    area_net_m2 = Column(Float)
    perimeter_m = Column(Float)

    pod = relationship("Pod", back_populates="elements")
    build_ups = relationship("BuildUp", back_populates="element")
    drawings = relationship("Drawing", back_populates="element")


class BuildUp(Base):
    __tablename__ = "build_ups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    element_id = Column(Uuid(as_uuid=True), ForeignKey("elements.id"), nullable=True)  # nullable for library templates
    name = Column(String(255))
    build_up_type = Column(String(50))                  # closed_panel, open_panel, SIP, CLT
    element_type = Column(String(30))                   # ExternalWall | Floor | Roof
    scope = Column(String(20), default="library")       # library | project
    status = Column(String(20), default="draft")        # draft | approved | superseded
    notes = Column(Text)
    u_value = Column(Float, nullable=True)               # cached W/m²K — updated on save
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    element = relationship("Element", back_populates="build_ups")
    layers = relationship("BuildUpLayer", back_populates="build_up", order_by="BuildUpLayer.position_order")


class BuildUpLayer(Base):
    __tablename__ = "build_up_layers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    build_up_id = Column(Integer, ForeignKey("build_ups.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("material_library.id"), nullable=False)
    thickness_mm = Column(Float, nullable=False)
    position_order = Column(Integer, nullable=False)    # 1 = innermost (INSIDE → OUTSIDE)
    properties = Column(JSON)                          # role, framing_fraction, include_in_u_value, sd_value_m

    build_up = relationship("BuildUp", back_populates="layers")
    material = relationship("MaterialLibrary", back_populates="layers")


class Junction(Base):
    __tablename__ = "junctions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pod_id = Column(Uuid(as_uuid=True), ForeignKey("pods.id"), nullable=False)
    type = Column(String(50))                           # eave, corner, cill, party_wall, etc.
    element_ids = Column(JSON)                         # list of element UUIDs meeting at this junction
    psi_value_W_mK = Column(Float)
    psi_source = Column(String(30))
    linear_metres_m = Column(Float)
    delta_u_W_m2K = Column(Float)                       # ψ × L / A contribution
    detail_ref = Column(String(255))
    detail_id = Column(Integer, ForeignKey("junction_detail_library.id"), nullable=True)

    pod = relationship("Pod", back_populates="junctions")
    detail = relationship("JunctionDetailLibrary", back_populates="junctions")


class ComplianceRun(Base):
    __tablename__ = "compliance_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pod_id = Column(Uuid(as_uuid=True), ForeignKey("pods.id"), nullable=False)
    input_hash = Column(String(64), nullable=False)     # SHA-256 of all inputs + library_version_id + jurisdiction_profile_id
    run_at = Column(DateTime(timezone=True), default=_now)
    status = Column(String(10), nullable=False)         # PASS, FAIL, OVERRIDE
    override_user_id = Column(String(255))
    override_reason = Column(Text)
    override_at = Column(DateTime(timezone=True))
    results = Column(JSON)                             # per-skill results list

    pod = relationship("Pod", back_populates="compliance_runs")
    production_runs = relationship("ProductionRun", back_populates="compliance_run")


class ProductionRun(Base):
    __tablename__ = "production_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pod_id = Column(Uuid(as_uuid=True), ForeignKey("pods.id"), nullable=False)
    input_hash = Column(String(64), nullable=False)
    run_at = Column(DateTime(timezone=True), default=_now)
    gated_on_compliance_run_id = Column(Integer, ForeignKey("compliance_runs.id"), nullable=True)
    status = Column(String(20), nullable=False)         # PENDING, RUNNING, COMPLETE, FAILED

    pod = relationship("Pod", back_populates="production_runs")
    compliance_run = relationship("ComplianceRun", back_populates="production_runs")


class Drawing(Base):
    __tablename__ = "drawings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    element_id = Column(Uuid(as_uuid=True), ForeignKey("elements.id"), nullable=True)
    code = Column(String(50), nullable=False)           # ISO 19650 code
    type = Column(String(50))
    rev = Column(String(10))
    suitability_code = Column(String(5))                # S0–S7
    status = Column(String(20))                         # WIP, PRELIMINARY, CONSTRUCTION, MANUFACTURE, AS_BUILT
    hash = Column(String(64))                           # content hash for change detection
    s3_key = Column(String(1000))
    issued_at = Column(DateTime(timezone=True))
    superseded_by = Column(Uuid(as_uuid=True), ForeignKey("drawings.id"), nullable=True)

    project = relationship("Project", back_populates="drawings")
    element = relationship("Element", back_populates="drawings")


class PodSpec(Base):
    __tablename__ = "pod_specs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    geometry = Column(JSON, nullable=False)
    wall_build_up_id = Column(Integer, ForeignKey("build_ups.id"), nullable=True)
    floor_build_up_id = Column(Integer, ForeignKey("build_ups.id"), nullable=True)
    roof_build_up_id = Column(Integer, ForeignKey("build_ups.id"), nullable=True)
    status = Column(String(20), default="draft")
    client_project_id = Column(String(50), nullable=True)
    # Customer finish / furniture / package selections.
    # Schema: {"packages": [{"package_id": 1, "quantity": 1}],
    #          "items":    [{"item_id": 7, "quantity": 1,
    #                        "unit_cost_override": null, "included": true}]}
    selected_finishes_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    wall_build_up  = relationship("BuildUp", foreign_keys=[wall_build_up_id])
    floor_build_up = relationship("BuildUp", foreign_keys=[floor_build_up_id])
    roof_build_up  = relationship("BuildUp", foreign_keys=[roof_build_up_id])


class OffcutRegister(Base):
    __tablename__ = "offcut_register"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    piece_id = Column(String(100), nullable=False)
    material_id = Column(Integer, ForeignKey("material_library.id"), nullable=False)
    length_mm = Column(Float, nullable=False)
    width_mm = Column(Float)
    available = Column(Boolean, default=True)
    reserved_for_project_id = Column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    organization = relationship("Organization", back_populates="offcuts", foreign_keys=[organization_id])
    material = relationship("MaterialLibrary", back_populates="offcuts")


class ProvisionalAllowance(Base):
    __tablename__ = "provisional_allowances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)   # envelope, roof, finishes, electrical, furniture, sanitary, client_discretion
    unit = Column(String(20), nullable=False)        # each, m2, lm, set
    default_unit_rate = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")
    # How quantity is determined: manual | opening_count_window | opening_count_door |
    # opening_count_rooflight | floor_area | wall_ceiling_area
    quantity_source = Column(String(50), nullable=False, default="manual")
    default_quantity = Column(Float, nullable=False, default=0)
    is_included_by_default = Column(Boolean, nullable=False, default=False)
    is_client_discretion = Column(Boolean, nullable=False, default=False)
    cost_phase = Column(String(50), nullable=False)  # base_envelope | interior_finish | optional_addons
    notes = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)


class MaterialPrice(Base):
    __tablename__ = "material_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey("material_library.id", ondelete="CASCADE"), nullable=False)

    # e.g. retail_lv, trade_lv, manufacturer_direct, import_benchmark, manual_override
    price_type = Column(String(30), nullable=False)
    price_per_unit = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)             # m2, lm, m3, pcs — must match MTO unit
    currency = Column(String(3), nullable=False, default="EUR")
    supplier_ref = Column(String(255))
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    material = relationship("MaterialLibrary", back_populates="prices")


class AccountSettings(Base):
    __tablename__ = "account_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Markup / pricing
    default_markup_percent = Column(Float, nullable=False, default=50.0)
    currency = Column(String(3), nullable=False, default="EUR")
    vat_rate_percent = Column(Float, nullable=False, default=21.0)
    # "excluded" = prices shown ex-VAT, VAT added on top
    # "included" = prices already include VAT
    vat_mode = Column(String(20), nullable=False, default="excluded")
    # Round selling price to nearest N (0 = no rounding)
    round_to_nearest = Column(Integer, nullable=False, default=100)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)


# ── Finish & Furniture Catalogue ──────────────────────────────────────────────
#
# Customer-facing catalogue: cladding options, flooring, sanitaryware, furniture,
# lighting etc. Separate from the technical material evidence register.
#
# CATEGORY values:
#   external_cladding | internal_paint | internal_timber_finish | flooring
#   sanitaryware | toilet | vanity_unit | kitchenette | furniture_set
#   lighting | heating_visible | ventilation_visible | cctv_data
#   solar_battery | delivery_install | other
#
# IMAGE_APPROVAL_STATUS values (only approved ones shown in customer PDF):
#   missing | internal_reference_only | needs_approval
#   approved_for_customer_pdf | own_photo | licensed_stock | generated_placeholder
#
# QUANTITY_RULE values:
#   each | per_m2_floor_area | per_m2_wall_area | per_m2_roof_area
#   per_lm_perimeter | manual | package_fixed

class FinishCatalogueItem(Base):
    __tablename__ = "finish_catalogue_items"

    id   = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), unique=True, nullable=False)

    # Classification
    category = Column(String(60), nullable=False)

    # Names & descriptions
    name                 = Column(String(255), nullable=False)    # internal name
    customer_name        = Column(String(255))                    # marketing name shown to customer
    customer_description = Column(Text)                           # shown on product card
    internal_description = Column(Text)                           # notes for manufacturer only

    # Supplier / product info (internal — not shown in customer PDF)
    supplier_name     = Column(String(255))
    manufacturer      = Column(String(255))
    supplier_url      = Column(Text)           # always internal — purchasing reference only
    specification_url = Column(Text)           # public if specification_url_public=True
    datasheet_url     = Column(Text)           # public if specification_url_public=True
    specification_url_public = Column(Boolean, nullable=False, default=False)  # show spec link in client PDF

    # Image
    image_url             = Column(Text)
    image_alt_text        = Column(String(255))
    # none | placeholder | generated_placeholder | own_photo
    # licensed_stock | supplier_reference | supplier_approved | needs_review
    image_source_type     = Column(String(40), nullable=False, default="none")
    # missing | internal_reference_only | needs_approval
    # approved_for_customer_pdf | own_photo | licensed_stock | generated_placeholder
    image_approval_status = Column(String(40), nullable=False, default="missing")

    # Pricing
    unit             = Column(String(20))                          # m2, each, set, lm …
    unit_cost        = Column(Float)
    currency         = Column(String(3), default="EUR")
    # retail | trade | allowance | included
    price_type       = Column(String(30), default="allowance")
    default_quantity = Column(Float, default=1.0)
    # each | per_m2_floor_area | per_m2_wall_area | per_m2_roof_area
    # per_lm_perimeter | manual | package_fixed
    quantity_rule    = Column(String(40), default="each")

    # Visibility / inclusion flags
    included_by_default = Column(Boolean, nullable=False, default=False)
    customer_visible    = Column(Boolean, nullable=False, default=True)
    internal_only       = Column(Boolean, nullable=False, default=False)

    # Optional pod-type filter and package grouping (JSON arrays)
    suitable_pod_types = Column(JSON)   # e.g. ["studio", "garden_office"]
    package_tags       = Column(JSON)   # e.g. ["premium_finish", "base_package"]

    # Misc
    lead_time_note = Column(String(255))
    notes          = Column(Text)
    is_active      = Column(Boolean, nullable=False, default=True)
    created_at     = Column(DateTime(timezone=True), default=_now)
    updated_at     = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    package_items  = relationship("FinishPackageItem", back_populates="catalogue_item")


# ── Finish Packages ───────────────────────────────────────────────────────────
#
# Groups of catalogue items bundled into customer-selectable presets.
#
# PACKAGE_CATEGORY values:
#   office | guest_sleep | studio_living | bathroom | external_finish
#   internal_finish | furniture | lighting | solar | cctv | custom
#
# IMAGE_APPROVAL_STATUS: same set as FinishCatalogueItem

class FinishPackage(Base):
    __tablename__ = "finish_packages"

    id   = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), unique=True, nullable=False)

    name                 = Column(String(255), nullable=False)
    customer_name        = Column(String(255))
    customer_description = Column(Text)
    internal_description = Column(Text)

    # Optional filter: which pod type this package is suited to (null = all)
    pod_type = Column(String(60))

    # office | guest_sleep | studio_living | bathroom | external_finish
    # internal_finish | furniture | lighting | solar | cctv | custom
    package_category = Column(String(60), nullable=False)

    image_url             = Column(Text)
    image_approval_status = Column(String(40), nullable=False, default="missing")

    default_selected  = Column(Boolean, nullable=False, default=False)
    customer_visible  = Column(Boolean, nullable=False, default=True)
    is_active         = Column(Boolean, nullable=False, default=True)
    sort_order        = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    items = relationship(
        "FinishPackageItem",
        back_populates="package",
        cascade="all, delete-orphan",
        order_by="FinishPackageItem.id",
    )


class FinishPackageItem(Base):
    """Join table: one package → many catalogue items, with per-item overrides."""
    __tablename__ = "finish_package_items"

    id                      = Column(Integer, primary_key=True, autoincrement=True)
    finish_package_id       = Column(Integer, ForeignKey("finish_packages.id"), nullable=False)
    finish_catalogue_item_id= Column(Integer, ForeignKey("finish_catalogue_items.id"), nullable=False)

    quantity          = Column(Float, nullable=False, default=1.0)
    quantity_override = Column(Float)   # if set, overrides the catalogue item default_quantity
    is_required       = Column(Boolean, nullable=False, default=True)
    notes             = Column(Text)

    package       = relationship("FinishPackage",      back_populates="items")
    catalogue_item= relationship("FinishCatalogueItem",back_populates="package_items")
