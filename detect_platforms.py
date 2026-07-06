#!/usr/bin/env python3
"""
detect_platforms.py  (v1 scaffold)
----------------------------------
One scan that feeds every batch. For each restaurant it answers:
  - What runs their online ordering? (Toast / Clover / Square / DoorDash
    Storefront / Sauce / marketplace-only / none)     -> PITCH_ANGLES 13/14/10a/10b/15
  - Who hosts their website?                          -> PITCH_ANGLES 11
  - Marker flags: Owner.com-built site, Resy+OpenTable sprawl,
    "cash only" stated on their own site              -> PITCH_ANGLES 15/12

Three ways to run it (pick ONE):

  1) SWEEP a neighborhood (needs GOOGLE_PLACES_API_KEY in .env):
       python3 detect_platforms.py --sweep "restaurants in Bushwick" --limit 20
     Uses Google Places to list restaurants, then classifies each one's website.
     No website found = third-party-only candidate (angle 10a) — the residue.

  2) CLASSIFY a CSV you already have (e.g. the bot's output — free, no key):
       python3 detect_platforms.py --csv enriched.csv
     Needs columns containing a name and a website URL (header names are
     matched loosely: "website", "site", "url" all work).

  3) TEST one website (free, no key):
       python3 detect_platforms.py --url https://thegrandastoria.com

  Sanity check without any network or key at all:
       python3 detect_platforms.py --selftest

Output: a CSV (default detected_YYYY-MM-DD.csv) whose columns line up with
the `enrichments` table in db/schema.sql, so ingesting it is trivial.

Truth policy (same as restaurant_status_bot.py): every value is either backed
by evidence (a URL or record we saw) or labeled unknown. The script never
asserts what it cannot prove.

Setup:
  pip install requests python-dotenv        (same as the bot)
  .env next to this script:  GOOGLE_PLACES_API_KEY=...  (only needed for --sweep)
                             SERPER_API_KEY=...          (optional, --confirm)

Cost guardrails: --sweep defaults to --limit 20 places. Every Places request
is announced before it's spent. Results should be cached in places_cache by
the ingest side — this script does not re-query anything it already printed.
"""

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

PLACES_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
SERPER_KEY = os.environ.get("SERPER_API_KEY")

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DOH_URL = "https://dns.google/resolve"          # DNS-over-HTTPS (free, keyless)
RDAP_URL = "https://rdap.org/domain/{domain}"    # registrar lookup (free, keyless)
UA = {"User-Agent": "Mozilla/5.0 (compatible; lead-research/1.0)"}
TIMEOUT = 12

# --------------------------------------------------------------- fingerprints
# THE TABLE IS DATA — Brad: add rows here, no logic changes needed.
# where: "url"  = pattern tested against every URL found (site address + every
#                 link on the homepage)
#        "html" = pattern tested against the homepage HTML itself
# platform / doordash map straight onto the enrichments columns.
# Source of each row: DATA_SOURCES.md §8 (confirmed in the wild 2026-07-06).
FINGERPRINTS = [
    dict(where="url", pattern=r"order\.toasttab\.com|toasttab\.com/local/order",
         platform="toast", angle="13", note="Toast online ordering"),
    dict(where="url", pattern=r"clover\.com/online-ordering",
         platform="clover", angle="tier5-clover", note="Clover online ordering"),
    dict(where="url", pattern=r"\.square\.site|squareup\.com/store|square\.link",
         platform="square", angle="14", note="Square ordering/site"),
    dict(where="url", pattern=r"order\.online/store",
         platform="doordash_storefront", angle="10b",
         note="DoorDash Storefront white-label — 'direct' ordering that isn't owned"),
    dict(where="url", pattern=r"getsauce\.com/order",
         platform="sauce", angle="10b", note="Sauce white-label ordering"),
    dict(where="url", pattern=r"doordash\.com/store",
         platform="marketplace:doordash", angle="10a", note="DoorDash marketplace listing"),
    dict(where="url", pattern=r"(grubhub|seamless)\.com",
         platform="marketplace:grubhub", angle="10a", note="Grubhub/Seamless listing"),
    dict(where="url", pattern=r"ubereats\.com",
         platform="marketplace:ubereats", angle="10a", note="UberEats listing"),
    dict(where="url", pattern=r"chownow\.com",
         platform="chownow", angle="other", note="ChowNow ordering (commission-free-ish; classify later)"),
    # HTML markers
    dict(where="html", pattern=r"we serve the following areas",
         platform="marker:ownercom", angle="ask-simon",
         note="Owner.com-built site (ordering solved, no POS/payroll) — open Simon question"),
    dict(where="html", pattern=r"cash\s*only",
         platform="marker:cash_only", angle="12",
         note="'Cash only' stated on their own site — gold-standard #12 evidence"),
]

