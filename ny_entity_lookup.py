#!/usr/bin/env python3
"""
ny_entity_lookup.py  (v1 scaffold)
----------------------------------
Looks up NY legal entities in the state's public "Active Corporations:
Beginning 1800" dataset (data.ny.gov, dataset n9v6-gdp6). Free, no API key.

This automates the "NYS entity search" open item on every lead: it can
confirm a legal entity exists, when it filed (a timing signal), its county,
registered agent, and — when the biennial statement was filed — a CEO name.

What it CANNOT do (be honest in the lead row):
  - Trade name != legal name. "Nippon Cha" may be "KATANA MATCHA LLC".
    Search by ADDRESS words when the name search comes up empty.
  - NY doesn't systematically publish owners/officers. CEO fields are often
    blank or stale. A human still resolves "who actually owns it" for
    ambiguous cases — this script narrows, it doesn't close.
  - DBAs for LLCs are filed at the county level and aren't in this dataset.

Run it:
  python3 ny_entity_lookup.py --name "GRAND ASTORIA"
  python3 ny_entity_lookup.py --name "STATION FOODS" --county KINGS
  python3 ny_entity_lookup.py --q "1913 BRONXDALE"        (full-text: catches addresses)
  python3 ny_entity_lookup.py --name "WO HOP" --json      (raw records, every field)

Notes:
  - Without an app token Socrata throttles heavy use; our volumes are tiny.
    If it ever matters, get a free token at data.ny.gov and put
    SOCRATA_APP_TOKEN=... in .env.
  - Results print every non-empty field, so if the state renames columns
    the script keeps working — nothing is hardcoded to a column list.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

DATASET_URL = "https://data.ny.gov/resource/n9v6-gdp6.json"
TIMEOUT = 20

# Fields worth showing first when present (order of usefulness to us).
PREFERRED_ORDER = [
    "current_entity_name", "dos_id", "initial_dos_filing_date", "entity_type",
    "county", "jurisdiction", "ceo_name", "registered_agent_name",
    "dos_process_name", "dos_process_address_1", "dos_process_city",
]


def query(params):
    headers = {}
    token = os.environ.get("SOCRATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
    r = requests.get(DATASET_URL, params=params, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def search(name=None, q=None, county=None, limit=10):
    """Two strategies:
    1) --name: case-insensitive 'contains' on the entity-name column.
    2) --q:    Socrata full-text search across ALL columns (also catches
               addresses and agent names). Used automatically as a fallback
               when the name search returns nothing.
    """
    params = {"$limit": str(limit)}
    if county:
        params["$where"] = f"upper(county) = '{county.upper()}'"
    if name:
        clause = f"upper(current_entity_name) like '%{name.upper().replace(chr(39), chr(39)*2)}%'"
        params["$where"] = (params.get("$where", "") + " AND " + clause) if "$where" in params else clause
        try:
            rows = query(params)
            if rows:
                return rows, "name-contains"
        except requests.HTTPError:
            pass  # column name may differ — fall through to full-text
        params.pop("$where", None)
        if county:
            params["$where"] = f"upper(county) = '{county.upper()}'"
        params["$q"] = name
        return query(params), "full-text fallback"
    if q:
        params["$q"] = q
        return query(params), "full-text"
    sys.exit("Give me --name or --q. Run with -h for examples.")


def print_rows(rows):
    for i, row in enumerate(rows, 1):
        print(f"\n--- match {i} " + "-" * 50)
        shown = set()
        for k in PREFERRED_ORDER:
            if row.get(k):
                print(f"  {k:28s} {row[k]}")
                shown.add(k)
        for k, v in row.items():
            if v and k not in shown:
                print(f"  {k:28s} {v}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", help="entity legal name (partial ok): --name 'GRAND ASTORIA'")
    ap.add_argument("--q", help="full-text search across every field (addresses work here)")
    ap.add_argument("--county", help="narrow to a county: KINGS, QUEENS, NEW YORK, BRONX, RICHMOND")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true", help="dump raw records instead of the tidy view")
    args = ap.parse_args()

    rows, how = search(name=args.name, q=args.q, county=args.county, limit=args.limit)
    if not rows:
        print("No matches. Remember: trade name != legal name. Try --q with the "
              "street address (e.g. --q '1913 BRONXDALE'), or a distinctive word "
              "from the name. If still nothing, it may be a county-level DBA — "
              "that needs the manual NYS DOS / county clerk search.")
        return
    print(f"{len(rows)} match(es) via {how} search:")
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print_rows(rows)
        print("\nReminder: CEO/agent fields are often stale or blank — treat a hit "
              "as 'entity confirmed', not 'owner confirmed'. Log verified_as_of.")


if __name__ == "__main__":
    main()
