-- db/schema.sql — leads.db DDL (SQLite v1)
-- Rationale in DB_SCHEMA.md. Create the DB with: python init_db.py
-- Rules: append-only for anything time-stamped; `businesses` is the only table that mutates.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id  INTEGER PRIMARY KEY,
    source       TEXT NOT NULL,               -- 'sla_pending', 'dohmh', ...
    pulled_at    TEXT NOT NULL,               -- ISO date of the pull
    filename     TEXT,
    row_count    INTEGER,
    file_hash    TEXT UNIQUE,                 -- sha256 of the export; blocks double-ingest
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS licenses (
    license_row_id  INTEGER PRIMARY KEY,
    snapshot_id     INTEGER NOT NULL REFERENCES snapshots(snapshot_id),
    serial_number   TEXT NOT NULL,            -- stable key across snapshots
    legal_name      TEXT,
    trade_name      TEXT,                     -- legal != trade; both needed for matching
    address         TEXT,
    zip             TEXT,
    borough         TEXT,
    license_type    TEXT,                     -- On-Premises filter lives on this
    license_status  TEXT,                     -- transfer vs new (S1/S2 split)
    raw_json        TEXT NOT NULL,            -- full original row, verbatim
    UNIQUE (serial_number, snapshot_id)
);
CREATE INDEX IF NOT EXISTS idx_licenses_serial   ON licenses(serial_number);
CREATE INDEX IF NOT EXISTS idx_licenses_snapshot ON licenses(snapshot_id);

CREATE TABLE IF NOT EXISTS businesses (
    business_id        INTEGER PRIMARY KEY,
    canonical_name     TEXT NOT NULL,
    address            TEXT,
    zip                TEXT,
    borough            TEXT,
    segment            TEXT CHECK (segment IN ('S1','S2','S3','S4') OR segment IS NULL),
    status             TEXT NOT NULL DEFAULT 'unknown'
                       CHECK (status IN ('pre_open','open','closed','unknown')),
    chain_flag         INTEGER NOT NULL DEFAULT 0,      -- hard disqualifier
    franchise_control  TEXT,                            -- brand_controlled / owner_controlled / unknown
    first_seen         TEXT,                            -- derived from snapshots
    last_seen          TEXT,
    notes              TEXT
);

-- Which raw records belong to which business. Also the fuzzy-match review log.
CREATE TABLE IF NOT EXISTS business_sources (
    source            TEXT NOT NULL,          -- 'sla', 'dohmh', 'dob', ...
    external_key      TEXT NOT NULL,          -- serial number / CAMIS / permit #
    business_id       INTEGER NOT NULL REFERENCES businesses(business_id),
    match_method      TEXT NOT NULL DEFAULT 'manual'
                      CHECK (match_method IN ('serial','camis','fuzzy','manual')),
    match_confidence  REAL,                   -- 0-1, meaningful for fuzzy only
    needs_review      INTEGER NOT NULL DEFAULT 0,  -- 1 = unconfirmed fuzzy match
    linked_at         TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source, external_key)
);
CREATE INDEX IF NOT EXISTS idx_bsources_business ON business_sources(business_id);

-- Google Places results. Check here before every API call — cache is money.
CREATE TABLE IF NOT EXISTS places_cache (
    cache_id         INTEGER PRIMARY KEY,
    business_id      INTEGER NOT NULL REFERENCES businesses(business_id),
    queried_at       TEXT NOT NULL DEFAULT (datetime('now')),
    business_status  TEXT,                    -- OPERATIONAL / CLOSED_* / NO_LISTING
    chain_flag       INTEGER,
    website          TEXT,
    phone            TEXT,
    maps_url         TEXT,
    raw_json         TEXT
);
CREATE INDEX IF NOT EXISTS idx_places_business ON places_cache(business_id, queried_at);

CREATE TABLE IF NOT EXISTS enrichments (
    enrichment_id     INTEGER PRIMARY KEY,
    business_id       INTEGER NOT NULL REFERENCES businesses(business_id),
    doordash          TEXT,                   -- none / listed / third_party_only
    website_status    TEXT,                   -- none / live / under_construction
    platform          TEXT,                   -- toast / square / clover / other / none / unknown
    ordering_evidence TEXT,                   -- URL/fingerprint that proved it
    hosting           TEXT,                   -- godaddy / other / unknown
    hosting_evidence  TEXT,                   -- nameserver / WHOIS detail
    size_estimate     TEXT,                   -- headcount range
    locations_count   INTEGER,
    contact_name      TEXT,
    contact_info      TEXT,                   -- phone / email
    primary_angle     TEXT,                   -- PITCH_ANGLES.md id (working value)
    pitch_line        TEXT,                   -- working value; delivered version freezes in leads
    evidence_links    TEXT,                   -- Maps URL, site, listing (LEAD_SPEC required)
    enriched_at       TEXT NOT NULL DEFAULT (datetime('now')),
    enriched_by       TEXT NOT NULL CHECK (enriched_by IN ('brad','jack','ai','bot'))
);
CREATE INDEX IF NOT EXISTS idx_enrich_business ON enrichments(business_id, enriched_at);

CREATE TABLE IF NOT EXISTS batches (
    batch_id       INTEGER PRIMARY KEY,
    label          TEXT NOT NULL UNIQUE,      -- 'Pilot A', 'W29'
    delivered_at   TEXT,                      -- null until sent
    xlsx_filename  TEXT,
    notes          TEXT
);

-- What actually went to Simon. Frozen at delivery. This table proves the 3-5%.
CREATE TABLE IF NOT EXISTS leads (
    lead_id        INTEGER PRIMARY KEY,
    business_id    INTEGER NOT NULL REFERENCES businesses(business_id),
    batch_id       INTEGER NOT NULL REFERENCES batches(batch_id),
    score          REAL,
    rank           INTEGER,
    primary_angle  TEXT,
    pitch_line     TEXT,
    outcome        TEXT NOT NULL DEFAULT 'queued'
                   CHECK (outcome IN ('queued','delivered','called','closed','rejected')),
    outcome_notes  TEXT,
    outcome_at     TEXT,
    UNIQUE (business_id, batch_id)
);
CREATE INDEX IF NOT EXISTS idx_leads_batch   ON leads(batch_id);
CREATE INDEX IF NOT EXISTS idx_leads_outcome ON leads(outcome);

-- Newest places row per business + age. The "should I spend an API call" check:
-- stale (>30d), unknown status, or no row at all => query the API.
CREATE VIEW IF NOT EXISTS v_latest_places AS
SELECT p.*, CAST(julianday('now') - julianday(p.queried_at) AS INTEGER) AS age_days
FROM places_cache p
JOIN (SELECT business_id, MAX(queried_at) AS latest
      FROM places_cache GROUP BY business_id) m
  ON p.business_id = m.business_id AND p.queried_at = m.latest;

-- Newest enrichment per business. What the scorer and xlsx builder read.
CREATE VIEW IF NOT EXISTS v_latest_enrichment AS
SELECT e.*
FROM enrichments e
JOIN (SELECT business_id, MAX(enriched_at) AS latest
      FROM enrichments GROUP BY business_id) m
  ON e.business_id = m.business_id AND e.enriched_at = m.latest;
