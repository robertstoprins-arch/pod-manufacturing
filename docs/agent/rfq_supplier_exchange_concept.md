# Standardised RFQ / Supplier Exchange — Future Development Concept
# Last updated: 2026-05-14
# Status: Approved concept — not yet in active development

---

## 1. Main Idea

We want to create a standardised RFQ workflow where manufacturers, suppliers, and AI agents can exchange procurement information in a structured way.

The target is to reduce the current manual procurement loop:

```
Manufacturer prepares RFQ manually
→ sends emails to suppliers
→ waits days for replies
→ receives mixed formats
→ manually compares prices
→ manually checks lead times
→ manually checks alternatives
→ manually checks margin impact
```

Into a faster agent-supported loop:

```
Accepted Quote
→ BOM/MTO generated
→ materials grouped by supplier
→ standard RFQ request created
→ supplier system/agent responds with price, stock and lead time
→ Manufacture Suite compares responses
→ manufacturer approves supplier selection
→ procurement package is ready
```

The goal is **not** to replace human approval immediately.
The goal is to standardise the information exchange so AI agents and supplier systems can do the repetitive work.

---

## 2. Why This Matters

Existing manufacturers and suppliers often work with Excel price lists, PDF price lists, email quotations, WhatsApp messages, manual stock checks, phone calls, ERP exports, supplier portals, and manual comparison sheets.

A standardised RFQ format allows: faster supplier responses, automatic price comparison, lead-time comparison, stock availability checking, substitute product suggestions, evidence/document checking, margin impact warnings, and procurement readiness checks.

This supports the main Manufacture Suite target: sell faster, quote faster, procure faster, protect margin, reduce manual admin, create a closed-loop manufacturing workflow.

---

## 3. Product Split

### Commercial Product — Manufacture Suite

Used by manufacturers. Includes: leads, quotes, BOM/MTO, production packs, supplier directory, procurement packages, RFQ comparison, QA/handover, learning loop.

### Open / Free Tool — OpenRFQ Connector / Supplier Exchange Connector

Used by suppliers, agents and developers. Includes: standard RFQ schemas, supplier product list schema, RFQ request schema, RFQ response schema, mapping result schema, CSV/XLSX import examples, basic matching logic, agent instructions, MCP connector (later phase), API connector (later phase).

The open-source connector helps adoption. Manufacture Suite remains the paid platform.

---

## 4. The Big Workflow

```
Customer accepts quote
→ quote is locked
→ BOM/MTO is generated
→ BOM is grouped by supplier/category
→ RFQ packages are created
→ RFQ requests are sent to suppliers
→ suppliers respond by web form, Excel upload, API, connector or agent
→ responses are normalised into standard format
→ Manufacture Suite compares supplier options
→ system flags price, stock, lead time, substitutes and missing evidence
→ manufacturer approves supplier selection
→ procurement package is confirmed
→ supplier orders can be prepared
→ actual prices are stored
→ margins are checked
→ future quotes become smarter
```

---

## 5. Supplier Adoption Levels

Do not assume every supplier has an API. Support all maturity levels:

| Level | Method | Description |
|---|---|---|
| 0 | Normal email | Supplier replies manually. RFQ stored manually in Manufacture Suite. |
| 1 | Secure response link | Supplier receives email with private link → fills structured web form (price, availability, lead time, substitutes). No installation required. **Best first real version.** |
| 2 | CSV / Excel upload | Supplier uploads stock or price list. System maps columns and matches RFQ items. |
| 3 | Supplier mini portal | Supplier manages RFQs, responses, price list, stock, documents, lead times. |
| 4 | API connector | Supplier connects ERP/stock system/ecommerce through an API. |
| 5 | MCP connector / AI agent plugin | Agent receives RFQ, reads supplier stock/price source, maps products, checks availability, prepares and returns structured RFQ response. |

---

## 6. Cheapest / Fastest Start

```
1. Supplier Directory ✓ (built)
2. Materials linked to suppliers (next)
3. Accepted quote generates BOM (exists)
4. BOM grouped by supplier
5. RFQ email generated
6. Supplier receives secure response link
7. Supplier fills web form
8. Manufacture Suite compares responses
```

This does not require supplier installation, API, ERP or plugin.

---

## 7. Standard RFQ Objects

### Core objects (define first):

1. Supplier Product List
2. RFQ Request
3. RFQ Response
4. Mapping Result

### Later objects:

Order Confirmation, Delivery Update, Invoice Reference, Stock Feed, Supplier Performance, Agent Conversation Log.

---

## 8. Supplier Product List Schema

```json
{
  "message_type": "supplier_product_list",
  "version": "0.1",
  "supplier": {
    "supplier_id": "abc-supplies",
    "company_name": "ABC Building Supplies",
    "currency": "GBP"
  },
  "items": [
    {
      "supplier_sku": "PIR100-2400",
      "description": "100mm PIR insulation board 2400x1200mm foil faced",
      "category": "insulation",
      "unit": "board",
      "unit_price": 42.50,
      "stock_quantity": 120,
      "lead_time_days": 3,
      "datasheet_url": "",
      "dop_url": "",
      "last_updated": "2026-05-14"
    }
  ]
}
```

