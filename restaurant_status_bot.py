#!/usr/bin/env python3
"""
restaurant_status_bot.py
------------------------
Takes the SLA pending-license CSV, processes the first N rows, and for each one
asks the Google Places API two questions:

  1. Is this an opening / new restaurant?  (via businessStatus + "not found yet")
  2. Does it have other locations? If so, classify:
       - CHAIN (known brand name or 8+ locations)  -> set aside
       - MULTI-LOCATION independent (2-7 locations) -> POSITIVE signal (S3 sweet spot, +2)

Setup (run once, locally):
  pip install requests python-dotenv
  Get a key: https://console.cloud.google.com  -> enable "Places API (New)"
  Put it in a .env file next to this script:
      GOOGLE_PLACES_API_KEY=your_key
  Optional, for "coming soon" news signal:
      SERPER_API_KEY=your_serper_key

Run:
  python3 restaurant_status_bot.py "Pending Licenses.csv" --limit 20 --restaurants-only --out enriched.csv
  # NYC five boroughs only is the DEFAULT. Add --all-ny to include the whole state.

Output columns:
  search_name, address, zip, category, description, license_status, found,
  business_status, match_address, location_count, chain_flag, multi_location,
  opening_signal, notes, maps_url
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import requests

# --- load .env sitting next to this script (works in PyCharm too) ----------
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # fall back to shell-exported env vars

PLACES_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
SERPER_KEY = os.environ.get("SERPER_API_KEY")
SERP_ENABLED = bool(SERPER_KEY)

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Words in a name that almost always mean "national chain -> set aside"
KNOWN_CHAIN_HINTS = {
    "chipotle", "starbucks", "dunkin", "mcdonald", "subway", "ralph lauren",
    "ralph's coffee", "shake shack", "sweetgreen", "chick-fil-a", "panera",
    "popeyes", "wendy", "taco bell", "kfc", "burger king", "domino",
}

# location_count at or above this = treat as chain even without a name match
CHAIN_LOCATION_THRESHOLD = 8

# NYC five boroughs by ZIP prefix:
#   100-102 Manhattan · 103 Staten Island · 104 Bronx
#   110/111/113/114/116 Queens · 112 Brooklyn
NYC_ZIP_PREFIXES = ("100", "101", "102", "103", "104",
                    "110", "111", "112", "113", "114", "116")


def is_nyc_zip(zp: str) -> bool:
    zp = (zp or "").strip()
    return len(zp) >= 3 and zp[:3] in NYC_ZIP_PREFIXES


def places_text_search(query, field_mask, location_bias=None, max_results=5):
    """Call Places Text Search (New). Returns list of place dicts."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": PLACES_KEY,
        "X-Goog-FieldMask": field_mask,
    }
    body = {"textQuery": query, "maxResultCount": max_results}
    if location_bias:
        body["locationBias"] = location_bias
    resp = requests.post(TEXT_SEARCH_URL, headers=headers, json=body, timeout=20)
    if resp.status_code != 200:
        return {"_error": f"{resp.status_code}: {resp.text[:200]}"}
    return resp.json().get("places", [])