# NS-record suffix -> hosting label (for the enrichments.hosting column).
# Only GoDaddy is a pitch signal (#11, unvalidated); the rest are context.
NS_HOSTING = {
    "domaincontrol.com": "godaddy",
    "wixdns.net": "wix",
    "squarespacedns.com": "squarespace",
    "shopify": "shopify",
    "cloudflare.com": "cloudflare (proxy — real host hidden)",
    "awsdns": "aws",
    "googledomains.com": "google",
    "registrar-servers.com": "namecheap",
}


# --------------------------------------------------------------- classification

def classify_urls(urls):
    """Run every url-type fingerprint over a list of URLs. Returns hits."""
    hits = []
    for fp in FINGERPRINTS:
        if fp["where"] != "url":
            continue
        for u in urls:
            if re.search(fp["pattern"], u, re.I):
                hits.append(dict(fp, evidence=u))
                break
    return hits


def classify_html(html):
    hits = []
    for fp in FINGERPRINTS:
        if fp["where"] == "html" and re.search(fp["pattern"], html, re.I):
            hits.append(dict(fp, evidence="homepage text match"))
    # Reservation-vendor sprawl (feeds angle #15): both Resy AND OpenTable present
    if re.search(r"resy\.com", html, re.I) and re.search(r"opentable\.com", html, re.I):
        hits.append(dict(platform="marker:resy+opentable", angle="15",
                         note="Both Resy and OpenTable linked — vendor sprawl",
                         evidence="homepage links"))
    return hits


def extract_links(html, base_url):
    """Every absolute URL on the page (href, src, plain text). Cheap, no parser."""
    urls = set(re.findall(r'https?://[^\s"\'<>)]+', html))
    urls.add(base_url)
    return sorted(urls)


def fetch_site(url):
    """Fetch a homepage. Returns (html, final_url) or ('', url) on any failure."""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
        return (r.text or ""), r.url
    except requests.RequestException:
        return "", url


def check_hosting(website):
    """Nameservers via DNS-over-HTTPS + registrar via RDAP. Both free/keyless.
    Returns (hosting_label, evidence_string). 'unknown' when we can't prove it."""
    if not website:
        return "unknown", ""
    domain = urlparse(website if website.startswith("http") else "https://" + website).netloc
    domain = domain.removeprefix("www.")
    if not domain:
        return "unknown", ""
    ns_names, registrar = [], ""
    try:
        r = requests.get(DOH_URL, params={"name": domain, "type": "NS"}, timeout=TIMEOUT)
        ns_names = [a.get("data", "").rstrip(".").lower()
                    for a in r.json().get("Answer", []) if a.get("type") == 2]
    except (requests.RequestException, ValueError):
        pass
    try:
        r = requests.get(RDAP_URL.format(domain=domain), headers=UA, timeout=TIMEOUT)
        if r.ok:
            for ent in r.json().get("entities", []):
                if "registrar" in ent.get("roles", []):
                    for item in ent.get("vcardArray", [None, []])[1]:
                        if item and item[0] == "fn":
                            registrar = item[3]
    except (requests.RequestException, ValueError):
        pass
    label = "unknown"
    for suffix, name in NS_HOSTING.items():
        if any(suffix in ns for ns in ns_names):
            label = name
            break
    if label == "unknown" and registrar and "godaddy" in registrar.lower():
        label = "godaddy (registrar; NS elsewhere)"
    evidence = f"NS={','.join(ns_names[:3]) or '?'}; registrar={registrar or '?'}"
    return label, evidence


