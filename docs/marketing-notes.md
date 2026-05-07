# Pod Manufacturing Software — Marketing Notes

_Captured during architecture planning session, 2026-04-29_

---

## Target Market

**Primary geography:** Sweden + Norway (launch), Finland + Denmark (v1.1 expansion)
**Manufacturing base:** Latvia — EU CE materials, shorter supply chain to Scandinavia vs UK

---

## Ideal Customer Profile (ICP)

**Primary:** Modular house manufacturer, 10–100 employees, currently using AutoCAD + Excel
for production pack generation. Located in Sweden, Norway, Finland, or Latvia.
Produces 20–200 pod units per year.

**Pain:** Every new pod design takes 40–80 hours of manual draughting and schedule
generation. The software cuts that to 60 seconds.

**Secondary:** Prefab bathroom and kitchen pod manufacturers (high volume, identical
units — the cutting optimiser alone is a strong sell here).

---

## Market Tailwinds

- Stockholm municipality needs 140,000 new homes by 2030. Modular is the only
  viable path at that volume.
- Norwegian TEK17 tightened energy requirements — manual compliance proving is slow.
- Swedish Klimatdeklaration (mandatory Jan 2022) creates carbon reporting burden that
  the LCA output solves automatically.
- EU Taxonomy sustainability reporting pushing developers to demand carbon declarations
  from suppliers.
- IFC/BIM adoption accelerating — Norway mandates IFC for all public construction.

---

## Competitive Landscape

| Tool | What it does | Gap vs our software |
|------|-------------|---------------------|
| Revit / Archicad | Full BIM authoring | No cutting lists, no factory station packs, no compliance automation |
| Dietrichs M8 / SEMA | Timber frame design (German) | Good cutting lists, no compliance integration, no factory packs |
| Vertex BD | Structural timber design | No production pack generation |
| AutoCAD + Excel | Manual everything | The status quo we replace |

**Our moat:** Only software that generates a complete, compliant, production-ready
factory pack from a parametric input in under 60 seconds.

---

## Pricing Model

| Tier | Price | Volume |
|------|-------|--------|
| Starter | €199/pack | One-off projects, low commitment |
| Growth | €1,500/month | Up to 10 packs/month (~€150/pack) |
| Scale | €3,500/month | Unlimited packs + priority support |
| Enterprise | Custom | White-label, API access, SLA |

**ROI story:** Manual pack costs 60 hours × €50/hour = €3,000 engineer time.
Our software: €199–1,500. Payback on first pack.

---

## Go-to-Market Sequence

**Month 1–2:** Beta with one friendly Latvian manufacturer already selling to Sweden.
Free in exchange for a detailed case study with real numbers.

**Month 3–4:** Case study → outreach to 20 Swedish modular manufacturers via LinkedIn.
Hook: "We generated a compliant factory pack for a 6×3m garden room in 60 seconds.
Here's the IFC file."

**Month 5–6:** Nordbygg (Stockholm trade show, April biennial) — live demo booth
showing pack generation from parametric input to downloaded PDF in real time.

**Month 7+:** Referral-led growth. Modular manufacturers know each other.

---

## Key Marketing Asset (build alongside the software)

Public demo at `demo.[domain].com`:
- Anyone enters a 6×3m pod spec, hits Generate
- Downloads a watermarked sample pack (compliance report, cutting list, 1 drawing, IFC)
- No login required
- This sells itself — the product is the marketing

---

## Key Messages

1. **"60 seconds from brief to factory pack."** — speed is the headline
2. **"BBR and TEK17 compliance built in."** — removes regulatory anxiety
3. **"Your Klimatdeklaration, automatically."** — regulatory compliance as a feature
4. **"IFC export. Your architects can work with it."** — technical credibility
5. **"Latvia-optimised materials with Scandinavian compliance."** — cost + quality story

---

## Industry Channels

- **Trä- och Möbelföretagen** (Swedish timber industry association)
- **Norsk Tre** (Norwegian timber association)
- **buildingSMART Scandinavia** (BIM/IFC network)
- **Swedish BIM Alliance**
- **Nordbygg** (Stockholm, biennial trade show)
- **LinkedIn** — Production Managers, Technical Directors at modular manufacturers

