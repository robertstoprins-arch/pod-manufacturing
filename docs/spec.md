# Pod Manufacturing Software — Full Specification
_Version 3.0 — Revised 2026-04-30. Incorporates staged MVP, compliance liability clarification, and commercial model._
_Supersedes spec v2.0_

---

## ⚠️ Compliance Liability Boundary

This software generates **pre-checks against selected rule profiles** and produces
**structured technical documentation for professional review**. It does not:

- Guarantee BBR or TEK17 compliance
- Replace the role of KA (Kontrollansvarig, Sweden) or ansvarlig prosjekterende (Norway)
- Issue certificates or approvals
- Substitute for project-specific professional sign-off

All outputs must be reviewed by the appointed responsible designer before use in
planning applications, building permits, or manufacturing. The software provides
**rule-based checks with traceable assumptions** — not regulatory approval.

All UI copy, PDF headers, and API responses must use this language:
- ✅ "Pre-check against BBR 2024 rule profile"
- ✅ "Technical pack for professional review"
- ✅ "Compliance evidence — requires KA/AP sign-off"
- ❌ "Compliant with BBR"
- ❌ "Auto-approved"
- ❌ "SE-ready without review"

---

## 1. Product Definition

A parametric factory-pack generator for closed-panel timber pods manufactured in
Latvia for the Swedish and Norwegian markets. The user enters pod dimensions,
openings, wall/roof/floor build-ups, and material data. The software generates a
quotation, material take-off, procurement export, frame/sheathing/insulation
drawings, cutting lists, and a controlled PDF factory pack — ready for professional
review and manufacturing.

**Structural system at MVP:** Closed-panel timber frame only.
SIPs, CLT, and LGS become system plugins in Phase 2.

**Primary markets:** Sweden (BBR) + Norway (TEK17).
**Manufacturing base:** Latvia — EU CE materials, Scandinavian export market.

---

## 1a. Phased Build Plan

### MVP v0.1 — Factory Pack Generator
_Goal: Generate a repeatable, sellable factory pack for one standard pod type._

| Feature | Detail |
|---------|--------|
| Parametric pod input | Width, length, height, roof type, wall/roof/floor build-up, openings |
| Element decomposition | Walls, roof, floor, openings with areas and perimeters |
| Material take-off | C24 framing, OSB, insulation, plasterboard, membranes, battens |
| 5 drawing types | Frame layout, sheathing, insulation, section detail, cutting list |
| Procurement export | CSV/Excel: material, quantity, supplier ref, unit cost |
| Quotation output | Material cost + labour allowance + margin + transport placeholder |
| U-value pre-check | Flat build-up check vs BBR/TEK17 target — evidence only, not approval |
| PDF factory pack | Controlled PDF with disclaimer, drawing register, revision |
| Manual review step | "Submit for professional review" gate — no automated approval claim |

**Commercial model at MVP:** Service-led. £1,500–3,500 first manufacturer setup.
£300–900 per generated factory pack. Manual assistance behind the scenes.

### Phase 2 / v1 — Engineering Pack
_Add once MVP has paying users._

- EC5 structural summary (per-element: stud sizing, lintels, racking, hold-downs)
- Glaser condensation check (monthly, climate-driven)
- Junction ψ-value library (SVEBY/SINTEF, EN ISO 14683)
- IFC export (ifcopenshell, IFC4 ADD2 — required for Norwegian public sector)
- QR labels on cut pieces
- Work order packs by factory station
- Offcut register (cross-project reuse)

**Commercial model:** Semi-SaaS. £300–750/month + usage fee per pack.

### Phase 3 / v2 — Full Compliance & Automation
_Add once Phase 2 is stable._

- Full BBR/TEK17 compliance dashboard (all 13 checks, traffic light)
- Swedish Klimatdeklaration (A1–A5, Boverket format)
- Energideklaration inputs
- CNC BTL export (Hundegger/Weinmann/Randek)
- Client portal
- Factory scheduling (Takt-time, assembly graph)
- ACC/CDE publishing (ISO 19650)