def classify_business(name, website, confirm=False, city_hint="NYC"):
    """The core routine: one business in, one enrichments-shaped dict out."""
    row = dict(name=name, website=website or "", website_status="none",
               platform="none", ordering_evidence="", doordash="unknown",
               hosting="unknown", hosting_evidence="", markers="", angle_hint="",
               checked_at=dt.date.today().isoformat())
    if not website:
        # No website = 10a candidate. Optional Serper confirm of a marketplace listing.
        row["platform"] = "none"
        row["angle_hint"] = "10a candidate (no website found — confirm marketplace presence)"
        if confirm and SERPER_KEY:
            found = serper_marketplace_check(name, city_hint)
            row["doordash"] = "third_party_only" if found else "none"
            row["ordering_evidence"] = found or ""
            if found:
                row["angle_hint"] = "10a CONFIRMED (marketplace listing, no website)"
        return row

    html, final_url = fetch_site(website)
    row["website_status"] = "live" if html else "unreachable (verify by hand)"
    urls = extract_links(html, final_url) if html else [website]
    hits = classify_urls(urls) + (classify_html(html) if html else [])

    platforms = [h for h in hits if not h["platform"].startswith(("marker:", "marketplace:"))]
    markets   = [h for h in hits if h["platform"].startswith("marketplace:")]
    markers   = [h for h in hits if h["platform"].startswith("marker:")]

    if platforms:
        row["platform"] = platforms[0]["platform"]
        row["ordering_evidence"] = platforms[0]["evidence"]
        row["angle_hint"] = platforms[0]["angle"]
        if len(platforms) > 1:   # two real platforms at once -> fragmented stack
            row["angle_hint"] = "15 (fragmented: " + "+".join(p["platform"] for p in platforms) + ")"
    if markets:
        row["doordash"] = "listed" if platforms else "third_party_only"
        if not platforms:
            row["ordering_evidence"] = markets[0]["evidence"]
            row["angle_hint"] = "10a/10b (marketplace links only, no owned ordering)"
    row["markers"] = "; ".join(m["platform"].split(":", 1)[1] for m in markers)
    if any(m["platform"] == "marker:cash_only" for m in markers) and not row["angle_hint"]:
        row["angle_hint"] = "12 (cash only on own site)"

    row["hosting"], row["hosting_evidence"] = check_hosting(final_url or website)
    return row


def serper_marketplace_check(name, city_hint):
    """One Serper search: does a DoorDash/Grubhub listing exist for this name?
    Returns the listing URL or ''."""
    try:
        r = requests.post("https://google.serper.dev/search",
                          headers={"X-API-KEY": SERPER_KEY},
                          json={"q": f'"{name}" {city_hint} doordash OR grubhub'},
                          timeout=TIMEOUT)
        for item in r.json().get("organic", []):
            u = item.get("link", "")
            if re.search(r"(doordash|grubhub|seamless|ubereats)\.com", u, re.I):
                return u
    except (requests.RequestException, ValueError):
        pass
    return ""


# --------------------------------------------------------------- places sweep

def places_sweep(query, limit):
    """Text-search a neighborhood. Returns [(name, address, phone, place_id,
    business_status, website), ...]. Announces every paid request."""
    if not PLACES_KEY:
        sys.exit("Set GOOGLE_PLACES_API_KEY in .env to use --sweep.")
    fields = ("places.id,places.displayName,places.formattedAddress,"
              "places.websiteUri,places.businessStatus,places.nationalPhoneNumber,"
              "nextPageToken")
    out, token = [], None
    while len(out) < limit:
        body = {"textQuery": query, "pageSize": min(20, limit - len(out))}
        if token:
            body["pageToken"] = token
        print(f"  [Places request — ~{body['pageSize']} results]", file=sys.stderr)
        r = requests.post(TEXT_SEARCH_URL, json=body, timeout=TIMEOUT,
                          headers={"X-Goog-Api-Key": PLACES_KEY,
                                   "X-Goog-FieldMask": fields})
        r.raise_for_status()
        data = r.json()
        for p in data.get("places", []):
            out.append((p.get("displayName", {}).get("text", ""),
                        p.get("formattedAddress", ""),
                        p.get("nationalPhoneNumber", ""),
                        p.get("id", ""),
                        p.get("businessStatus", ""),
                        p.get("websiteUri", "")))
        token = data.get("nextPageToken")
        if not token:
            break
        time.sleep(2)   # token needs a moment to become valid
    return out[:limit]