---

## Notes for Future

- Consider white-label offering for large manufacturers who want to brand the output
- Partnership opportunity with Latvian material suppliers (Latvijas Finieris, etc.)
  — they could subsidise software access for customers buying their materials
- CNC machine manufacturers (Randek in Sweden) as channel partners
- Potential grant funding: Vinnova (Swedish innovation agency) funds construction tech

---

## Strategic Product & Market Review
_Added 2026-04-30 — full market direction analysis for 1,500 m² Latvia workshop + Scandinavian export_

---

### 1. Best Market Direction: Small Permitted / Low-Permission Timber Pods

The most attractive opening is **small timber buildings below major planning thresholds**, especially in Sweden.

Sweden has widened the market for smaller accessory buildings. Within detailed development plan areas, the largest accessory building may be up to **30 m²** (total accessory area up to 45 m²), ridge height up to 4 m. Outside detailed plan areas: up to **50 m²** (total up to 65 m²), ridge height up to 4.5 m. Neighbour consent still needed close to boundaries. (Source: Boden municipality guidance)

Even without full planning permission, **technical requirements still apply** — drawings, U-value summary, build-up, condensation logic, structural assumptions, transport information, installation manual, and handover documentation. This is exactly where the software pack creates value.

---

### 2. Pod Types Ranked by Opportunity

| Rank | Product type | Market chance | Manufacturing complexity | Compliance risk | Recommendation |
|-----:|-------------|--------------|--------------------------|----------------|----------------|
| 1 | Garden office / studio pod | High | Low–medium | Low–medium | **Best first product** |
| 2 | 30 m² Swedish accessory dwelling (Attefall-type) | High | Medium | Medium–high | Best second product |
| 3 | Glamping / hospitality cabin | Medium–high | Medium | Medium | Good design-led niche |
| 4 | Sauna / wellness pod | Medium | Medium | Medium | Good add-on product |
| 5 | Worker / site welfare pod | Medium | Medium | Medium | B2B opportunity |
| 6 | Bathroom / wet-room pod | Medium | High | High | Avoid at start |
| 7 | Full residential modular house | High market size | High | High | Later only |
| 8 | Data-centre / technical plant pod | Growing market | High | High | Later specialist route |

---

### 3. Best First Product: Premium Garden Office / Studio Pod

A garden office/studio avoids full kitchen/bathroom complexity. Sells to homeowners, architects, small developers, hospitality owners, and commercial users. Still needs good insulation, airtightness, ventilation, electrical provisions, structural integrity, fire-safe materials, and documentation — but avoids the hardest residential compliance at first.

The Scandinavian prefabricated housing market is forecast to grow from ~USD 6.35B in 2026 to USD 7.92B by 2031 (Mordor Intelligence). For a new entrant, the small-building niche is the better wedge.

**Start with 3 sizes only:**

| Product | Approx. size | Use |
|---------|-------------|-----|
| Studio S | 10–15 m² | Office, hobby room, guest room without bathroom |
| Studio M | 20–25 m² | Premium office / guest studio |
| Studio L | 30 m² | Swedish accessory building / future dwelling-ready shell |

Do not start with unlimited sizes. The software supports variation but the factory must start with controlled product rules.

**Key selling points:**
- Latvian timber manufacturing cost advantage
- Scandinavian-ready insulated build-up
- Fast delivery
- Clean modern design + factory quality control
- Full technical pack (drawings, U-values, build-up, installation manual)
- Optional foundation, PV-ready roof, MVHR-ready packages
- Optional bathroom/kitchen upgrade path

---

### 4. Second Product: 30 m² Swedish Accessory Dwelling Pod

Good commercial product but harder. Once it becomes a self-contained dwelling it adds: accessibility, ventilation, heating, water and drainage, bathroom waterproofing, fire, energy performance, acoustic comfort, local installation responsibility, groundworks interface, possible municipal technical control.

**Two commercial variants:**

**Variant A — "Shell + technical pack":** Manufacture the pod shell, envelope, windows, doors, internal lining, service zones, and factory drawings. Local professionals complete MEP, drainage, and final connection. Reduces liability.

