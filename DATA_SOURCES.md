# DATA_SOURCES.md
<!-- Purpose: every source we pull from — what it signals, how to get it, how often, and its quirks. Add a dated note whenever a source changes format or breaks. -->

## 1. NYS SLA — pending liquor licenses ★ primary source
- **Signals:** license transfers (S1) and pre-open restaurants/bars (S2). Pending license ≈ opening in 1–6 months.
- **Access A (current):** LAMP map (lamp.sla.ny.gov) → filter pending → export CSV (`Pending Licenses.csv`). Updated daily.
- **Access B (automate later):** data.ny.gov hosts a "Liquor Authority Pending Licenses" dataset with an API — no manual map export needed. <!-- TODO: verify columns match the LAMP export before switching the bot to it -->
- **Cadence:** weekly pull. Every pull saved with `pulled_at` → diff vs DB = fresh leads + status changes.
- **Quirks:** filename has a space (quote it in terminal). License types matter: On-Premises Liquor/Wine/Beer = restaurants/bars; ignore off-premises (liquor stores) and wholesale. Same address can carry multiple applications. Re-check pending licenses ~1yr later (renewal/re-evaluation = the treasure trove).

## 2. NYC DOHMH restaurant inspections
- **Signals:** rows with **INSPECTION DATE = 1/1/1900** = new establishment that applied for a permit but hasn't been inspected → pre-open/just-opened (S2). Also confirms a business is active.
- **Access:** NYC Open Data, dataset "DOHMH New York City Restaurant Inspection Results" (id `43nn-pn8j`). CSV export or Socrata API.
- **Cadence:** weekly; dataset updates continuously.
- **Quirks:** unique key = **CAMIS** (use it for dedupe). One row per violation → dedupe before counting. Only active-status establishments are included, so disappearance from the dataset ≈ closed. 1/1/1900 rows have empty ACTION/SCORE/GRADE — that's expected, not bad data.

## 3. NYC DOB NOW / DOB permits
- **Signals:** construction/renovation permits at commercial addresses = opening or remodel 3–12 months out. Earliest signal we have, but noisiest.
- **Access:** NYC Open Data DOB permit issuance datasets; DOB NOW public portal for lookups. <!-- TODO: pick the exact dataset + filters (job type, occupancy = restaurant/commercial kitchen) when we build this -->
- **Cadence:** later phase. Not needed for Pilot A/B.
- **Quirks:** permits are per-building, not per-business — needs joining to an address/entity. High false-positive rate; use as corroboration, not a lead source alone. Also feeds the construction/certified-payroll track (PITCH_ANGLES #9).

## 4. NYC DCWP — legally operating businesses
- **Signals:** business license status/start date → confirms active operation, catches new registrations. Useful for size/age enrichment.
- **Access:** NYC Open Data, DCWP "Legally Operating Businesses" dataset. <!-- TODO: confirm dataset id + which license categories cover restaurants (many food businesses are DOHMH-permitted, not DCWP-licensed) -->
- **Cadence:** later phase; on-demand enrichment for now.
- **Quirks:** restaurants mostly appear via DOHMH, not DCWP — treat this as a secondary/enrichment source, not discovery.

## 5. Community board SLA calendars
- **Signals:** liquor license applications appear on CB agendas BEFORE/while SLA processes them — earliest named-applicant signal, often includes owner names (contact enrichment!).
- **Access:** manual — each CB posts agendas/calendars on its own site. Start with boards covering restaurant-dense areas. <!-- TODO: list the 5–10 CBs we'll actually monitor -->
- **Cadence:** monthly per board, manual until it proves valuable.
- **Quirks:** zero standardization between boards (PDFs, web pages, scans). Applicant name on agenda = LLC or person → cross-reference with SLA data. BetaNYC's SLAM tool aggregates some CB-relevant data — check before building anything.

## 6. Google Places API
- **Signals:** business_status (OPERATIONAL / CLOSED_TEMPORARILY / CLOSED_PERMANENTLY), **"no listing found" = strong pre-open signal (not an error)**, multiple same-name hits = chain flag, plus website URL, phone, photos for enrichment.
- **Access:** `restaurant_status_bot.py`, personal-Gmail GCP project. <!-- key setup in RUNBOOK once done -->
- **Cadence:** per pipeline run (each SLA pull).
- **Quirks:** costs money per request past free tier — batch carefully, cache results in DB, never re-query unchanged rows. Name matching is fuzzy (SLA legal name ≠ trade name; e.g. "XYZ Hospitality LLC" vs "Joe's Tacos"). Photos are manual-review material (surcharge signage, old terminals — PITCH_ANGLES #5, #12).

## 7. Manual per-lead enrichment (no API)
- **DoorDash/UberEats/Grubhub search:** presence/absence per lead (S2 hook + commission-bleed angle).
- **Restaurant website:** ordering link target (Toast/Square fingerprint), hosting lookup (GoDaddy).
- **Job postings (Indeed/Craigslist):** headcount clues, "biweekly pay" (angle #6), hiring frequency (WOTC angle).
- **Yelp/Google photos & reviews:** "cash only" mentions, surcharge signage, old terminals.
<!-- Each of these is an automation candidate — log time spent to prioritize. -->

## Source-to-segment map
| Segment | Discovery | Corroboration |
|---|---|---|
| S1 ownership change | SLA transfers (1) | CB agendas (5) |
| S2 pre-open | SLA pending (1), DOHMH 1/1/1900 (2) | Places no-listing (6), CB agendas (5), DOB (3) |
| S3 established | <!-- TBD: needs a discovery source — Places search? DOHMH? --> | DCWP (4), job postings (7) |
| S4 conversion | detector scans of known restaurant sites (7) | — |
