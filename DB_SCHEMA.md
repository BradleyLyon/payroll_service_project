# DB_SCHEMA.md
<!-- Purpose: what's in the DB and why. SQLite for now (one file: `leads.db`). Migrate to Postgres only if the data business materializes. DDL lives in db/schema.sql; `python init_db.py` creates leads.db. -->

## Why snapshots (read this first)
Every SLA pull is saved whole, tagged with `pulled_at`. Never overwrite. Reasons:
1. **Diff engine:** new rows vs last pull = this week's fresh leads; vanished rows = status change worth knowing.
2. **The treasure trove:** licenses get re-evaluated/renewed ~1 year later. A year of snapshots = a queryable history of every opening in NYC — resellable on its own, and it tells us exactly when a business hits its renewal window (a fresh contact trigger).
3. Filings lag reality; history lets us verify when something *actually* changed.

## Tables

### snapshots
One row per data pull.
| field | notes |
|---|---|
| snapshot_id | PK |
| source | 'sla_pending', 'dohmh', ... |
| pulled_at | date |
| filename | original export file |
| row_count, file_hash | sanity checks vs bad exports. **file_hash is UNIQUE** — ingesting the same CSV twice would poison the diff engine |

### licenses
Raw SLA rows, append-only, FK → snapshots.
| field | notes |
|---|---|
| license_row_id | PK |
| snapshot_id | FK |
| serial_number | SLA serial — the stable key across snapshots |
| legal_name, trade_name | legal ≠ trade; both needed for matching |
| address, zip, borough | |
| license_type, license_status | On-Premises filter; transfer vs new (S1/S2 split) |
| raw_json | full original row — schema changes won't lose data |

Unique on (serial_number, snapshot_id). Indexed on serial_number for the diff.

### businesses
Deduped real-world entities (one restaurant = one row, however many filings). The only table that mutates.
| field | notes |
|---|---|
| business_id | PK |
| canonical_name, address, zip, borough | |
| segment | S1–S4 per LEAD_SPEC, nullable until classified |
| status | pre_open / open / closed / unknown |
| chain_flag, franchise_control | hard-disqualifier fields — resolve or drop |
| first_seen, last_seen | derived from snapshots |
| notes | |

<!-- serial_numbers and camis moved to business_sources — lists in a column can't be joined or indexed in SQLite. -->

### business_sources
Which raw records belong to which business — SLA serials, DOHMH CAMIS, later DOB/DCWP keys. **This is also the fuzzy-match review log** (dedupe rule: serial > CAMIS > fuzzy name+address, log fuzzy matches for review).
| field | notes |
|---|---|
| source | 'sla', 'dohmh', 'dob', ... |
| external_key | serial number / CAMIS / permit # |
| business_id | FK |
| match_method | 'serial' / 'camis' / 'fuzzy' / 'manual' |
| match_confidence | 0–1, only meaningful for fuzzy |
| needs_review | 1 = a human hasn't confirmed the fuzzy match yet. `SELECT * WHERE needs_review = 1` is the review queue |

PK on (source, external_key) — one raw record maps to exactly one business.

### places_cache
Google Places results, append-only. **Check here before every API call — cache is money.** Latest row per business wins; re-query only if stale (>30d) or status unknown (use view `v_latest_places`).
| field | notes |
|---|---|
| cache_id | PK |
| business_id | FK |
| queried_at | |
| business_status, chain_flag, website, phone, maps_url | |
| raw_json | |

### enrichments
One row per business per enrichment pass, append-only. Latest wins (view `v_latest_enrichment`).
| field | notes |
|---|---|
| enrichment_id | PK |
| business_id | FK |
| doordash, website_status, platform, hosting | detector/manual results |
| ordering_evidence, hosting_evidence | the URL/fingerprint that proved it — pitch rule requires *verifiable* observations |
| size_estimate, locations_count | |
| contact_name, contact_info | |
| primary_angle, pitch_line | from PITCH_ANGLES.md — working values; the *delivered* version freezes in `leads` |
| evidence_links | Maps URL, site, listing (LEAD_SPEC required field) |
| enriched_at, enriched_by | 'brad' / 'jack' / 'ai' / 'bot' |

### batches
One row per delivery to Simon. <!-- was missing: leads referenced batch_id but nothing defined a batch -->
| field | notes |
|---|---|
| batch_id | PK |
| label | 'Pilot A', 'Pilot B', 'W29' |
| delivered_at | null until sent |
| xlsx_filename | `leads_batch_{N}_{YYYY-MM-DD}.xlsx` per LEAD_SPEC |
| notes | |

### leads
What actually went to Simon. This table proves the 3–5%. Score/rank/angle/pitch are **frozen at delivery** — enrichments may change later, this row records what was sent.
| field | notes |
|---|---|
| lead_id | PK |
| business_id, batch_id | FKs; unique together |
| score, rank | rubric at time of delivery |
| primary_angle, pitch_line | as delivered |
| outcome | queued / delivered / called / closed / rejected — CHECK-constrained so a typo can't corrupt the closure math |
| outcome_notes, outcome_at | Simon's feedback, verbatim if short |

Closure rate = closed / delivered (excl. queued), per batch or overall.
"Not previously delivered" check (LEAD_SPEC disqualifier #5): `business_id IN (SELECT business_id FROM leads WHERE outcome != 'queued')`.

## Views
- `v_latest_places` — newest places_cache row per business + its age in days. The "should I spend an API call" check.
- `v_latest_enrichment` — newest enrichment per business. What the scorer and xlsx builder read.

## Rules
- Append, don't update, for anything time-stamped. `businesses` is the only table that mutates.
- Dedupe key priority: SLA serial > CAMIS > fuzzy name+address (fuzzy matches land in `business_sources` with `needs_review = 1`).
- Back up `leads.db` weekly. **`*.db` is gitignored** — it holds contact info and client-adjacent data; never push it to public GitHub.

## Scripts (db layer)
| Script | Does |
|---|---|
| `init_db.py` | creates `leads.db` from `db/schema.sql` (idempotent) |
| `ingest_sla.py` | loads a LAMP CSV as a snapshot, diffs vs previous pull → prints new / vanished / status-changed serials, optional CSV of new candidates |