**Variant B — "Turnkey dwelling pod":** Only once partners in Sweden/Norway are in place for local foundation, utility connection, inspection, and sign-off. Higher profit, higher risk.

---

### 5. Strong Niche: Glamping / Hospitality Cabins

Good design-led market, especially in Scandinavia. Modular luxury nature accommodation is an active trend (BIG/Nokken Softshell example). Can be less regulation-heavy than permanent dwellings depending on jurisdiction, duration, foundation, and services. Rewards good visual design and brand positioning.

**Best position:** Premium insulated Nordic micro-cabin for year-round hospitality use.

Potential sizes: 12–15 m² sleeping cabin / 18–22 m² ensuite cabin / 25–30 m² premium cabin. Shares the same software and factory logic as the garden office pod.

**Risk:** More brand/design/sales-heavy. Needs strong visuals, lifestyle photography, and partnerships with landowners and hospitality operators.

---

### 6. Avoid First: Bathroom Pods and Full Houses

**Bathroom pods:** Waterproofing certification, drainage falls, leak testing, MEP coordination, logistics damage risk, fire/acoustic penetrations, site interface complexity, high defect liability. Avoid until QA system is mature.

**Full modular houses:** Big market but crowded and high-liability. Latvia already has established prefab/timber manufacturers exporting across Europe (PMH: 7,500 m² production, 98% export; Vitbūve: prefab wooden-frame houses delivered Europe-wide). Enter this market later, not as a generic prefab house company from day one.

---

### 7. What Is Short on the Market

The gap is not "pods generally." There are many pod/cabin/prefab suppliers.

**The gaps are:**

**1. Technically credible small pods** — Many garden rooms are sold with nice renders but weak technical documentation. Aftonbladet's 2026 review of Swedish accessory houses criticised manufacturers for misleading renders, poor layouts, and weak adaptation to new rules.
_Opportunity: sell trust, not just design._ Offer real plans, real sections, real U-value build-up, realistic furniture layouts, installation manual, transparent options, transport dimensions, foundation assumptions, maintenance pack.

**2. Export-ready Scandinavian documentation** — Many manufacturers can build but fewer can package information in a way Swedish/Norwegian clients, engineers, and local professionals trust. This is the SaaS/factory pack differentiator.

**3. Semi-standardised premium product** — Space between cheap flat-pack sheds and expensive architect-designed bespoke cabins. Position: **premium-standardised, not fully bespoke.** Allow choices in façade, window position, insulation level, interior finish, and MEP readiness — but not unlimited geometry.

**4. Fast quote + fast technical pack** — Manufacturers lose leads because quoting takes too long or sends vague pricing. The software turns a lead into: price range, layout, section, material list, delivery estimate, carbon estimate, optional upgrades. This wins jobs before larger companies respond.

---

### 8. Workshop Strategy (1,500 m²)

Do not start with heavy automation or CNC on day one unless equipment is already owned.

**Suggested layout:**

| Zone | Approx. area | Function |
|------|-------------|---------|
| Material storage | 250–300 m² | Timber, boards, insulation, membranes |
| Cutting / prep | 150–200 m² | Timber cutting, board cutting, labelling |
| Panel assembly tables | 350–450 m² | Wall, roof, floor cassette assembly |
| Pod / module assembly | 300–400 m² | Full pod dry fit / finishing |
| Finishing / QA / photo | 150–200 m² | Inspection, wrapping, documentation |
| Packing / loading | 150–200 m² | Weather protection, transport prep |
| Office / sample showroom | 50–100 m² | Sales, technical review, mock-ups |

---

### 9. Manufacturing Strategy: Panel First, Volumetric Later

**Stage 1 — Panelised kit:** Wall panels, roof/floor cassettes, pre-cut insulation, membrane kits, sheathing, fixing packs, drawing pack, installation guide. Easier to export, easier to standardise, less risky.

**Stage 2 — Hybrid pod:** Pre-finished external wall panels, pre-installed windows/doors, internal service battens, pre-cut interior boards, roof cassette, floor cassette. Reduces transport headaches.

