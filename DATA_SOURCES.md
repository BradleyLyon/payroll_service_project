# DATA_SOURCES.md
<!-- Purpose: every source we pull from — what it signals, how to get it, how often, and its quirks. Add a dated note whenever a source changes format or breaks. -->
<!-- 2026-07-06: added §8 fingerprint table, signal-decay rules, and quirks from the manual bot session (see session_insights_2026-07-06.md). -->

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
- **Quirks:** zero standardization between boards (PDFs, web pages, scans). Applicant name on agenda = LLC or person → cross-reference with SLA data. BetaNYC's SLAM tool aggregates some CB-relevant data — check before building anything. Proof it works: KOMENORI (2026-07-06 batch) was surfaced via a Brooklyn CB6 liquor filing before most press coverage.

## 6. Google Places API
- **Signals:** business_status (OPERATIONAL / CLOSED_TEMPORARILY / CLOSED_PERMANENTLY), **"no listing found" = strong pre-open signal (not an error)**, multiple same-name hits = chain flag, plus website URL, phone, photos for enrichment.
- **Access:** `restaurant_status_bot.py`, personal-Gmail GCP project. <!-- key setup in RUNBOOK once done -->
- **Cadence:** per pipeline run (each SLA pull).
- **Quirks:** costs money per request past free tier — batch carefully, cache results in DB, never re-query unchanged rows. Name matching is fuzzy (SLA legal name ≠ trade name; e.g. "XYZ Hospitality LLC" vs "Joe's Tacos"). Photos are manual-review material (surcharge signage, old terminals — PITCH_ANGLES #5, #12).
- **2026-07-06:** `place_id` becomes the canonical business key for entity resolution (name+address+entity matching is mandatory — 4 same-name collisions hit in one manual session: Apapacho Brooklyn vs DC, Wo Hop vs "Wo Hop Next Door", Tom's Prospect Heights vs Morningside Heights, Peppa's multi-operator cluster). `website: none` or `website = marketplace URL` is the second stage of the 10a marketplace-residue detector (see §8).

## 7. Manual per-lead enrichment (no API)
- **DoorDash/UberEats/Grubhub search:** presence/absence per lead (S2 hook + commission-bleed angle). **2026-07-06:** marketplace menu prices often exceed house prices (Lincoln Station: $14.25 house vs $15.39 DoorDash) — a verifiable, citable pitch observation. Also check whether the "direct" ordering link is actually a white-label (§8).
- **Restaurant website:** ordering link target (fingerprint per §8), hosting lookup (GoDaddy).
- **Job postings (Indeed/Craigslist):** headcount clues, "biweekly pay" (angle #6), hiring frequency (WOTC angle), sometimes names the payroll provider.
- **Yelp/Google photos & reviews:** "cash only" mentions, surcharge signage, old terminals. **2026-07-06:** Yelp's cash-only category contains stale false positives years old (John's of Bleecker: cards since May 2016, still listed). Never ship a cash-only lead without a primary source ≤ 12 months old — the business's own site/menu is the gold standard (J.G. Melon states it on its menu page).
<!-- Each of these is an automation candidate — log time spent to prioritize. -->

## 8. Platform & ordering fingerprints (detector reference) — added 2026-07-06
Confirmed in the wild during the manual bot session. Detectors should **scrape the matched page, not just fingerprint the URL** — competitor ordering pages leak enrichment (surcharge disclosures, gift-card programs, delivery config; e.g. The Grand's 3% surcharge found on its Toast page).

| Fingerprint | Meaning | Notes |
|---|---|---|
| `order.toasttab.com/*`, `toasttab.com/local/order/*` | Toast online ordering | Angle #13; scrape page body |
| `toasttab.com/local/<name>` with no Order button | Toast POS account, ordering NOT enabled | Stack-contradiction signal (#15) if marketplaces are active — owner pays for the fix and doesn't use it (case: Burger Queens) |
| `clover.com/online-ordering/*` | Clover online ordering | Confirmed live (Nippon Cha Williamsburg) |
| `*.square.site`, Square checkout | Square | Angle #14 |
| `order.online/store/*` | **DoorDash Storefront** — white-label "direct" ordering | High-precision "no owned channel" tell → angle 10b (cases: Lincoln Station, Burger Queens) |
| `getsauce.com/order/site/*` | Sauce white-label ordering | → angle 10b (case: Peppa's 2nd Ave cluster) |
| Owner.com template markers: rewards-program block + "We serve the following areas" SEO section + identical ordering UI | Owner.com-built site (site+ordering solved; no POS/payroll) | Lead value TBD — open Simon question (CLIENT_PROFILE) |
| Resy + OpenTable listed simultaneously | Reservation-vendor sprawl | Feeds #15 fragmented stack (case: F&J Pine) |

**10a sourcing rule:** the strict third-party-only population (marketplace listings, no website) is **search-resistant** — web search selects against it because no owned channel = no indexable footprint. Bot pipeline only: marketplace listings per neighborhood → Places lookup per name (§6) → filter to `website: none / marketplace URL`. The residue is the batch.

## Signal decay rules — added 2026-07-06
Every sourced fact carries a `verified_as_of` date (see LEAD_SPEC). Observed half-lives:
- **Crowd/review signals** (Yelp categories, review mentions): ~12 months before mandatory re-verification.
- **Map-scraped candidate lists** (Google Maps hand-research): **weeks.** All four June seed candidates had drifted by early July (one wrong-entity, two became new openings, one already-fixed stack). Fresh pulls beat stored lists — the same principle that justifies the LAMP diff engine.
- **Press-sourced ownership facts:** re-verify if > ~2 years old (The Grand's 2019 ownership press is the open-item case).
- **Legal context note:** NY GBL § 396-ii (eff. March 2026) bans *cashless* businesses statewide; cash-only remains legal. Usable as context in #12 pitches — do not overstate it as regulatory pressure on cash-only operators.

## Source-to-segment map
| Segment | Discovery | Corroboration |
|---|---|---|
| S1 ownership change | SLA transfers (1) | CB agendas (5) |
| S2 pre-open | SLA pending (1), DOHMH 1/1/1900 (2) | Places no-listing (6), CB agendas (5), DOB (3) |
| S3 established | <!-- TBD: needs a discovery source — Places search? DOHMH? --> | DCWP (4), job postings (7) |
| S4 conversion | detector scans of known restaurant sites (7), platform-URL fingerprint search (8) | Places (6) |
| S5 third-party-only (10a) | marketplace listings → Places no-website residue (8+6) — bot only | manual spot-check |
