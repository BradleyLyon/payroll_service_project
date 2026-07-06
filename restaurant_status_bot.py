#!/usr/bin/env python3
"""
restaurant_status_bot.py  (v2 — DOHMH-first, no false positives)
----------------------------------------------------------------
Pipeline per SLA row:
  1. NYC five-borough zip filter (default; --all-ny to disable)
  2. DOHMH inspections lookup (free, keyless, deterministic):
       - match by building number + zipcode, then name-similarity to pick the right CAMIS
       - inspection_date 1900-01-01  -> CONFIRMED pre-open (permitted, never inspected)
       - real inspections            -> CONFIRMED active
       - same address, different DBA -> possible ownership change hint (S1)
       - grabs CAMIS, BIN, BBL, phone
  3. Google Places (enrichment ONLY, never the source of truth):
       - a match counts ONLY if its street number and zip agree with the input
       - mismatched matches are discarded (this killed the RYE/Jolie-Laide false "already_open")
  4. Chain / multi-location classification (conservative — always marked "verify")

Truth policy: every status is labeled confirmed_* (a government record proves it)
or unverified_* (inference only). The bot never asserts what it cannot prove.

Setup:
  pip install requests python-dotenv
  .env next to this script:  GOOGLE_PLACES_API_KEY=...   (SERPER_API_KEY optional)

Run:
  python3 restaurant_status_bot.py "Pending Licenses.csv" --limit 40 --restaurants-only --out enriched.csv
"""

import argparse
import csv
import os
import re
import sys
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

PLACES_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DOHMH_URL = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"

KNOWN_CHAIN_HINTS = {
    "chipotle", "starbucks", "dunkin", "mcdonald", "subway",
    "ralph's coffee", "shake shack", "sweetgreen", "chick-fil-a", "panera",
    "popeyes", "wendy", "taco bell", "kfc", "burger king", "domino",
    "pret a manger", "eataly", "gyu kaku", "gyu-kaku",
}
CHAIN_LOCATION_THRESHOLD = 8

NYC_ZIP_PREFIXES = ("100", "101", "102", "103", "104",
                    "111", "112", "113", "114", "116")
NYC_ZIP_EXCEPTIONS = {"11004", "11005"}


def is_nyc_zip(zp: str) -> bool:
    zp = (zp or "").strip()
    return zp in NYC_ZIP_EXCEPTIONS or (len(zp) >= 3 and zp[:3] in NYC_ZIP_PREFIXES)


# ---------------------------------------------------------------- utils

