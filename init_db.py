#!/usr/bin/env python3
"""init_db.py — create (or verify) leads.db from db/schema.sql.

Idempotent: safe to run on an existing DB (schema uses IF NOT EXISTS).
Usage:
    python init_db.py            # creates ./leads.db
    python init_db.py --db path/to/leads.db
"""
import argparse
import sqlite3
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "db" / "schema.sql"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="leads.db", help="path to the SQLite file (default: leads.db)")
    ap.add_argument("--schema", default=str(SCHEMA_PATH), help="path to schema.sql")
    args = ap.parse_args()

    schema_file = Path(args.schema)
    if not schema_file.exists():
        print(f"error: schema file not found at {schema_file}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(args.db)
    try:
        conn.executescript(schema_file.read_text())
        conn.commit()
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        views = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]
    finally:
        conn.close()

    print(f"ok: {args.db}")
    print(f"  tables: {', '.join(tables)}")
    print(f"  views:  {', '.join(views)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