# --------------------------------------------------------------- selftest

SELFTEST = [
    ("https://order.toasttab.com/online/choicebrooklyn", "toast"),
    ("https://www.clover.com/online-ordering/nippon-cha-williamsburg", "clover"),
    ("https://order.online/store/lincoln-station-brooklyn-40276781", "doordash_storefront"),
    ("https://getsauce.com/order/site/peppas-jerk-chicken", "sauce"),
    ("https://www.doordash.com/store/some-restaurant", "marketplace:doordash"),
    ("https://mycoolrestaurant.square.site", "square"),
]

def selftest():
    ok = True
    for url, expected in SELFTEST:
        hits = classify_urls([url])
        got = hits[0]["platform"] if hits else "none"
        status = "PASS" if got == expected else "FAIL"
        ok = ok and (status == "PASS")
        print(f"  {status}  {url}  ->  {got}")
    html_hits = classify_html("Welcome! We Serve The Following Areas: ... CASH ONLY please. "
                              "book at resy.com/x or opentable.com/y")
    got = sorted(h["platform"] for h in html_hits)
    want = ["marker:cash_only", "marker:ownercom", "marker:resy+opentable"]
    status = "PASS" if got == want else "FAIL"
    ok = ok and (status == "PASS")
    print(f"  {status}  html markers -> {got}")
    print("SELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


# --------------------------------------------------------------- main

OUT_COLS = ["name", "address", "phone", "place_id", "business_status",
            "website", "website_status", "platform", "ordering_evidence",
            "doordash", "hosting", "hosting_evidence", "markers",
            "angle_hint", "checked_at"]

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sweep", metavar='"restaurants in Bushwick"',
                      help="Places text search, then classify each result")
    mode.add_argument("--csv", metavar="FILE", help="classify businesses from a CSV")
    mode.add_argument("--url", metavar="URL", help="classify one website and exit")
    mode.add_argument("--selftest", action="store_true",
                      help="run offline fingerprint checks (no key, no network)")
    ap.add_argument("--limit", type=int, default=20,
                    help="max places to pull in --sweep (default 20 — keeps cost tiny)")
    ap.add_argument("--confirm", action="store_true",
                    help="for no-website places, spend one Serper search to confirm a marketplace listing")
    ap.add_argument("--out", default=f"detected_{dt.date.today().isoformat()}.csv")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if args.url:
        row = classify_business(name="(single-url test)", website=args.url)
        for k in OUT_COLS:
            print(f"{k:20s} {row.get(k, '')}")
        return

    rows = []
    if args.sweep:
        for name, addr, phone, pid, status, site in places_sweep(args.sweep, args.limit):
            print(f"- {name}: {site or 'NO WEBSITE'}")
            row = classify_business(name, site, confirm=args.confirm,
                                    city_hint=args.sweep)
            row.update(address=addr, phone=phone, place_id=pid, business_status=status)
            rows.append(row)
            time.sleep(0.5)   # be polite to the sites we fetch
    elif args.csv:
        with open(args.csv, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            name_col = next((c for c in reader.fieldnames if "name" in c.lower()), None)
            site_col = next((c for c in reader.fieldnames
                             if any(k in c.lower() for k in ("website", "site", "url"))), None)
            if not name_col:
                sys.exit(f"Couldn't find a name column in {reader.fieldnames}")
            for r in reader:
                name = (r.get(name_col) or "").strip()
                site = (r.get(site_col) or "").strip() if site_col else ""
                if not name:
                    continue
                print(f"- {name}: {site or 'NO WEBSITE'}")
                rows.append(classify_business(name, site, confirm=args.confirm))
                time.sleep(0.5)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    n_platform = sum(1 for r in rows if r["platform"] not in ("none", "unknown"))
    n_10a = sum(1 for r in rows if "10a" in r["angle_hint"])
    print(f"\nWrote {len(rows)} rows -> {args.out}")
    print(f"  platform detected: {n_platform} | third-party-only candidates: {n_10a}")
    print("Next: spot-check a few rows by hand, then hand the CSV to the ingest side.")


if __name__ == "__main__":
    main()
