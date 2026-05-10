# Manufacture Suite — Hermes Project Context
# Load this at the start of every session.
# Last updated: 2026-05-10

---

## Primary Goal

Manufacture Suite is being built as an AI-assisted closed-loop manufacturing operating layer for configurable product manufacturers (pods, garden rooms, bathroom pods, modular units).

Target workflow:
Lead → Configure → Quote → Drawing → BOM/MTO → Procurement/RFQ → Production Pack → QA/QC → Handover → Learning Loop

---

## Live Deployment

| Layer | Service | URL |
|---|---|---|
| Frontend | Vercel | https://pod-mfg.vercel.app |
| Backend API | Render | https://pod-manufacturing-api.onrender.com |
| Database | Neon PostgreSQL | ep-floral-wildflower-al5oqd0t.c-3.eu-central-1.aws.neon.tech |
| Auth | Clerk | Production instance |
| Source control | GitHub | https://github.com/robertstoprins-arch/pod-manufacturing |

Auto-deploy: git push to main → Vercel and Render deploy automatically.

---

## What Has Been Built (Implemented)

### Frontend (React/Vite on Vercel)
- Pod Designer — create/edit pod spec, dimensions, openings, rooflights
- Drawing generation — manufacture plan, sales sheet, opening schedule, PDF export
- BOM/MTO — material quantities, waste, unit pricing, cost roll-up
- Cost Summary — provisional allowances, finish packages, heating/ventilation, foundations
- Material Library — supplier links, datasheets, DoPs, evidence status and category grouping
- Finish Catalogue — customer-facing finish/product/furniture choices
- Settings page — markup %, VAT %, currency, VAT mode, pricing preview
- Sidebar navigation with all pages

### Backend (FastAPI/Python on Render)
- PostgreSQL via Neon (SQLAlchemy + Alembic migrations)
- Migrations run automatically at startup
- PDF generation via ReportLab — Internal Technical Pack + Client Quote PDF
- Material evidence API — verified/partial/provisional/missing status
- Account Settings API — markup, VAT, currency
- BOM endpoint with evidence warnings
- Seed scripts — standard materials, build-ups, finish catalogue, material evidence

### Authentication
- Clerk — invite-only mode, production keys configured

---

## Current Material Evidence Status (as of 2026-05-10)

| Status | Count | Notes |
|---|---|---|
| Verified | 7 | Confirmed supplier + datasheet + DoP |
| Partial | 5 | Some evidence missing (datasheet or DoP) |
| Provisional | 4 | Assembly/calculation rows — no DoP required |
| Missing | 4 | No evidence yet — raw commodity items or unselected products |

Evidence seed script: backend/seeds/material_evidence_seed.py
Run with: python seeds/material_evidence_seed.py --force

---

## Key Architecture Decisions

- Internal Technical Pack and Client Quote PDF are separate outputs
- Client PDF hides BOM, supplier refs, markup and internal warnings
- Markup controlled from Account Settings only — not scattered across components
- Assembly/calculation rows (service void, cavity) are not manufactured products — they are provisional
- Evidence must use real URLs only — never invented links
- Seed scripts are idempotent and safe to run against production
- Render and Vercel deploy independently — always verify both after a push

---

## Current Roadmap

| Phase | Scope | Status |
|---|---|---|
| Phase 1 | Stabilise MVP — PDF, drawings, BOM, evidence, settings | Current |
| Phase 2 | Quote pipeline — status, history, client records, sent/accepted/lost | Next |
| Phase 3 | Procurement/RFQ — supplier directory, RFQ packages, price comparison | Near-term |
| Phase 4 | Production job pack — convert quote to job, QA/QC, handover | Mid-term |
| Phase 5 | Closed-loop AI — event log, recommendations, margin alerts, learning | Strategic |

---

## Known Issues / Follow-Up

- Gyproc DoP URL not yet found — add manually via Material Library Edit modal
- Kronospan OSB/3 TDS not directly accessible — JS portal
- PDF generation needs continued production testing
- Drawing annotation clash detection needs refinement
- Rooflight representation in drawings/schedule/BOM needs verification

---

## How Claude and Hermes Work Together

Claude Code (VS Code):
- Reads and edits code files
- Runs backend commands via terminal
- Updates the architecture .docx document
- Commits and pushes to GitHub

Hermes (WSL2 / Telegram):
- Plans and prepares task chunks for Claude
- Runs production smoke test checklists
- Audits material evidence
- Maintains project memory across sessions
- Flags risks and suggests next actions

Roberts approves anything before it touches production, GitHub or external systems.

---

## Files To Know

| File | Purpose |
|---|---|
| backend/seeds/material_evidence_seed.py | Evidence data seed — run with --force against Neon |
| backend/app/api/build_ups.py | Material library API, evidence logic, BOM output |
| backend/app/api/pod_specs.py | Pod spec routes, BOM endpoint, PDF generation |
| backend/app/api/settings.py | Account settings, markup/VAT |
| backend/skills/pdf_review_pack.py | Internal Technical Pack PDF |
| backend/skills/pdf_client_quote.py | Client Quote PDF |
| src/pages/MaterialLibrary.jsx | Material evidence UI |
| src/pages/Settings.jsx | Settings page |
| docs/260510 manufacture_suite_architecture_documentation 1.docx | Controlled architecture record |
| docs/agent/hermes_operating_rules.md | Hermes operating rules |
| docs/agent/hermes_allowed_tasks.md | Hermes allowed tasks |
| docs/agent/hermes_forbidden_tasks.md | Hermes forbidden tasks |

---

## Start Of Session Checklist (Hermes)

1. Read this file.
2. Read hermes_operating_rules.md
3. Confirm current project state understanding.
4. Suggest top 3 actions based on current roadmap and known issues.
5. Ask Roberts what he wants to work on today.