def norm_name(s: str) -> str:
    """Lowercase, strip punctuation and legal suffixes for name comparison."""
    s = (s or "").lower()
    s = re.sub(r"\b(llc|inc|corp|corporation|co|ltd|restaurant|cafe|the)\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(s.split())


def name_similarity(a: str, b: str) -> float:
    """Token-overlap similarity in [0,1]. Cheap, dependency-free."""
    ta, tb = set(norm_name(a).split()), set(norm_name(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def building_number(address1: str) -> str:
    """First token of the street address ('39-22 61st St' -> '39-22', '285 Lafayette' -> '285')."""
    tok = (address1 or "").strip().split()
    return tok[0] if tok else ""


def leading_number(formatted: str) -> str:
    """Leading house number of a Places formatted_address."""
    m = re.match(r"\s*([0-9][0-9\-]*)", formatted or "")
    return m.group(1) if m else ""


def zip_in(formatted: str) -> str:
    m = re.search(r"\b(\d{5})(?:-\d{4})?\b(?!.*\b\d{5}\b)", formatted or "")
    return m.group(1) if m else ""


# ---------------------------------------------------------------- DOHMH

def dohmh_lookup(bldg: str, zp: str, lead_name: str):
    """Query DOHMH by building+zip. Returns dict of confirmed facts (or reasons why not)."""
    out = {
        "camis": "", "dohmh_dba": "", "dohmh_phone": "", "bin": "", "bbl": "",
        "dohmh_status": "no_dohmh_record",
        "same_address_other_dba": "",
    }
    if not bldg or not zp:
        out["dohmh_status"] = "dohmh_skipped (no building/zip)"
        return out
    try:
        r = requests.get(DOHMH_URL, params={
            "$where": f"building='{bldg}' AND zipcode='{zp}'",
            "$select": "camis,dba,phone,inspection_date,bin,bbl",
            "$limit": "200",
        }, timeout=20)
        if r.status_code != 200:
            out["dohmh_status"] = f"dohmh_error {r.status_code}"
            return out
        rows = r.json()
    except Exception as e:
        out["dohmh_status"] = f"dohmh_error {e}"
        return out

    if not rows:
        return out  # no_dohmh_record — honest answer, NOT proof of pre-open

    by_camis = {}
    for row in rows:
        by_camis.setdefault(row.get("camis", ""), []).append(row)

    # pick the CAMIS whose DBA best matches the lead name
    best, best_sim = None, 0.0
    for camis, rws in by_camis.items():
        sim = name_similarity(lead_name, rws[0].get("dba", ""))
        if sim > best_sim:
            best, best_sim = camis, sim

    other_dbas = sorted({r0.get("dba", "") for r0 in rows
                         if r0.get("dba") and name_similarity(lead_name, r0.get("dba", "")) < 0.5})
    if other_dbas:
        out["same_address_other_dba"] = "; ".join(other_dbas[:5])

    if best is None or best_sim < 0.5:
        out["dohmh_status"] = "dohmh_address_known_no_name_match"
        return out

    match_rows = by_camis[best]
    r0 = match_rows[0]
    out.update({"camis": best, "dohmh_dba": r0.get("dba", ""),
                "dohmh_phone": r0.get("phone", ""),
                "bin": r0.get("bin", ""), "bbl": r0.get("bbl", "")})

    dates = {rw.get("inspection_date", "") for rw in match_rows}
    real_inspections = [d for d in dates if d and not d.startswith("1900-01-01")]
    if real_inspections:
        out["dohmh_status"] = "confirmed_active (inspected)"
    elif any(d.startswith("1900-01-01") for d in dates):
        out["dohmh_status"] = "confirmed_preopen (permitted, never inspected)"
    else:
        out["dohmh_status"] = "dohmh_record_no_dates"
    return out


# ---------------------------------------------------------------- Places

def places_text_search(query, field_mask, max_results=5):
    headers = {"Content-Type": "application/json",
               "X-Goog-Api-Key": PLACES_KEY,
               "X-Goog-FieldMask": field_mask}
    try:
        resp = requests.post(TEXT_SEARCH_URL, headers=headers,
                             json={"textQuery": query, "maxResultCount": max_results},
                             timeout=20)
    except Exception as e:
        return {"_error": str(e)}
    if resp.status_code != 200:
        return {"_error": f"{resp.status_code}: {resp.text[:200]}"}
    return resp.json().get("places", [])


def places_lookup(name, address, bldg, zp):
    """Places enrichment with strict address validation. A hit that isn't at the
    lead's building+zip is DISCARDED (that's how Google invented 'already open'
    for pre-opens by matching some other place)."""
    out = {"places_match": "N", "business_status": "", "website": "",
           "match_address": "", "maps_url": "", "places_note": ""}
    if not PLACES_KEY:
        out["places_note"] = "no API key — Places skipped"
        return out
    mask = ("places.displayName,places.formattedAddress,"
            "places.businessStatus,places.id,places.websiteUri")
    res = places_text_search(f"{name} {address}", mask, max_results=5)
    if isinstance(res, dict) and res.get("_error"):
        out["places_note"] = "API error: " + res["_error"]
        return out
    if not res:
        out["places_note"] = "no Places results"
        return out

    for p in res:
        fa = p.get("formattedAddress", "")
        if leading_number(fa) == bldg and (not zip_in(fa) or zip_in(fa) == zp):
            nm = (p.get("displayName", {}) or {}).get("text", "")
            if name_similarity(name, nm) < 0.34:
                continue  # right address, wrong business (e.g. the Pret upstairs)
            out.update({
                "places_match": "Y",
                "business_status": p.get("businessStatus", ""),
                "website": p.get("websiteUri", ""),
                "match_address": fa,
                "maps_url": f"https://www.google.com/maps/place/?q=place_id:{p.get('id','')}"
                            if p.get("id") else "",
            })
            return out

    out["places_note"] = (f"results found but none at building {bldg} / zip {zp} "
                          f"(closest: {res[0].get('formattedAddress','')})")
    return out


def location_scan(name):
    """Count plausible same-name locations. NEVER definitive — always 'verify'."""
    out = {"location_count": 0, "chain_flag": "N", "multi_location": "N", "loc_note": ""}
    if any(h in (name or "").lower() for h in KNOWN_CHAIN_HINTS):
        out["chain_flag"] = "Y"
        out["loc_note"] = "known chain name"
        return out
    if not PLACES_KEY or not norm_name(name):
        return out
    res = places_text_search(f"{name} New York",
                             "places.formattedAddress,places.displayName",
                             max_results=10)
    if not isinstance(res, list):
        return out
    addrs = set()
    for p in res:
        dn = (p.get("displayName", {}) or {}).get("text", "")
        if name_similarity(name, dn) >= 0.67:
            addrs.add(p.get("formattedAddress", ""))
    n = len(addrs)
    out["location_count"] = n
    if n >= CHAIN_LOCATION_THRESHOLD:
        out["chain_flag"] = "Y"
        out["loc_note"] = f"{n} same-name hits — chain scale (VERIFY: generic names collide)"
    elif n >= 2:
        out["multi_location"] = "Y"
        out["loc_note"] = f"{n} same-name hits — possible multi-location independent (VERIFY same owner)"
    return out


# ---------------------------------------------------------------- signal synthesis

def synthesize(dohmh, places):
    """One honest opening_signal from all evidence. DOHMH outranks Places."""
    ds, ps = dohmh["dohmh_status"], places.get("business_status", "")
    if ds.startswith("confirmed_preopen"):
        return "confirmed_preopen (DOHMH permitted, never inspected)"
    if ds.startswith("confirmed_active"):
        if ps == "CLOSED_PERMANENTLY":
            return "conflict: DOHMH active vs Places closed — HUMAN CHECK"
        return "confirmed_active (DOHMH inspection history)"
    if ds == "dohmh_address_known_no_name_match":
        others = dohmh.get("same_address_other_dba", "")
        base = "possible_new_tenant_or_ownership_change (address in DOHMH under different name"
        return base + (f": {others})" if others else ")")
    # no DOHMH record at all:
    if places["places_match"] == "Y":
        if ps == "OPERATIONAL":
            return "unverified_open (Places match at correct address; no DOHMH record — could be very new)"
        if ps == "CLOSED_PERMANENTLY":
            return "unverified_closed (Places says closed; no DOHMH record)"
        if ps == "CLOSED_TEMPORARILY":
            return "unverified_closed_temporarily (possible reopen / new owner)"
        return "unverified_listing_found"
    return "unverified_preopen (no DOHMH record, no address-validated Places listing)"


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--out", default="enriched.csv")
    ap.add_argument("--restaurants-only", action="store_true")
    ap.add_argument("--all-ny", action="store_true",
                    help="Include all of NY state (default: NYC five boroughs only)")
    args = ap.parse_args()

    food_terms = ("restaurant", "food & beverage", "summer food")
    out_rows, skipped_geo = [], 0

    with open(args.csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if count >= args.limit:
                break
            desc = (row.get("Description") or "").lower()
            if args.restaurants_only and not any(t in desc for t in food_terms):
                continue
            zp = (row.get("ZIP") or "").strip()[:5]
            if not args.all_ny and not is_nyc_zip(zp):
                skipped_geo += 1
                continue

            name = (row.get("Premise DBA") or "").strip() or (row.get("Premise Name") or "").strip()
            a1 = (row.get("Address1") or "").strip()
            city = (row.get("City") or "").strip()
            address = ", ".join(x for x in [a1, city, "NY", zp] if x)
            bldg = building_number(a1)

            print(f"[{count+1}/{args.limit}] {name} — {address}")

            dohmh = dohmh_lookup(bldg, zp, name)
            places = places_lookup(name, address, bldg, zp)
            locs = location_scan(name)
            signal = synthesize(dohmh, places)

            notes = " | ".join(x for x in [places.get("places_note", ""),
                                           locs.get("loc_note", "")] if x)

            out_rows.append({
                "search_name": name, "address": address, "zip": zp,
                "category": row.get("Category", ""),
                "description": row.get("Description", ""),
                "license_status": (row.get("License Status") or row.get("Status")
                                   or row.get("Application Status") or ""),
                "opening_signal": signal,
                "camis": dohmh["camis"], "dohmh_dba": dohmh["dohmh_dba"],
                "dohmh_phone": dohmh["dohmh_phone"],
                "bin": dohmh["bin"], "bbl": dohmh["bbl"],
                "same_address_other_dba": dohmh["same_address_other_dba"],
                "places_match": places["places_match"],
                "business_status": places["business_status"],
                "website": places["website"],
                "match_address": places["match_address"],
                "location_count": locs["location_count"],
                "chain_flag": locs["chain_flag"],
                "multi_location": locs["multi_location"],
                "notes": notes, "maps_url": places["maps_url"],
            })
            count += 1
            time.sleep(0.3)

    cols = ["search_name", "address", "zip", "category", "description", "license_status",
            "opening_signal", "camis", "dohmh_dba", "dohmh_phone", "bin", "bbl",
            "same_address_other_dba", "places_match", "business_status", "website",
            "match_address", "location_count", "chain_flag", "multi_location",
            "notes", "maps_url"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nWrote {len(out_rows)} rows to {args.out}"
          + (f" ({skipped_geo} skipped — outside NYC five boroughs)" if skipped_geo else ""))


if __name__ == "__main__":
    main()
