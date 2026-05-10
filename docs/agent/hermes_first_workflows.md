# First Hermes Workflows For Manufacture Suite

## Workflow 1 — Architecture Documentation Keeper
Input: summary of completed development work, changed files, known issues
Output: architecture document update recommendation, change log entry, follow-up actions

## Workflow 2 — Production Smoke Test
Checklist:
- Vercel app loads
- Clerk login works
- create/save spec
- generate drawings
- generate BOM/MTO
- generate Internal Technical Pack
- generate Client Quote PDF
- check Material Library evidence counts
- check Settings page

## Workflow 3 — Material Evidence Audit
Checklist:
- count verified/partial/provisional/missing
- list missing datasheets
- list missing DoPs
- confirm assemblies are provisional
- confirm raw materials not treated as manufactured products

## Workflow 4 — Claude Task Chunk Generator
Output format: Problem / Files to inspect / Required fix / Do not change / Acceptance criteria

## Workflow 5 — Closed-Loop Intelligence Roadmap
Lead → Configure → Quote → Drawing → BOM/MTO → Procurement/RFQ → Production Pack → QA/QC → Handover → Learning Loop