**Stage 3 — Full volumetric pod:** Only after market is known and logistics are sorted. Best for garden offices, hospitality cabins, small studios, sauna pods, ensuite cabins.

---

### 10. Product Roadmap

**Phase 1 (0–3 months) — Prove demand:**
- 3 standard pod models
- One technical brochure + parametric quote calculator
- One factory-pack generator prototype
- 1:1 wall/roof/floor mock-up
- Supplier cost database + sample drawing pack
- Target: 10–20 serious enquiries + 1–2 paid prototype orders

**Phase 2 (3–6 months) — First production system:**
- Build first physical prototype (15 m² office pod, 30 m² accessory shell, hospitality cabin concept)
- Use software internally only — do not sell SaaS yet
- Outputs: quote, MTO, cutting list, factory drawings, assembly method statement, QA checklist, photo evidence pack

**Phase 3 (6–12 months) — Productised manufacturing:**
- Standard options catalogue, reseller pricing, installation partner model
- CE/product documentation route + quality control process
- Packaging and transport method + aftercare manual
- Market as: "Designed/specified in the UK/EU — manufactured in Latvia — delivered to Scandinavia"

**Phase 4 (12–24 months) — SaaS becomes commercial:**
- Factory becomes the test bed for the SaaS
- Offer the workflow to other manufacturers once your own process is proven

---

### 11. Recommended First Product Family: Nordic Studio Pods

| Model | Size | Description |
|-------|------|-------------|
| **Studio 15** | 15 m² | Office / hobby / guest room, no bathroom, insulated year-round, electrical-ready, flat or mono-pitch. Easiest to build and sell. |
| **Studio 25** | 20–25 m² | Premium office / guest studio, optional kitchenette wall, optional MVHR, premium cladding options. |
| **Studio 30** | 30 m² | Swedish accessory-building size, shell-first product, bathroom/kitchen-ready but locally completed. Strongest long-term market. |
| **Cabin 22 Ensuite** _(Phase 2)_ | 22 m² | Hospitality/glamping, bathroom module, higher price, requires mature QA. |
| **Sauna / Wellness Pod** _(Phase 2)_ | 12–18 m² | Sauna + shower + changing area, premium add-on for hospitality clients. |

---

### 12. Sales Channels

**1. Swedish reseller / installer partners** _(fastest route)_ — You manufacture, they sell/install locally. They handle: client relationship, local groundworks, permits/notification, electrical/plumbing, final handover. You provide: product, technical pack, installation instructions, warranty, delivery.

**2. Architects and small developers** — Offer: "Standard technical pod systems with customisable façade and layout." Architects want something they can specify without embarrassment.

**3. Hospitality operators** — Target glamping sites, rural hotels, ski/nature tourism, lake/forest retreats, campsites upgrading from tents. They care about ROI, durability, guest experience, delivery speed.

**4. Direct-to-consumer** — Possible but more marketing-heavy. Requires excellent visuals, trust signals, reviews, and local installation coverage.

---

### 13. Main Risks

| Risk | Mitigation |
|------|-----------|
| Becoming too bespoke — kills margin | Rule: 80% standard, 20% configurable |
| Taking too much compliance responsibility | Always separate: software evidence / engineer review / local statutory responsibility / installation responsibility |
| Underestimating transport | Panelised or hybrid may be better than full volumetric for export |
| Weak local installation network | Sweden/Norway local installers make or break the business — recruit early |
| Competing only on price | Compete on technical credibility + speed + design + documentation, not cheapest shed |

---

### 14. Clear Recommendation

**Start with:**
> Premium panelised / hybrid timber garden office and 30 m² accessory-building shells for Sweden, manufactured in Latvia, supported by an automated technical/factory-pack workflow.

**Do not start with:** full residential modular houses, bathroom pods, unlimited bespoke pods, full SaaS-first strategy, or full compliance automation.

**The two businesses that support each other:**
- **Manufacturing business** → generates cash and proof of concept
- **SaaS business** → captures the process and scales the knowledge

The factory is the test bed. The SaaS is the multiplier. Build manufacturing first.