**Minimum fields:** supplier_sku, description, category, unit, unit_price, stock_quantity, lead_time_days, datasheet_url, dop_url.

**Optional fields:** manufacturer_name, manufacturer_product_ref, GTIN, EPD link, warranty document, fire certificate, acoustic certificate, pack size, minimum order quantity, delivery region.

---

## 9. RFQ Request Schema

```json
{
  "message_type": "rfq_request",
  "version": "0.1",
  "buyer": {
    "company_name": "Example Pod Manufacturer",
    "contact_name": "Procurement Team",
    "contact_email": "procurement@example.com"
  },
  "project": {
    "quote_id": "Q-1024",
    "job_reference": "Garden Office 4x6m",
    "delivery_postcode": "SW1A 1AA",
    "required_by": "2026-06-15"
  },
  "rfq": {
    "rfq_id": "RFQ-0001",
    "valid_response_required_by": "2026-05-25",
    "currency": "GBP",
    "allow_substitutes": true
  },
  "items": [
    {
      "line_id": "1",
      "description": "100mm PIR insulation board",
      "category": "insulation",
      "quantity": 52.4,
      "unit": "m2",
      "preferred_product_ref": "PIR-100",
      "acceptable_substitutes": true,
      "required_evidence": ["datasheet", "DoP"]
    },
    {
      "line_id": "2",
      "description": "OSB/3 board 18mm",
      "category": "boards",
      "quantity": 34,
      "unit": "sheets",
      "acceptable_substitutes": true,
      "required_evidence": ["datasheet", "DoP"]
    }
  ]
}
```

---

## 10. RFQ Response Schema

```json
{
  "message_type": "rfq_response",
  "version": "0.1",
  "supplier": {
    "company_name": "ABC Building Supplies",
    "contact_email": "sales@abcsupplies.com"
  },
  "rfq_id": "RFQ-0001",
  "supplier_quote_reference": "ABC-Q-98231",
  "valid_until": "2026-05-30",
  "currency": "GBP",
  "delivery": {
    "available_delivery_date": "2026-06-10",
    "delivery_cost": 120.00,
    "delivery_terms": "Kerbside delivery"
  },
  "items": [
    {
      "line_id": "1",
      "status": "available",
      "matched_supplier_sku": "PIR100-2400",
      "matched_description": "100mm PIR insulation board 2400x1200mm foil faced",
      "match_confidence": 0.92,
      "requested_quantity": 52.4,
      "requested_unit": "m2",
      "quoted_quantity": 19,
      "quoted_unit": "board",
      "unit_price": 42.50,
      "line_total": 807.50,
      "lead_time_days": 3,
      "datasheet_url": "",
      "dop_url": "",
      "needs_human_review": false,
      "notes": "19 boards required based on 2.88m2 per board."
    },
    {
      "line_id": "2",
      "status": "substitute_offered",
      "matched_supplier_sku": "OSB18-ALT",
      "matched_description": "OSB/3 board 18mm alternative manufacturer",
      "match_confidence": 0.81,
      "requested_quantity": 34,
      "requested_unit": "sheets",
      "quoted_quantity": 34,
      "quoted_unit": "sheets",
      "unit_price": 18.90,
      "line_total": 642.60,
      "lead_time_days": 5,
      "datasheet_url": "",
      "dop_url": "",
      "needs_human_review": true,
      "notes": "Substitute offered. Manufacturer approval required."
    }
  ],
  "total_ex_vat": 1570.10,
  "vat": 314.02,
  "total_inc_vat": 1884.12
}
```

---

## 11. Standard Item Statuses

| Status | Meaning |
|---|---|
| available | Exact or approved item can be supplied |
| partial_available | Only part of the requested quantity is available |
| substitute_offered | Supplier has offered an alternative product |
| unavailable | Supplier cannot supply this item |
| needs_human_review | Match is uncertain or requires approval |
| not_quoted | Supplier did not quote this item |

---

## 12. Mapping Result Schema

```json
{
  "message_type": "mapping_result",
  "version": "0.1",
  "rfq_line_id": "1",
  "requested_description": "100mm PIR insulation board",
  "matched_supplier_sku": "PIR100-2400",
  "matched_description": "100mm PIR insulation board 2400x1200mm foil faced",
  "confidence": 0.92,
  "match_type": "likely_exact",
  "unit_conversion_required": true,
  "unit_conversion_note": "Requested 52.4m2. Supplier sells 2.88m2 boards. Rounded to 19 boards.",
  "substitute": false,
  "needs_human_review": false
}
```

