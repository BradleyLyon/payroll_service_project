#!/usr/bin/env python3
"""ingest_sla.py — load a LAMP pending-licenses CSV into leads.db as a snapshot,
then diff against the previous pull.

The diff is the lead generator:
  * NEW serials      -> this week's fresh candidates
  * VANISHED serials -> license left pending (approved/withdrawn) — status change worth knowing
  * STATUS-CHANGED   -> same serial, different license_status

Usage:
    python ingest_sla.py "data/pulls/pending_2026-07-06.csv"
    python ingest_sla.py "Pending Licenses.csv" --pulled-at 2026-07-06 --out data/diffs/new_2026-07-06.csv

Notes:
    - Idempotent: refuses to re-ingest a file whose sha256 already exists in `snapshots`.
    - Every original column is preserved in licenses.raw_json even if unmapped.
    - LAMP changes formats without notice (see DATA_SOURCES.md) — if you see
      "unmapped field" warnings, update COLUMN_ALIASES below and note the change.
"""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

SOURCE = "sla_pending"

# canonical field -> candidate header names (lowercased, alphanumerics only).
# LAMP headers drift; add aliases here rather than editing code below.
COLUMN_ALIASES = {
    "serial_number":  ["serialnumber", "serial", "licenseserialnumber"],
    "legal_name":     ["legalname", "premisesname", "licenseename", "applicant"],
    "trade_name":     ["tradename", "dba", "doingbusinessas", "doingbusinessasdba", "dbaname"],
    "address":        ["address", "premisesaddress", "streetaddress", "address1"],
    "zip":            ["zip", "zipcode", "postalcode"],
    "borough":        ["borough", "county", "city"],
    "license_type":   ["licensetype", "licensetypename", "type", "licenseclass"],
    "license_status": ["licensestatus", "status", "applicationstatus"],
}


def norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def build_column_map(headers):
    """Map canonical field -> actual CSV header. Warn on gaps, don't fail."""
    normed = {norm(h): h for h in headers}
    mapping, missing = {}, []
    for field, aliases in COLUMN_ALIASES.items():
        hit = next((normed[a] for a in aliases if a in normed), None)
        if hit:
            mapping[field] = hit
        else:
            missing.append(field)
    for field in missing:
        print(f"  warning: unmapped field '{field}' — raw_json still has everything; "
              f"add its header to COLUMN_ALIASES", file=sys.stderr)
    if "serial_number" not in mapping:
        raise SystemExit("error: cannot find a serial-number column — the diff engine "
                         "needs it. Headers seen: " + ", ".join(headers))
    return mapping


