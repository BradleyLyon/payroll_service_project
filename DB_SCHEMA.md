# DB_SCHEMA.md
<!-- Purpose: what's in the DB and why. SQLite for now (one file: `leads.db`). Migrate to Postgres only if the data business materializes. -->

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
| row_count, file_hash | sanity checks vs bad exports |

### licenses
Raw SLA rows, append-only, FK → snapshots.
| field | notes |
|---|---|
| license_id | PK |
| snapshot_id | FK |
| serial_number | SLA serial — the stable key across snapshots |
| legal_name, trade_name | legal ≠ trade; both needed for matching |
| address, zip, borough | |
| license_type, license_status | On-Premises filter; transfer vs new (S1/S2 split) |
| raw_json | full original row — schema changes won't lose data |

### businesses
Deduped real-world entities (one restaurant = one row, however many filings).
| field | notes |
|---|---|
| business_id | PK |
| canonical_name, address | |
| camis | DOHMH key, nullable |
| serial_numbers | linked SLA serials |
| first_seen, last_seen | derived from snapshots |
| status | pre_open / open / closed / unknown |

### places_cache
Google Places results. **Check here before every API call — cache is money.**
| field | notes |
|---|---|
| business_id | FK |
| queried_at | re-query only if stale (>30d) or status unknown |
| business_status, chain_flag, website, phone, maps_url | |
| raw_json | |

### enrichments
One row per business per enrichment pass.
| field | notes |
|---|---|
| business_id | FK |
| doordash, website_status, platform, hosting | detector/manual results |
| size_estimate, contact_name, contact_info | |
| primary_angle, pitch_line | from PITCH_ANGLES.md |
| enriched_at, enriched_by | 'brad' / 'jack' / 'ai' |

### leads
What actually went to Simon. This table proves the 3–5%.
| field | notes |
|---|---|
| lead_id | PK, FK → business_id |
| batch_id, delivered_at | |
| score, rank | rubric at time of delivery |
| outcome | delivered / called / closed / rejected |
| outcome_notes, outcome_at | Simon's feedback, verbatim if short |

## Rules
- Append, don't update, for anything time-stamped. `businesses` is the only table that mutates.
- Dedupe key priority: SLA serial > CAMIS > fuzzy name+address (log fuzzy matches for review).
- Back up `leads.db` to the repo's private storage weekly. <!-- decide where — not public GitHub -->