**Commercial model:** Organisation licence + API access. Enterprise contracts.

---

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                              │
│                                                                      │
│  Parametric Form          Compliance Dashboard      Drawing Register │
│  + Live SVG Preview       (13 checks, traffic light) + IFC download  │
│  [Konva canvas v1.1]                                                 │
│                           3D Viewer (Three.js)                       │
│                           assembled / exploded / click-to-buildup    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  REST + SSE (progress streaming)
┌──────────────────────────────▼──────────────────────────────────────┐
│                    FastAPI  +  Celery  +  Redis                      │
│           Content-hash keyed tasks · Parallel · Retry               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
         ┌─────────────────────┼──────────────────────┐
         ▼                     ▼                      ▼
   ┌───────────┐        ┌────────────┐        ┌────────────────┐
   │ GEOMETRY  │        │ COMPLIANCE │        │  PRODUCTION    │
   │           │        │            │        │                │
   │ Element   │        │ U-value    │        │ MTO            │
   │ Decomposer│        │ + ψ-values │        │ 1D Cut Opt.    │
   │           │        │ Glaser     │        │ 2D Sheet Nest  │
   │ Build-up  │        │ Fire (×3)  │        │ Membrane Plan  │
   │ Resolver  │        │ Structural │        │ Fixing Sched.  │
   │           │        │ EC5 Design │        │ Drawing Gen.   │
   │ Junction  │        │ Acoustic   │        │  (10 types)    │
   │ Resolver  │        │ Ventilat.  │        │ IFC Exporter   │
   │ ψ Library │        │ Airtight.  │        │ Assembly Graph │
   │           │        │ Daylighting│        │ Takt-time      │
   │           │        │ Radon/Moist│        │ Transport      │
   │           │        │ Embodied C │        │ Work Orders    │
   │           │        │ A1–B6 LCA  │        │ Klimatdekl.    │
   │           │        │ Perf.Optim.│        │ Energidekl.    │
   └───────────┘        └────────────┘        └────────────────┘
         │                     │                      │
         └─────────────────────┼──────────────────────┘
                               ▼
          ┌──────────────────────────────────────────┐
          │              DATA LAYER                   │
          │  Postgres (normalized, versioned schema)  │
          │  Redis (Celery broker + task cache)        │
          │  Hetzner Object Storage (S3-compatible)   │
          └──────────────────────────────────────────┘
```

**Orchestrator:** Celery + Redis. Content-hash keyed tasks. Parallel tracks.
Compliance failures block production track unless overridden with logged justification.

---

## 3. Data Model

```
Organization { id, name, slug, created_at }

Project {
  id, organization_id FK
  name, address, jurisdiction_profile_id FK (pinned at creation)
  library_version_id FK (pinned at creation)
  created_at, updated_at
}

JurisdictionProfile { id, version, country, code (BBR|TEK17|PARTL),
  u_value_wall, u_value_roof, u_value_floor, u_value_window,
  climate_data JSONB (monthly temp/RH for Glaser),
  snow_zone, wind_zone, radon_zone_source,
  airtightness_target, daylighting_wfr_min }

LibraryVersion { id, version, released_at, notes }

MaterialLibrary { id, library_version_id FK, name, manufacturer,
  spec_ref, lambda_W_mK, density_kg_m3, cp_J_kgK,
  fire_euroclass, embodied_carbon_kgCO2e_per_kg,
  price_per_unit, unit, currency, supplier_ref,
  superseded_by FK (null if current) }

JunctionDetailLibrary { id, library_version_id FK, code, type,
  build_up_type, insulation_continuity, thermal_break_present,
  min_outboard_insulation_mm, psi_value_W_mK,
  psi_source (EN_ISO_14683|SVEBY|SINTEF|FEA),
  cert_ref, passivhaus_flag }