def infer_pulled_at(csv_path: Path) -> str:
    """Try YYYY-MM-DD from the filename; fall back to today."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", csv_path.name)
    return m.group(1) if m else date.today().isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_path", help="path to the LAMP export CSV")
    ap.add_argument("--db", default="leads.db")
    ap.add_argument("--pulled-at", default=None, help="ISO date of the pull (default: from filename or today)")
    ap.add_argument("--out", default=None, help="optional path: write NEW candidate rows as CSV")
    args = ap.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"error: {csv_path} not found", file=sys.stderr)
        return 1

    raw_bytes = csv_path.read_bytes()
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    pulled_at = args.pulled_at or infer_pulled_at(csv_path)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # -- idempotency guard ----------------------------------------------------
    dup = conn.execute("SELECT snapshot_id, pulled_at FROM snapshots WHERE file_hash = ?",
                       (file_hash,)).fetchone()
    if dup:
        print(f"already ingested: this exact file is snapshot #{dup['snapshot_id']} "
              f"(pulled_at {dup['pulled_at']}). Nothing to do.")
        return 0

    # -- read csv ---------------------------------------------------------------
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        colmap = build_column_map(headers)
        rows = list(reader)
    if not rows:
        print("error: CSV has headers but no rows — bad export?", file=sys.stderr)
        return 1

    # -- previous snapshot (before we insert the new one) -----------------------
    prev = conn.execute(
        "SELECT snapshot_id, pulled_at FROM snapshots WHERE source = ? "
        "ORDER BY pulled_at DESC, snapshot_id DESC LIMIT 1", (SOURCE,)).fetchone()

    # -- insert snapshot + license rows -----------------------------------------
    cur = conn.execute(
        "INSERT INTO snapshots (source, pulled_at, filename, row_count, file_hash) "
        "VALUES (?, ?, ?, ?, ?)",
        (SOURCE, pulled_at, csv_path.name, len(rows), file_hash))
    snapshot_id = cur.lastrowid

    def field(row, name):
        return (row.get(colmap[name]) or "").strip() if name in colmap else None

    skipped = 0
    for row in rows:
        serial = field(row, "serial_number")
        if not serial:
            skipped += 1
            continue
        conn.execute(
            "INSERT OR IGNORE INTO licenses (snapshot_id, serial_number, legal_name, trade_name, "
            "address, zip, borough, license_type, license_status, raw_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (snapshot_id, serial, field(row, "legal_name"), field(row, "trade_name"),
             field(row, "address"), field(row, "zip"), field(row, "borough"),
             field(row, "license_type"), field(row, "license_status"),
             json.dumps(row, ensure_ascii=False)))
    conn.commit()

    print(f"snapshot #{snapshot_id}: {len(rows) - skipped} rows ingested from {csv_path.name} "
          f"(pulled_at {pulled_at})" + (f", {skipped} rows skipped (no serial)" if skipped else ""))

    # -- diff engine -------------------------------------------------------------
    if not prev:
        print("first pull for this source — everything is new; no diff to run.")
        conn.close()
        return 0

    new_rows = conn.execute("""
        SELECT serial_number, trade_name, legal_name, address, license_type, license_status
        FROM licenses WHERE snapshot_id = :cur
          AND serial_number NOT IN (SELECT serial_number FROM licenses WHERE snapshot_id = :prev)
        ORDER BY serial_number""", {"cur": snapshot_id, "prev": prev["snapshot_id"]}).fetchall()

    vanished = conn.execute("""
        SELECT serial_number, trade_name, legal_name, address
        FROM licenses WHERE snapshot_id = :prev
          AND serial_number NOT IN (SELECT serial_number FROM licenses WHERE snapshot_id = :cur)
        ORDER BY serial_number""", {"cur": snapshot_id, "prev": prev["snapshot_id"]}).fetchall()

    changed = conn.execute("""
        SELECT c.serial_number, c.trade_name, p.license_status AS old_status,
               c.license_status AS new_status
        FROM licenses c
        JOIN licenses p ON p.serial_number = c.serial_number AND p.snapshot_id = :prev
        WHERE c.snapshot_id = :cur AND IFNULL(c.license_status,'') != IFNULL(p.license_status,'')
        ORDER BY c.serial_number""", {"cur": snapshot_id, "prev": prev["snapshot_id"]}).fetchall()

    print(f"\ndiff vs snapshot #{prev['snapshot_id']} ({prev['pulled_at']}):")
    print(f"  NEW (fresh candidates): {len(new_rows)}")
    for r in new_rows[:20]:
        print(f"    {r['serial_number']}  {r['trade_name'] or r['legal_name'] or '?'}  "
              f"{r['address'] or ''}  [{r['license_status'] or '?'}]")
    if len(new_rows) > 20:
        print(f"    ... and {len(new_rows) - 20} more (use --out to get all as CSV)")

    print(f"  VANISHED (left pending — approved/withdrawn?): {len(vanished)}")
    for r in vanished[:10]:
        print(f"    {r['serial_number']}  {r['trade_name'] or r['legal_name'] or '?'}")

    print(f"  STATUS CHANGED: {len(changed)}")
    for r in changed[:10]:
        print(f"    {r['serial_number']}  {r['trade_name'] or '?'}: "
              f"{r['old_status']} -> {r['new_status']}")

    if args.out and new_rows:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(new_rows[0].keys())
            w.writerows([tuple(r) for r in new_rows])
        print(f"\nwrote {len(new_rows)} new candidates -> {out_path}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