def check_lead(name, address, city):
    """Return a dict of enrichment fields for one lead."""
    result = {
        "found": "N",
        "business_status": "",
        "match_address": "",
        "location_count": 0,
        "chain_flag": "N",       # known brand OR 8+ locations -> disqualify
        "multi_location": "N",   # 2-7 same-name locations -> POSITIVE (S3, +2)
        "opening_signal": "",
        "notes": "",
        "maps_url": "",
    }

    # Fast pre-filter: obvious national chains by name
    low = name.lower()
    if any(h in low for h in KNOWN_CHAIN_HINTS) or "#" in name:
        result["chain_flag"] = "Y"
        result["notes"] = "Name matches a known chain pattern."

    # --- Q1: status of the exact premise -------------------------------
    mask = ("places.displayName,places.formattedAddress,"
            "places.businessStatus,places.id,places.websiteUri")
    exact = places_text_search(f"{name} {address}", mask, max_results=3)
    if isinstance(exact, dict) and exact.get("_error"):
        result["notes"] = (result["notes"] + " | API error: " + exact["_error"]).strip(" |")
        return result

    if not exact:
        # Pending license but Google has no listing -> strong "not open yet" signal
        result["opening_signal"] = "likely_preopen (no Google listing yet)"
        result["notes"] = (result["notes"] + " | Pending license, no Maps listing.").strip(" |")
    else:
        top = exact[0]
        result["found"] = "Y"
        result["business_status"] = top.get("businessStatus", "")
        result["match_address"] = top.get("formattedAddress", "")
        pid = top.get("id", "")
        if pid:
            result["maps_url"] = f"https://www.google.com/maps/place/?q=place_id:{pid}"
        bs = result["business_status"]
        if bs == "OPERATIONAL":
            result["opening_signal"] = "already_open (verify if recent / new owner)"
        elif bs in ("CLOSED_TEMPORARILY",):
            result["opening_signal"] = "closed_temporarily (possible reopen / new owner)"
        elif bs in ("CLOSED_PERMANENTLY",):
            result["opening_signal"] = "closed_permanently (skip)"

    # --- Q2: other locations? (chain vs multi-location independent) ----
    name_only = places_text_search(name, "places.formattedAddress,places.displayName",
                                   max_results=10)
    if isinstance(name_only, list) and name_only:
        addrs = set()
        for p in name_only:
            dn = (p.get("displayName", {}) or {}).get("text", "").lower()
            # only count matches whose name actually resembles our lead
            if dn and (low[:6] in dn or dn[:6] in low):
                addrs.add(p.get("formattedAddress", ""))
        result["location_count"] = len(addrs)
        if len(addrs) >= CHAIN_LOCATION_THRESHOLD:
            result["chain_flag"] = "Y"
            result["notes"] = (result["notes"] +
                               f" | {len(addrs)} locations — chain scale.").strip(" |")
        elif len(addrs) >= 2 and result["chain_flag"] == "N":
            result["multi_location"] = "Y"
            result["notes"] = (result["notes"] +
                               f" | {len(addrs)} locations — multi-location independent (S3 signal). "
                               f"Verify same business, not name collision.").strip(" |")

    # --- Optional: "coming soon" news signal via SERP ------------------
    if SERP_ENABLED and result["opening_signal"].startswith("likely_preopen"):
        try:
            r = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
                json={"q": f"{name} {city} restaurant opening"},
                timeout=20,
            )
            blob = (r.text or "").lower()
            for kw in ("coming soon", "now open", "grand opening", "set to open", "opening"):
                if kw in blob:
                    result["opening_signal"] += f" | news mentions '{kw}'"
                    break
        except Exception as e:
            result["notes"] = (result["notes"] + f" | SERP error: {e}").strip(" |")

    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--out", default="enriched.csv")
    ap.add_argument("--restaurants-only", action="store_true",
                    help="Only process rows whose Description looks like food service")
    ap.add_argument("--all-ny", action="store_true",
                    help="Include all of NY state (default: NYC five boroughs only)")
    args = ap.parse_args()

    if not PLACES_KEY:
        sys.exit("Set GOOGLE_PLACES_API_KEY (in .env next to this script, or export it).")

    food_terms = ("restaurant", "food & beverage", "summer food")
    out_rows = []
    skipped_geo = 0
    with open(args.csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if count >= args.limit:
                break
            desc = (row.get("Description") or "").lower()
            if args.restaurants_only and not any(t in desc for t in food_terms):
                continue
            zp = (row.get("ZIP") or "").strip()
            if not args.all_ny and not is_nyc_zip(zp):
                skipped_geo += 1
                continue
            name = (row.get("Premise DBA") or "").strip() or (row.get("Premise Name") or "").strip()
            a1 = (row.get("Address1") or "").strip()
            city = (row.get("City") or "").strip()
            address = ", ".join(x for x in [a1, city, "NY", zp] if x)

            print(f"[{count+1}/{args.limit}] {name} — {address}")
            enriched = check_lead(name, address, city)
            enriched.update({"search_name": name, "address": address, "zip": zp,
                             "category": row.get("Category", ""),
                             "description": row.get("Description", ""),
                             "license_status": (row.get("License Status")
                                                or row.get("Status")
                                                or row.get("Application Status") or "")})
            out_rows.append(enriched)
            count += 1
            time.sleep(0.3)  # be polite to the API

    cols = ["search_name", "address", "zip", "category", "description",
            "license_status", "found", "business_status", "match_address",
            "location_count", "chain_flag", "multi_location",
            "opening_signal", "notes", "maps_url"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nWrote {len(out_rows)} rows to {args.out}"
          + (f" ({skipped_geo} rows skipped — outside NYC five boroughs)" if skipped_geo else ""))


if __name__ == "__main__":
    main()