Pod { id, project_id FK, name, geometry_2d JSONB,
  structural_load_set_id FK (nullable) }

StructuralLoadSet { id, pod_id FK,
  source (SE_PROVIDED|SOFTWARE_DEFAULT|SPAN_TABLE),
  se_reference, se_name, se_certification,
  wind_pressure_kNm2, floor_imposed_kNm2,
  roof_snow_kNm2, roof_imposed_kNm2,
  party_wall_load_kNm, ground_bearing_kNm2,
  point_loads JSONB }

Element { id, pod_id FK, type (ExternalWall|Floor|Roof|Partition|Opening),
  geometry JSONB, exposure, adjacencies JSONB, area_gross_m2,
  area_net_m2, perimeter_m }

BuildUp { id, element_id FK, name, build_up_type }

BuildUpLayer { id, build_up_id FK, material_id FK,
  thickness_mm, position_order, properties JSONB }

Junction { id, pod_id FK, type, element_ids JSONB,
  psi_value_W_mK, psi_source, linear_metres_m,
  delta_u_W_m2K, detail_ref, detail_id FK }

ComplianceRun { id, pod_id FK, input_hash, run_at,
  status (PASS|FAIL|OVERRIDE),
  override_user_id FK, override_reason, override_at,
  results JSONB }

ProductionRun { id, pod_id FK, input_hash, run_at,
  gated_on_compliance_run_id FK, status }

Drawing { id, project_id FK, element_id FK (nullable),
  code, type, rev, suitability_code (S0-S7),
  status (WIP|PRELIMINARY|CONSTRUCTION|MANUFACTURE|AS_BUILT),
  hash, s3_key, issued_at, superseded_by FK }

OffcutRegister { id, organization_id FK, project_id FK,
  piece_id, material_id FK, length_mm, width_mm,
  available, reserved_for_project_id FK (nullable) }
