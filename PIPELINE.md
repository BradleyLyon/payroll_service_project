# PIPELINE.md
<!-- Purpose: how data becomes a delivered lead. Status boxes = what's left to build. Update boxes as things ship. -->

## The flow

```
  SOURCES                PROCESS                        OUTPUT
┌─ SLA pending CSV ─┐
│  DOHMH 1/1/1900   │→ ingest + snapshot → DB ─→ diff vs last pull = candidates
└─ (later: DOB) ────┘                                   │
                                                        ▼
                                    restaurant_status_bot.py (Places lookup)
                                    → status, chain_flag, website, Maps URL
                                                        │
                                                        ▼
                                    detectors: platform / hosting / DoorDash
                                                        │
                                                        ▼
                                    enrichment (manual or AI prompt):
                                    contact, size, angle, pitch_line
                                                        │
                                                        ▼
                                    score (LEAD_SPEC rubric) → ranked xlsx
                                                        │
                                                        ▼
                                    deliver to Simon → log outcomes in DB
```

## Scripts
<!-- One line each. Add as built. -->
| Script | Does | Status |
|---|---|---|
| `restaurant_status_bot.py` | SLA CSV → Places status, chain flag, notes, Maps URL | ✅ built, needs API key |
| `ingest_sla.py` | load a pull into DB with `pulled_at`, diff vs previous → new/changed | ⬜ Week 2 Wed |
| `detect_platform.py` | site URL → Toast/Square/other via redirect + HTML fingerprint | ⬜ Week 2 Mon |
| `detect_hosting.py` | domain → GoDaddy flag via DNS/WHOIS | ⬜ Week 2 Tue |
| `score_leads.py` | enriched rows → rubric score + ranked xlsx | ⬜ can be manual for Pilot A |

## Angle-of-attack checklists (per data stream)

### A. SLA pending licenses (S1 transfers + S2 pre-opens) — PILOT A PATH
- [x] LAMP CSV export working
- [ ] Places API key → run bot end-to-end
- [ ] Spot-check ~20 rows; tune chain detection + no-listing logic
- [ ] Figure out how the export distinguishes a *transfer at an existing address* (S1) from a *new application* (S2) — check license type/status columns
- [ ] Filter to On-Premises license types only
- [ ] Later: switch acquisition to the data.ny.gov pending-licenses API (no manual export)

### B. Platform detection (S4 conversion batches)
- [ ] v1: requests → follow ordering link → match `order.toasttab.com`, `*.square.site`, Square checkout markers
- [ ] v2: HTML signature scan (script tags, meta) for embedded ordering
- [ ] v3 (only if needed): Playwright headless fallback for JS-rendered sites
- [ ] Build fingerprint list as a data file, not hardcoded (add Clover/Stripe later)

### C. Hosting detection (GoDaddy cross-sell)
- [ ] DNS NS lookup (GoDaddy nameservers = `domaincontrol.com`) + WHOIS registrar as backup
- [ ] Flag but don't over-rank — unvalidated signal until Simon confirms

### D. DoorDash / delivery presence
- [ ] Manual for Pilot A (search each name + address)
- [ ] Automation candidate: scripted search — measure manual time first, automate only if painful

### E. DOHMH 1/1/1900 (second pre-open source)
- [ ] Hand-check 5 rows to validate signal quality (filler task)
- [ ] Then: Socrata API pull filtered to `inspection_date = 1900-01-01`, dedupe by CAMIS, cross-match against SLA names/addresses

### F. Contact discovery (weakest link — every lead needs one)
- [ ] Pilot A: manual — CB agendas (applicant names!), site/Instagram, WHOIS, state LLC lookup
- [ ] Log which source actually produced contacts → automate the winner

## Existing tools (don't build what exists)
- **sodapy** — Python client for Socrata (NYC/NYS open data APIs). Covers sources 1B, 2, 3, 4.
- **googlemaps** — official Places API Python client (bot may already use raw requests; fine either way).
- **requests + BeautifulSoup** — v1/v2 platform detection. **Playwright** only as fallback.
- **dnspython / python-whois** — hosting detection in ~10 lines.
- **pandas + openpyxl** — CSV wrangling and the ranked xlsx output.
- **BetaNYC SLAM** — aggregates licenses + inspections + 311 for CBs; check it before building CB tooling.
<!-- Rule: 30 min searching for an existing tool before writing any new scraper. -->
