#!/usr/bin/env python3
"""
restaurant_status_bot.py
------------------------
Takes the SLA pending-license CSV, processes the first N rows, and for each one
asks the Google Places API two questions:

  1. Is this an opening / new restaurant?  (via businessStatus + "not found yet")
  2. Does it have other locations? If so, flag it to SET ASIDE (chain).

Why Places API and not "googling" directly:
  - Google search results are not meant to be scraped. You get CAPTCHAs, IP
    bans, and a brittle parser. The Places API gives you structured fields
    (businessStatus, address, place id) that are exactly what you need.

Setup (run once, locally — NOT in a no-internet sandbox):
  pip install requests
  Get a key: https://console.cloud.google.com  -> enable "Places API (New)"
  export GOOGLE_PLACES_API_KEY="your_key"
  # Optional, for "coming soon" news signal (see SERP_ENABLED below):
  export SERPER_API_KEY="your_serper_key"   # from https://serper.dev

Run:
  python3 restaurant_status_bot.py Pending_Licenses.csv --limit 20 --out enriched.csv

Output columns:
  search_name, address, found, business_status, match_address,
  location_count, set_aside_chain, opening_signal, notes, maps_url
"""

import argparse
import csv
import os
import sys
import time

import requests

PLACES_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
SERPER_KEY = os.environ.get("SERPER_API_KEY")
SERP_ENABLED = bool(SERPER_KEY)  # the "coming soon" check turns on if you set the key

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Words in a name that almost always mean "national chain -> set aside"
KNOWN_CHAIN_HINTS = {
    "chipotle", "starbucks", "dunkin", "mcdonald", "subway", "ralph lauren",
    "ralph's coffee", "shake shack", "sweetgreen", "chick-fil-a", "panera",
    "popeyes", "wendy", "taco bell", "kfc", "burger king", "domino",
}


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
        "set_aside_chain": "N",
        "opening_signal": "",
        "notes": "",
        "maps_url": "",
    }

    # Fast pre-filter: obvious national chains by name
    low = name.lower()
    if any(h in low for h in KNOWN_CHAIN_HINTS) or "#" in name:
        result["set_aside_chain"] = "Y"
        result["notes"] = "Name matches a known chain pattern."
        # still worth confirming below, but flag is set

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

    # --- Q2: other locations? (chain detection) ------------------------
    # Search the bare name across a wide area; count distinct addresses.
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
        if len(addrs) > 1:
            result["set_aside_chain"] = "Y"
            extra = f"{len(addrs)} matching locations found."
            result["notes"] = (result["notes"] + " | " + extra).strip(" |")

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
    args = ap.parse_args()

    if not PLACES_KEY:
        sys.exit("Set GOOGLE_PLACES_API_KEY first.")

    food_terms = ("restaurant", "food & beverage", "summer food")
    out_rows = []
    with open(args.csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if count >= args.limit:
                break
            desc = (row.get("Description") or "").lower()
            if args.restaurants_only and not any(t in desc for t in food_terms):
                continue
            name = (row.get("Premise DBA") or "").strip() or (row.get("Premise Name") or "").strip()
            a1 = (row.get("Address1") or "").strip()
            city = (row.get("City") or "").strip()
            zp = (row.get("ZIP") or "").strip()
            address = ", ".join(x for x in [a1, city, "NY", zp] if x)

            print(f"[{count+1}/{args.limit}] {name} — {address}")
            enriched = check_lead(name, address, city)
            enriched.update({"search_name": name, "address": address,
                             "category": row.get("Category", ""),
                             "description": row.get("Description", "")})
            out_rows.append(enriched)
            count += 1
            time.sleep(0.3)  # be polite to the API

    cols = ["search_name", "address", "category", "description", "found",
            "business_status", "match_address", "location_count",
            "set_aside_chain", "opening_signal", "notes", "maps_url"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nWrote {len(out_rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