```

---

## 4. Envelope Scope

All six envelope elements covered at MVP:

| Element | Default build-up |
|---------|-----------------|
| External wall | Closed-panel timber frame, inside-out spec (see §5) |
| Roof | Warm flat (inverted) as default; pitched cold roof as variant |
| Ground floor | Suspended timber cassette (default) or concrete slab |
| Intermediate floor | Timber cassette with acoustic quilt |
| Openings — windows | Triple glazed default; manufacturer Uw per EN ISO 10077-1 |
| Openings — doors | Insulated composite default; Ud from manufacturer |
| Openings — ventilation | MVHR supply/extract; grille sizes from ventilation skill |

---

## 5. Skills Specification

### 5.1 Element Decomposer
Input: parametric pod model (width, length, height, floors, openings)
Output: typed element list with geometry, exposure, adjacencies

Exposure lookup: Swedish SMHI driving rain zones (primary),
Norwegian Met Institute zones (secondary).

### 5.2 Build-up Resolver
Input: element + jurisdiction profile + user preference
Output: validated layered build-up with material_id FKs

Default external wall (inside out):
1. Plasterboard 12.5mm
2. Service void (battens 25×50 @ 600cc)
3. VCL (Intello Plus, sd ≥ 10m)
4. OSB3 sheathing 11mm
5. C24 stud 38×140 @ 600cc + PIR 140mm between
6. PIR 50mm continuous outboard
7. Breather membrane (sd ≤ 0.1m)
8. Treated batten 25mm (drained cavity)
9. Treated counter-batten 38mm
10. Cladding (per project)

Stud size updated by EC5 Structural Design skill output if SE loads provided.

Validators (blocking):
- VCL warm-side of insulation centroid
- Breather cold-side, no vapour-tight layer outboard
- DPC at sole plate
- Service void inboard of airtight layer
- Cavity drained and ventilated

### 5.3 EC5 Structural Design Skill ← NEW
Input: elements + StructuralLoadSet (SE-provided or default span tables)
Output: stud sizes, lintel schedule, racking design, hold-down forces

Calculations (EC5 + EN 1995-1-1):
- Stud compression (EC5 6.3.2) — axial + buckling
- Stud bending under wind (EC5 6.1.6) — out-of-plane
- Combined bending + compression (EC5 6.2.4) — interaction formula
- Racking resistance (EC5 Annex B) — OSB panel shear
- Floor joist sizing — span tables (Trä-guiden SE / SINTEF NO)
- Lintel/header sizing — span tables per clear opening + bearing
- Hold-down forces — wind uplift at corners

Output drawing: Structural Summary (type "SE", suitability S4 — for SE stamp)

Library: handcalcs (Python) renders calculations as readable formulas in PDF.
SE reviews summary, stamps, returns. Software locks structural inputs.

SE sign-off required flag: triggered when pod width > 4.8m, span > 3.6m,
or point loads present.

### 5.4 Junction Resolver
Input: elements + adjacencies
Output: junction list with ψ-values from JunctionDetailLibrary

Junction types: SolePlate, Eave, Parapet, ExternalCorner, InternalCorner,
WindowHead, WindowCill, WindowJamb, DoorHead, DoorThreshold,
IntermediateFloor, RidgeParty.

Corner detection: cold corner (ψ ≈ 0.10–0.15) vs warm/California corner
(ψ ≈ 0.02–0.04) — detected from build-up spec, conservative default.

ψ-value feeds into effective U-value: U_eff = U_flat + Σ(ψ × L) / A

### 5.5 Material Take-off
Input: elements + build-ups + structural outputs
Output: raw quantities by material_id with uplift factors

Includes: C24 (by section size), PIR (by thickness), OSB3, plasterboard,
VCL membrane, breather membrane, tapes, cavity battens, fixings.

### 5.6 1D Cutting Optimiser (Timber)
Input: required cut lengths + grade + treatment
Stock: C24 lengths 3.0–6.0m (configurable)
Algorithm: First-Fit-Decreasing (MVP); HiGHS ILP hook (v1.1)
Output: cutting plan per stock length, kerf 3mm, offcut register ≥ 600mm
Labels: LB2501-W-A1-S07 format
Export: PDF cutting list + BTL file (CNC-ready, Hundegger/Weinmann/Randek)
QR codes: each piece label carries QR linking to installation drawing

### 5.7 2D Sheet Nesting
Input: rectangular parts with grain direction
Stock: configurable sheet sizes
Algorithm: guillotine bottom-left-fill (OR-Tools); skyline upgrade hook
Timeout: 10 seconds, fallback to greedy if exceeded
Output: nesting visualisation per sheet, waste %, offcut register,
labelled parts, DXF for CNC router

### 5.8 Cross-Project Offcut Pool
Before cutting: check OffcutRegister for reusable pieces ≥ required length
from same organization. Reserve matching offcuts. Report savings.

### 5.9 Membrane Roll Planner
Input: element dimensions + lap allowances
Output: roll cuts per element, tape/staple/grommet totals
Drawings: membrane layout with tape runs and grommet positions

### 5.10 Fixing Schedule
Input: build-ups + element geometry + structural hold-down forces
Output: fixing schedule per layer interface
Source: Eurocode 5 + TRADA + manufacturer guidance, encoded as data
Updated by EC5 structural output (sole plate fixings, hold-downs)

### 5.11 Drawing Generators (10 types)
All emit SVG (canonical) + DXF (CNC/CAD) + PDF (issue).

1. Frame Layout — stud positions, plates, noggins, openings, sizes
2. Insulation Cut Plan — PIR pieces numbered, matching cutting list IDs
3. Membrane Layout — sheets, laps, tape runs, grommets
4. Sheathing Layout — OSB/ply panels, fixing centres, panel joints offset
5. Section Detail — layered section with dimensional ladder, call-outs
6. Junction Details — corner, head, cill, eave (parametric library)
7. Lifting Plan — COG, lift points, mass, sling angles
8. Structural Summary — EC5 outputs, stud/lintel schedule, SE stamp box
9. IFC Export — not a drawing, but registered in Drawing Register
10. Klimatdeklaration — A1–A5 carbon declaration (WeasyPrint template)

Title block (all drawings):
```
PROJECT / CLIENT / ADDRESS
DRAWING TITLE / CODE (ISO 19650) / TYPE / ROLE
REVISION / SUITABILITY CODE / DATE / SCALE
DRAWN / CHECKED / APPROVED
INPUT HASH (parametric model fingerprint)
```

Suitability codes: S0 WIP → S3 For Review → S4 Approved →
S5 For Construction → S6 For Manufacture → S7 As-Built

Disclaimer (on S5 and above):
"This document has been prepared by Top-R Solutions Ltd using parametric
design software. All dimensions to be verified on site before fabrication.
Structural calculations require review and certification by a licensed
structural engineer prior to commencement of works. Compliance with local
building regulations (BBR, TEK17) is the responsibility of the appointed
Kontrollansvarig or Ansvarlig prosjekterende. © Top-R Solutions Ltd."

### 5.12 IFC Exporter
Tool: ifcopenshell (Python)
Schema: IFC4 ADD2
Elements: IfcWall, IfcSlab, IfcRoof, IfcWindow, IfcDoor
Materials: IfcMaterialLayerSet (lambda from MaterialLibrary)
Geometry: IfcExtrudedAreaSolid
Output: .ifc file → S3 → registered in Drawing Register (type BIM, S6)

Scandinavia compliance: IFC4 ADD2 required by Statsbygg (NO) and
BIM Alliance (SE). CE-marking documentation attachable as IfcDocumentReference.

### 5.13 Compliance Skills (parallel, 13 checks)

Each returns: { status, value, target, clause, headroom, fix_suggestion }

1. U-value (effective) — BS EN ISO 6946 + ψ corrections vs BBR/TEK17
2. Condensation (Glaser) — BS EN ISO 13788, monthly, climate-data driven
3. Fire — Reaction to fire — EN 13501-1 Euroclass per exposed material
4. Fire — External cladding — height-dependent class (D-s2,d2 / A2 above 8m)
5. Fire — Compartmentation — cavity barriers, fire stops at junctions
6. Fire — Escape — window opening area ≥ 0.33m², min 450mm height
7. Structural EC5 — stud/joist/racking checks (see §5.3)
8. Acoustic — mass-spring-mass estimate vs BBR/TEK17 separating elements
9. Ventilation — BBR ch.6 / TEK17 §13 — MVHR spec if airtightness target met
10. Airtightness — q50 target check (1.5 BBR default / 0.6 Passivhaus preset)
11. Daylighting — window-to-floor ratio ≥ 10% per habitable room
12. Ground moisture / Radon — zone lookup (SGU map SE / NGU map NO)
13. Embodied carbon — A1–B6 lifecycle vs RICS WLCA bands

Performance optimiser: for each element, shows headroom vs target
and minimum build-up change to reach next tier (standard → NZE → Passivhaus)
with material cost delta per m².

### 5.14 A1–B6 Lifecycle Carbon
A1–A3: material embodied carbon (from MaterialLibrary.embodied_carbon)
A4: transport Latvia → delivery address (pod weight × distance × 0.062 kgCO₂/t·km)
A5: factory assembly energy (kWh × grid carbon factor, configurable)
B4: replacement carbon (membrane 25yr, cladding 40yr cycle)
B6: operational energy (heat loss × degree-days × fuel carbon factor)

Output: Klimatdeklaration PDF (Swedish mandatory format, A1–A5)
        Energideklaration inputs (kWh/m²/year for Swedish energy certificate)

### 5.15 Element Value / Cost Breakdown
Material cost: MTO quantities × MaterialLibrary.price_per_unit
Labour cost: takt-time per station × configurable labour rate (€/hr)
Transport cost: pod weight × distance × rate (€/t·km)
Total pod cost / cost per m²

Outputs: Quotation document + Procurement list (CSV/Excel, supplier SKU-ready)

### 5.16 Assembly Graph Builder
Input: build-ups + fixing schedule
Output: directed graph of operations with QA hold-points

Each node: prerequisites, parts, fixings, tools, std_time_min,
qa_holdpoint (visual check, blocker), H&S notes

Topological sort → method statement
QA hold-points → sign-off checklists

### 5.17 Takt-time Calculator
Sum operation times by station, apply efficiency factor (0.75 default)
Expose bottleneck station. Used for capacity planning and delivery date estimation.

### 5.18 Transport Sizer
Input: pod outer dimensions + total mass
Output: vehicle profile, STGO/TSFS category, escort requirements

Jurisdictions: Sweden TSFS (Transportstyrelsen), Norway SVV, UK STGO
Flag: > 4.95m wide or > 25.25m long (SE/NO abnormal load thresholds)

### 5.19 Drawing Register Agent
Every output gets an ISO 19650 code:
{Project}-{Originator}-{Volume}-{Level}-{Type}-{Role}-{Number}
LB2501-TPR-W01-XX-DR-A-1001

Stored as database row. Content-hashed — rev only bumps on real change.
Searchable by element, status, suitability, rev, type, hash.

### 5.20 Work Order Compiler (by station)
Frame Station: frame layout + C24 cutting list (PDF + BTL) + structural summary + QA sheet
Insulation Station: insulation cut plan + PIR nesting + install drawing
Membrane Station: membrane layout + tape/grommet schedule + airtightness holdpoint
Sheathing Station: sheathing layout + ply nesting + nail schedule
External Station: cavity batten layout + cladding schedule + fire-stop schedule
Internals Station: service void + plasterboard layout + screw schedule
Final QA: complete checksheet, photo evidence at each holdpoint

### 5.21 Swedish Klimatdeklaration PDF
Mandatory since 2022 for all new Swedish buildings.
Format: Boverket-specified A1–A5 carbon declaration.
Auto-generated from LCA data. WeasyPrint template. ~2 days effort.

### 5.22 CDE Publisher
S3 + CloudFront (MVP static site). ACC / Autodesk Construction Cloud (v1.1).
Webhook on rev change → notify procurement, factory manager.

---

## 6. Additional Features (all confirmed for MVP or v1.1)

### MVP (alongside core pipeline)

**QR Codes on Cut Lists**
Each labelled piece (LB2501-W-A1-S07) carries a QR code in the cutting list.
Factory worker scans → sees installation drawing for that piece.
Library: `qrcode` (Python). ~1 week.

**Procurement List Export**
From MTO: generate purchase order CSV/Excel.
Columns: material_name, sku, quantity, unit, supplier_ref, supplier_name,
unit_price, total_price, notes.
Ready to send to Latvian supplier. ~3 days.

**Offcut Register Reuse**
Cross-project offcut pool per organization.
Before cutting: check register for reusable offcuts ≥ required length.
Reports: material saved (m and €) per project. ~1 week.

**Energideklaration (Swedish Energy Performance Certificate)**
Annual energy demand kWh/m²/year from B6 LCA calculation.
Required for all Swedish dwellings. ~1 week.

**EC5 Structural Design** (see §5.3)
SE provides loads → software sizes studs, lintels, racking → SE stamps.

### v1.1

**Konva Canvas** — freehand 2D pod drawing (replaces parametric form)
**Client Portal** — read-only: compliance status, drawings, delivery date
**Factory Scheduling Board** — Kanban by station, takt-time derived dates
**Supplier Price Feed** — Excel import first, API later
**Variation Tracking** — change after issue → delta drawings + cost/carbon impact
**Tablet Rollout** — scan QR on part → digital sign-off replaces paper
**BTL Export** — already designed in cutting optimiser; activate for CNC machines
**2D FEA Hook** — NumPy/SciPy steady-state heat flow for non-standard junctions
**SIPs/CLT/LGS** — structural system plugins

---

## 7. Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | React + TypeScript + Vite | — |
| UI components | shadcn/ui + Tailwind | — |
| Data fetching | TanStack Query | — |
| 3D viewer | Three.js | Data from API params, not IFC |
| 2D canvas (v1.1) | Konva.js | — |
| Backend | Python + FastAPI | — |
| Task queue | Celery + Redis | Replaces custom DAG |
| Geometry | Shapely + ezdxf | Note: Y-up/Y-down transform helper required |
| Structural calcs | Custom EC5 + handcalcs | — |
| Optimisation | OR-Tools (1D+2D) | 10s timeout, greedy fallback |
| BIM export | ifcopenshell | IFC4 ADD2 |
| PDF generation | WeasyPrint + pypdf | WeasyPrint for all generation, pypdf for merge only |
| Templating | Jinja2 | Spec text, method statements, declarations |
| QR codes | qrcode (Python) | — |
| Database | Postgres + normalized schema | Library versions pinned per project |
| Storage | Hetzner Object Storage | S3-compatible, EU data sovereignty |
| Auth | Clerk | Organization-scoped, SAML SSO in v1.1 |
| Deployment | Docker Compose → Hetzner VPS | See §9 |

---

## 8. Drawing Register — Status Codes (ISO 19650)

| Code | Name | Use |
|------|------|-----|
| S0 | Work in Progress | Internal only, never issued |
| S3 | For Review and Comment | KA / SE / client review |
| S4 | For Stage Approval | Formal sign-off (SE stamp) |
| S5 | For Construction | Issued for Construction |
| S6 | For Manufacture | Issued for Manufacture — factory packs |
| S7 | As-Constructed | Record drawings |

Revision numbering: P01, P02 (preliminary S0–S4) → C01, C02 (construction S5–S6)
Disclaimer text: on S5 and above only (see §5.11)

---

## 9. Deployment Plan

### Phase 1 — MVP (Weeks 1–18)
Single Hetzner VPS (~€50/month):
```
Docker Compose:
  nginx       → reverse proxy, SSL (Let's Encrypt)
  fastapi     → API server
  celery      → 4 workers (parallel PDF/drawing generation)
  postgres    → database (persisted volume)
  redis       → Celery broker + cache

Hetzner Object Storage → drawings/, exports/, ifc/
CI/CD: GitHub Actions → SSH → docker compose up -d
Migrations: alembic upgrade head (auto on deploy)
Monitoring: Sentry + UptimeRobot
Backup: nightly pg_dump → separate Hetzner bucket, 30-day retention
```

### Phase 2 — v1.0 Hardened (3+ clients)
- Hetzner Managed Postgres (automated backups, failover)
- Hetzner CDN for drawing delivery
- Staging environment (identical stack, separate domain)
- Prometheus + Grafana (Celery queue depth, task duration)

### Phase 3 — SaaS Scale (10+ organizations)
- k3s Kubernetes on Hetzner Cloud
- Per-organization Celery queues
- Postgres read replica for reporting
- Row-level security on organization_id
- GDPR: EU data residency (Hetzner Frankfurt or Helsinki)
- SAML SSO for enterprise

---

## 10. Certifications Required (Latvian Manufacturer → Scandinavian Market)

### CE Marking (manufacturer's responsibility)
Relevant standards: EN 14732, EN 15498
Requires: Initial Type Testing + Factory Production Control + Declaration of Performance
Notified Body: RISE (Sweden) or SINTEF Building Certification (Norway)
Timeline: 6–12 months — START IN PARALLEL WITH SOFTWARE DEVELOPMENT

### Sweden
- KA (Kontrollansvarig) appointed by client, certified by Boverket
- Konstruktör signs structural calculations
- Software generates technical documentation package for KA review

### Norway
- Ansvarlig prosjekterende needs Sentral Godkjenning (GOF) from DiBK
- Software generates technical documentation package for GOF holder review

### What the Software Provides
Technical Documentation Package per pod:
- Compliance Report (13 checks, clause citations)
- Structural Summary (SE review + stamp box)
- U-value Certificates with ψ-corrections
- Condensation Analysis (Glaser, monthly)
- Fire Performance Declaration
- A1–B6 Carbon Declaration (Klimatdeklaration format)
- Material Declarations (DoP references)
- Drawing Set (ISO 19650, revisioned)
- IFC Model

---

## 11. CNC Integration (v1.1)

### Timber Frame CNC (Hundegger, Weinmann, Randek)
Format: BTL (BauTeile Liste) XML — timber machining standard
Data already generated by 1D cutting optimiser — needs BTL serialiser only
Covers: C24 studs, plates, noggins, lintels
Labels: match LB2501-W-A1-S07 system

### Sheet Goods CNC (Homag, Biesse, SCM, SCM)
Format: DXF (already output by 2D nesting)
Verify: correct layer naming (CUT layer, LABEL layer) for CNC import

### Randek (Swedish manufacturer — key partner opportunity)
Used widely in Scandinavian timber frame factories
DXF panel layouts accepted
Potential channel partner relationship

Machine profiles (configurable per organization):
- Kerf width (default 3mm)
- Blade entry/exit clearance
- Min clamp distance
- Stock length rounding rules

---

## 12. Build Timeline (Solo Developer)

| Weeks | Deliverable |
|-------|------------|
| 1–2 | Schema + Celery + BBR + TEK17 + Part L profiles + Excel material import |
| 3–4 | Element Decomposer + Build-up Resolver (walls + roof + floor + openings) |
| 5–6 | Junction Resolver + ψ-library + effective U-value + Glaser condensation |
| 7 | Fire compliance (×3 checks) + Acoustic + Airtightness |
| 8 | EC5 Structural Design skill + MTO + 1D Cutting Optimiser + IFC Exporter |
| 9 | 2D Sheet Nesting + Membrane Plan + Fixing Schedule |
| 10 | Drawing generators (10 types) + title blocks + disclaimers |
| 11 | 3D viewer (Three.js, assembled + exploded) |
| 12 | Assembly graph + Work orders + QR codes on cut lists |
| 13 | Ventilation/MVHR + Daylighting + Radon + Airtightness checks |
| 14 | A1–B6 LCA + Klimatdeklaration PDF + Energideklaration |
| 15 | Performance optimiser + Element cost/value + Procurement export |
| 16 | Drawing Register UI + Compliance dashboard UI + Offcut pool |
| 17 | Transport plan (SE/NO rules) + CDE publish + end-to-end test (real pod) |
| 18 | Hardening + Hetzner deployment + beta launch |

With part-time frontend help (weeks 10–16): compress to ~14 weeks.

---

## 13. Definition of Done (MVP)

A user opens a blank project, picks Sweden BBR, draws a 6×3m garden-room pod
in the parametric form, enters SE-provided loads (or accepts defaults), picks
the default closed-panel timber frame build-up, hits Generate Pack.

Within 60 seconds they receive:

- Compliance report (13 checks, all green or fixable with one click)
- Structural summary (EC5 stud/lintel/racking, ready for SE stamp)
- 10 drawings, ISO 19650 coded, S6 Issued for Manufacture
- IFC4 model (.ifc)
- 3D viewer (assembled + exploded)
- C24 cutting list (PDF + BTL for CNC)
- PIR/OSB/plasterboard nesting plans (PDF + DXF for CNC)
- Membrane plan with tape and grommet totals
- Full fixing schedule per interface
- Method statement with QA hold-points
- Station work order packs (PDFs, printable)
- Transport plan (Swedish TSFS)
- Procurement list (CSV, Latvian supplier ready)
- Quotation with cost breakdown and carbon intensity
- Swedish Klimatdeklaration (A1–A5, Boverket format)

Zero hand-drawing. Zero spreadsheet wrangling. That is the bar.