**Match types:** exact_sku, exact_description, likely_exact, similar_product, substitute, uncertain, no_match.

---

## 13. Confidence Thresholds

| Score | Action |
|---|---|
| 90%+ | Auto-match allowed |
| 70–90% | Suggest match, review recommended |
| Below 70% | Human review required |
| Any substitute | Human approval required |
| Any missing evidence | Warning required |
| Any unit conversion | Calculation must be shown |

---

## 14. AI Role (Lightweight)

**AI should do:** column mapping, product matching, unit normalisation suggestions, duplicate detection, substitute detection, confidence scoring, missing evidence detection.

**AI must not:** silently approve substitutes, place orders automatically, change manufacturer specifications, ignore low-confidence matches, hide unit conversions, approve missing evidence.

---

## 15. Column Mapping

Supplier uploads a spreadsheet. The AI maps spreadsheet headers to standard fields. The mapping is saved per supplier so it does not need to be repeated.

Example:
```
"Item Code"       → supplier_sku
"Product Description" → description
"Trade Price"     → unit_price
"Available Qty"   → stock_quantity
"Delivery Days"   → lead_time_days
"Spec Sheet"      → datasheet_url
```

---

## 16. Unit Normalisation

The system must understand different units and conversions:

- m2 to board / roll
- linear metre to length
- each to pack
- sheet to m2
- m3 to bags

Example: Buyer requests 52.4 m2. Supplier sells 2400×1200 boards. One board = 2.88 m2. 52.4 / 2.88 = 18.19 → round up to 19 boards. The response must show this calculation.

---

## 17. Secure RFQ Link — Security Rules

- Unique random token
- Expires after set period
- Access to one RFQ only
- No access to internal margin
- No access to other suppliers or projects
- Revocable by manufacturer
- Audit log of every response
- File upload limits and virus/file validation

---

## 18. Human Approval Rules

**Require human approval for:** supplier selection, substitutes, low-confidence matches, missing evidence, large price increases, lead time conflicts, purchase orders, changes to locked quote/spec.

**Allow automation for:** creating RFQ packages, sending RFQ requests, importing supplier price lists, mapping columns, suggesting matches, generating comparison summaries, flagging risks.

---

## 19. Development Stages

| Stage | Scope | Status |
|---|---|---|
| 1 | Internal Foundation — supplier directory, materials linked, BOM grouped by supplier, RFQ package object | In progress |
| 2 | RFQ Request Schema — generate standard RFQ JSON from BOM | Not started |
| 3 | Secure Supplier Response Link — email + web form, structured storage | Not started |
| 4 | Supplier Response Comparison — price, lead time, availability, margin impact | Not started |
| 5 | CSV/XLSX Supplier Upload — column mapping, item matching | Not started |
| 6 | Open-Source CLI Connector — schemas, examples, CLI, basic matching | Not started |
| 7 | Supplier Mini Portal — company profile, stock/price, RFQs, documents | Not started |
| 8 | API Connector | Not started |
| 9 | MCP Connector / Plugin | Not started |
| 10 | Agent-to-Agent Supplier Exchange | Not started |

---

## 20. Open-Source Repository Structure (Future)

```
openrfq-connector/
  README.md
  LICENSE
  docs/
    overview.md
    quickstart.md
    supplier-adoption.md
    schemas.md
    security.md
    agent-instructions.md
    mcp-roadmap.md
  schemas/
    rfq-request.schema.json
    rfq-response.schema.json
    supplier-product.schema.json
    mapping-result.schema.json
  examples/
    rfq-request.sample.json
    rfq-response.sample.json
    supplier-stock.sample.csv
    supplier-stock.sample.xlsx
    mapping-result.sample.json
  openrfq/
    cli.py
    mapper.py
    matcher.py
    units.py
    schemas.py
    confidence.py
  connectors/
    mcp/
      README.md
      server.py
      tools.py
    api/
      README.md
      app.py
  tests/
    test_mapper.py
    test_matcher.py
    test_units.py
```

---

## 21. What NOT to Build First

- Automatic purchase orders
- Payment automation
- Full ERP integration
- Global supplier marketplace
- Complex negotiation AI
- Automatic substitution approval
- Email free-text parsing as primary workflow
- Full Excel plugin
- Full MCP plugin before schema is stable

---

## 22. Final Positioning

| Audience | Value |
|---|---|
| Suppliers | A free tool to respond to RFQs faster using your existing Excel price list |
| Manufacturers | A structured supplier exchange that turns BOMs into RFQs and compares supplier responses automatically |
| Agents | A standard RFQ format and connector that allows agents to request, match and return material quotes safely |
| Manufacture Suite | A procurement automation layer that closes the loop from accepted quote to supplier pricing, margin protection and production readiness |

---

## 23. Key Rule

> Do not automate risky decisions first.
> Standardise the data first.
> Automate the repetitive work second.
> Require human approval for substitutes, low-confidence matches and purchasing.
