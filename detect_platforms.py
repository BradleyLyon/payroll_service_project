#!/usr/bin/env python3
"""
detect_platforms.py  (v1 scaffold)
----------------------------------
One scan that feeds every batch. For each restaurant it answers:
  - What runs their online ordering? (Toast / Clover / Square / DoorDash
    Storefront / Sauce / marketplace-only / none)     -> PITCH_ANGLES 13/14/10a/10b/15
  - How do they get delivered? Every third-party provider found (DoorDash,
    UberEats, Grubhub/Seamless, Caviar, Postmates, Storefront, Sauce), a
    text-signal check for in-house/direct delivery, or "no delivery found"
    if neither shows up.                               -> the delivery_* columns
  - Who hosts their website?                          -> PITCH_ANGLES 11
  - Marker flags: Owner.com-built site, Resy+OpenTable sprawl,
    "cash only" stated on their own site (negation-aware, and flagged as a
    CONTRADICTION if a payment platform was also detected)
                                                        -> PITCH_ANGLES 15/12

2026-07-09 fixes: an Instagram/Facebook-only "website" from Places is no
longer scanned as if it were a real site (it's a strong 10a signal instead);
every evidence URL is checked for at least one shared word with the business
name and flagged if not (the Apapachó-DC / FUKUROU-Foozo trap); "cash only"
text is ignored if negated nearby ("no longer cash only") and flagged as a
contradiction rather than silently coexisting if a payment platform is also
detected on the same site.

Three ways to run it (pick ONE):

  1) SWEEP a neighborhood (needs GOOGLE_PLACES_API_KEY in .env):
       python3 detect_platforms.py --sweep "restaurants in Bushwick" --limit 20
     Uses Google Places to list restaurants, then classifies each one's website.
     No website found = third-party-only candidate (angle 10a) — the residue.

  2) CLASSIFY a CSV you already have (e.g. the bot's output — free, no key):
       python3 detect_platforms.py --csv enriched.csv
     Needs columns containing a name and a website URL (header names are
     matched loosely: "website", "site", "url" all work).

  3) TEST one website:
       python3 detect_platforms.py --url https://thegrandastoria.com --name "The Grand"
     The --name matters: if the site blocks us (Cloudflare 403 is common), the
     search-index fallback looks the business up by name. Without a name it
     can't, and it'll say so rather than waste a search.

  Sanity check without any network or key at all:
       python3 detect_platforms.py --selftest

Output: a CSV (default detected_YYYY-MM-DD.csv) whose columns line up with
the `enrichments` table in db/schema.sql, so ingesting it is trivial.

Truth policy (same as restaurant_status_bot.py): every value is either backed
by evidence (a URL or record we saw) or labeled unknown. The script never
asserts what it cannot prove. `scan_method` records HOW we learned it:
  direct          = we read the restaurant's own site
  search_fallback = their site blocked us; a search engine had already indexed
                    the ordering page (spot-check these before shipping)
  blocked         = nobody could tell us; a human must look

We do not attempt to bypass bot protection (Cloudflare 403s, challenge pages).
That would breach site terms and undercut the "public information, collected
responsibly" promise this project is built on. Blocked means blocked.

Setup:
  pip install requests        (that's the only dependency)
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

def load_env(path=None):
    """Read a .env file next to this script into os.environ. Stdlib only —
    no python-dotenv needed. Existing environment variables always win.
    Handles: comments, blank lines, `export FOO=bar`, quotes, stray spaces."""
    path = Path(path or Path(__file__).parent / ".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


load_env()

PLACES_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
SERPER_KEY = os.environ.get("SERPER_API_KEY")

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DOH_URL = "https://dns.google/resolve"          # DNS-over-HTTPS (free, keyless)
RDAP_URL = "https://rdap.org/domain/{domain}"    # registrar lookup (free, keyless)
UA = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 12

# --------------------------------------------------------------- fingerprints
# THE TABLE IS DATA — Brad: add rows here, no logic changes needed.
# where: "url"  = pattern tested against every URL found (site address + every
#                 link on the homepage)
#        "html" = pattern tested against the homepage HTML itself
# platform / doordash map straight onto the enrichments columns.
# Source of each row: DATA_SOURCES.md §8 (confirmed in the wild 2026-07-06).
FINGERPRINTS = [
    # 2026-07 widened: was `toasttab.com/local/order`, which missed Burger Queens'
    # real Toast page (`toasttab.com/local/burgerqueens` — no /order/ segment).
    # Caught by validate_detectors.py. Any toasttab.com/local/<slug> is Toast-hosted.
    dict(where="url", pattern=r"order\.toasttab\.com|toasttab\.com/local/",
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
    "cloudflare.com": "cloudflare_proxied",  # real host hidden — treat as unknown
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


# Ordering links usually live one click deep. Try these paths, plus any
# same-domain link whose URL/anchor text mentions order/menu.
ORDER_PATHS = ["/menu", "/menus", "/order", "/order-online", "/online-ordering", "/ordering"]
MAX_SUBPAGES = 4


def candidate_subpages(html, base_url):
    """Same-domain links that look like ordering/menu pages, plus common paths."""
    base = urlparse(base_url)
    root = f"{base.scheme}://{base.netloc}"
    found = []
    for href in re.findall(r'href=["\']([^"\'<>]+)', html, re.I):
        full = href if href.startswith("http") else root + "/" + href.lstrip("/")
        if urlparse(full).netloc != base.netloc:
            continue
        if re.search(r"(order|menu)", urlparse(full).path, re.I):
            found.append(full.split("#")[0])
    found += [root + p for p in ORDER_PATHS]
    seen, out = set(), []
    for u in found:
        if u not in seen and u.rstrip("/") != base_url.rstrip("/"):
            seen.add(u); out.append(u)
    return out[:MAX_SUBPAGES]


BLOCK_MARKERS = re.compile(
    r"(just a moment|checking your browser|enable javascript and cookies|"
    r"cf-browser-verification|attention required!|access denied)", re.I)


def fetch_site(url, debug=False):
    """Fetch a page. Returns (html, final_url, note).

    `note` is '' on a clean fetch, otherwise says WHY the html is untrustworthy:
    an HTTP error, a bot-challenge interstitial, or a JS-only shell. We never
    treat a challenge page as if it were the site (that's how a blocked scan
    masquerades as 'no platform found')."""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as e:
        if debug:
            print(f"    [debug] {url} -> request failed: {type(e).__name__}", file=sys.stderr)
        return "", url, "unreachable"
    html = r.text or ""
    note = ""
    if r.status_code != 200:
        note = f"http_{r.status_code}"
    elif BLOCK_MARKERS.search(html[:4000]):
        note = "bot_challenge"
    elif len(re.sub(r"<[^>]+>", "", html).strip()) < 400 and "<script" in html.lower():
        note = "js_rendered_shell"   # content is drawn by JavaScript; a plain fetch can't see it
    if debug:
        n_links = len(set(re.findall(r'https?://[^\s"\'<>)]+', html)))
        print(f"    [debug] {url} -> HTTP {r.status_code}, {len(html)} bytes, "
              f"{n_links} links, note={note or 'clean'}", file=sys.stderr)
        if "toasttab" in html.lower():
            print("    [debug] !! 'toasttab' IS present in this page's html", file=sys.stderr)
    return html, r.url, note


def check_hosting(website):
    """Nameservers via DNS-over-HTTPS + registrar via RDAP. Both free/keyless.
    Returns (hosting_label, registrar, evidence_string).

    Note: these are two DIFFERENT facts and we keep them apart.
      - hosting  = who runs the DNS/site (the cross-sell signal, angle 11)
      - registrar = where the domain was bought (weaker; often GoDaddy even
        when someone else hosts)
    Cloudflare nameservers proxy the real host, so hosting reads
    'cloudflare_proxied' — that is an honest 'unknown host', not a finding."""
    if not website:
        return "unknown", "", ""
    domain = urlparse(website if website.startswith("http") else "https://" + website).netloc
    domain = domain.removeprefix("www.")
    if not domain:
        return "unknown", "", ""
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
    evidence = f"NS={','.join(ns_names[:3]) or '?'}; registrar={registrar or '?'}"
    return label, registrar, evidence


# --------------------------------------------------------------- delivery detection
# Separate from the FINGERPRINTS table above on purpose: FINGERPRINTS answers
# "what system runs their ordering" (one primary platform, drives the pitch
# angle); this answers "who actually delivers for them" (can be several
# providers at once — useful on its own, regardless of angle).

# Patterns must match a STORE/RESTAURANT page — not a homepage, neighborhood
# directory, or blog post. Without the trailing path requirement, a link to
# "postmates.com/neighborhood/whitestone-queens" counts as a delivery
# provider. That happened on the 2026-07-09 Bushwick sweep (Otis).
#
# Postmates: absorbed into Uber Eats, standalone app retired. postmates.com
# /store/* now serves Uber Eats' catalog on a legacy domain. It is NOT an
# independent provider, so it maps to ubereats. Counting it separately
# inflated 8 of 20 rows on the first sweep.
DELIVERY_PROVIDER_PATTERNS = {
    "doordash_marketplace": r"doordash\.com/store/",
    "doordash_storefront":  r"order\.online/store/",
    "ubereats":              r"(ubereats\.com/store/|postmates\.com/store/)",
    "grubhub_seamless":      r"(grubhub|seamless)\.com/restaurant/",
    "caviar":                r"trycaviar\.com/store/",
    "sauce":                 r"getsauce\.com/order/",
    "chownow":               r"chownow\.com/order/",
}

# Weak, text-only evidence that they deliver themselves — a mention, not a
# proof. Reported separately from a confirmed provider, never merged into it.
DIRECT_DELIVERY_SIGNAL = re.compile(
    r"(free delivery|local delivery|we deliver|delivery available|"
    r"delivery zone|delivery radius|delivery fee|order.{0,15}delivery)", re.I)

# The honest "no delivery" case — they say so themselves.
NO_DELIVERY_SIGNAL = re.compile(
    r"(pickup only|takeout only|no delivery|dine.?in only|we do not deliver)", re.I)


def scan_delivery_links(urls, name=None):
    """Every delivery provider linked from the business's own pages.
    Returns {provider: evidence_url}.

    If `name` is given, an evidence URL that shares no significant word with
    the business name is discarded — it belongs to someone else. Same guard
    as evidence_mismatch(), applied to delivery links. (Otis, 2026-07-09:
    a postmates.com Whitestone-Queens *neighborhood* page was being counted
    as Otis's delivery provider.)"""
    found = {}
    for prov, pat in DELIVERY_PROVIDER_PATTERNS.items():
        for u in urls:
            if not re.search(pat, u, re.I):
                continue
            if name and evidence_mismatch(name, u):
                continue        # wrong entity — not this restaurant's listing
            found[prov] = u
            break
    return found


def search_delivery_providers(name, city_hint):
    """One search-index query covering every provider at once. Catches
    listings a restaurant doesn't link from its own site — the common case,
    since most restaurants don't advertise DoorDash on their homepage."""
    if not SERPER_KEY or not name or name.startswith("("):
        return {}
    q = (f'"{name}" {city_hint} '
         '(doordash OR ubereats OR grubhub OR seamless OR caviar OR "order.online")')
    try:
        r = requests.post("https://google.serper.dev/search",
                          headers={"X-API-KEY": SERPER_KEY},
                          json={"q": q}, timeout=TIMEOUT)
        urls = [i.get("link", "") for i in r.json().get("organic", [])]
    except (requests.RequestException, ValueError):
        return {}
    return scan_delivery_links(urls, name=name)


# White-label providers are ALSO ordering platforms: if delivery finds one,
# the platform column must agree. (Carmenta's: delivery said DoorDash
# Storefront while platform said 'none' — the columns contradicted.)
WHITE_LABEL_PLATFORMS = {"doordash_storefront": "10b", "sauce": "10b", "chownow": "other"}


def delivery_status_label(providers, direct_signal, none_signal, searched=False):
    """`searched` = we actually queried the search index for listings. It
    separates 'we looked and found nothing' (evidence of absence, weak but
    real) from 'we never looked' (no information at all). Conflating those
    is how a lead list fills up with phantom no-delivery restaurants."""
    only_white_label = providers and all(p in WHITE_LABEL_PLATFORMS for p in providers)
    if providers and direct_signal and not only_white_label:
        return "direct_and_third_party"
    if providers and direct_signal and only_white_label:
        # "We deliver!" next to a DoorDash Storefront usually means DoorDash's
        # drivers deliver. Don't credit them with in-house delivery.
        return "third_party_only (site claims direct — white-label handles it)"
    if providers:
        return "third_party_only"              # the population 10a/10b batches want
    if direct_signal:
        return "direct_mentioned_unverified"    # text says so; nobody's confirmed it
    if none_signal:
        return "no_delivery_stated"             # they say pickup/dine-in only
    return "no_delivery_found (searched)" if searched else "unknown (not searched)"


def check_delivery(name, html, urls, city_hint, confirm):
    """Answers 'who delivers for this business, and how' — independent of
    which ordering *system* they run. Returns (providers_dict, status_label,
    evidence_string)."""
    providers = scan_delivery_links(urls, name=name)
    searched = False
    if confirm:
        searched = True
        for prov, u in search_delivery_providers(name, city_hint).items():
            providers.setdefault(prov, u)
    direct_signal = bool(html and DIRECT_DELIVERY_SIGNAL.search(html))
    none_signal = bool(html and NO_DELIVERY_SIGNAL.search(html))
    status = delivery_status_label(providers, direct_signal, none_signal, searched)
    evidence = "; ".join(f"{k}:{v}" for k, v in providers.items())
    return providers, status, evidence


# --------------------------------------------------------------- entity sanity

# A "website" that's actually just a social profile isn't an owned channel —
# treat it the same as no website (strong 10a signal), and never try to crawl
# it for ordering-platform fingerprints (an Instagram page isn't the site).
SOCIAL_ONLY = re.compile(
    r"(instagram\.com|facebook\.com|linktr\.ee|linktree\.com|"
    r"tiktok\.com|threads\.net|m\.me/)", re.I)

_STOP_WORDS = {"the", "and", "of", "restaurant", "cafe", "bar", "grill",
              "kitchen", "nyc", "brooklyn", "queens", "manhattan", "bronx",
              "llc", "inc", "co"}


def name_tokens(name):
    """Significant words from a business name, for evidence-URL sanity checks."""
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    return {w for w in words if len(w) >= 4 and w not in _STOP_WORDS}


def evidence_mismatch(name, evidence_url):
    """True if the evidence URL shares NO significant word with the business
    name — the Apapachó-DC / FUKUROU→Foozo trap from the Bushwick sweep. This
    doesn't prove a mismatch, it only flags a suspicious one for a human to
    check before the lead ships."""
    if not evidence_url:
        return False
    toks = name_tokens(name)
    if not toks:
        return False
    ev = evidence_url.lower()
    return not any(t in ev for t in toks)


def classify_business(name, website, confirm=False, city_hint="NYC", debug=False):
    """The core routine: one business in, one enrichments-shaped dict out."""
    row = dict(name=name, website=website or "", website_status="none",
               platform="none", ordering_evidence="", ordering_evidence_page="",
               delivery_providers="", delivery_status="unknown", delivery_evidence="",
               hosting="unknown", registrar="", hosting_evidence="",
               markers="", angle_hint="", scan_method="direct",
               checked_at=dt.date.today().isoformat())

    has_owned_site = bool(website) and not SOCIAL_ONLY.search(website)

    if not has_owned_site:
        # No website, OR the "website" Places gave us is just a social
        # profile (Instagram/Facebook/Linktree) — neither is an owned
        # ordering channel. Both are strong 10a signals.
        row["platform"] = "none"
        if website:
            row["website_status"] = "social_only (not an owned site)"
            row["angle_hint"] = "10a candidate (social-only presence, no owned site)"
        else:
            row["angle_hint"] = "10a candidate (no website found)"
        providers, status, evidence = check_delivery(name, "", [], city_hint, confirm)
        row["delivery_providers"] = "; ".join(sorted(providers))
        row["delivery_status"] = status
        row["delivery_evidence"] = evidence
        # A white-label found here IS their ordering system, site or not.
        for prov, angle in WHITE_LABEL_PLATFORMS.items():
            if prov in providers:
                row["platform"] = prov
                row["ordering_evidence"] = providers[prov]
                row["angle_hint"] = f"{angle} (white-label ordering, no owned site)"
                break
        if providers:
            row["angle_hint"] = ("10a CONFIRMED (no owned site; delivery via "
                                 + ", ".join(sorted(providers)) + ")")
        return row

    html, final_url, note = fetch_site(website, debug=debug)
    if note in ("bot_challenge", "js_rendered_shell"):
        row["website_status"] = f"BLOCKED:{note} — scan unreliable, verify by hand"
    elif note:
        row["website_status"] = f"error:{note} — verify by hand"
    else:
        row["website_status"] = "live" if html else "unreachable (verify by hand)"
    urls = extract_links(html, final_url) if html else [website]
    all_html = html

    # Ordering links are usually on /menu or /order, not the homepage.
    # Only bother crawling if the homepage showed no real platform.
    if html and not classify_urls(urls):
        for sub in candidate_subpages(html, final_url):
            time.sleep(0.4)
            sub_html, sub_final, sub_note = fetch_site(sub, debug=debug)
            if not sub_html or sub_note in ("http_404", "bot_challenge"):
                continue
            urls += extract_links(sub_html, sub_final)
            all_html += "\n" + sub_html
            if classify_urls(urls):
                row["ordering_evidence_page"] = sub_final
                break

    hits = classify_urls(urls) + (classify_html(all_html) if all_html else [])

    platforms = [h for h in hits if not h["platform"].startswith(("marker:", "marketplace:"))]
    markers   = [h for h in hits if h["platform"].startswith("marker:")]

    if platforms:
        row["platform"] = platforms[0]["platform"]
        row["ordering_evidence"] = platforms[0]["evidence"]
        row["angle_hint"] = platforms[0]["angle"]
        if len(platforms) > 1:   # two real platforms at once -> fragmented stack
            row["angle_hint"] = "15 (fragmented: " + "+".join(p["platform"] for p in platforms) + ")"

    # cash-only marker: skip if negated nearby ("no longer cash only", "now
    # accepts cards"), and flag as a CONTRADICTION rather than silently
    # coexisting if we also detected a real payment platform (Tabaré case:
    # 'cash only' text + a live Square site — one of those is stale or the
    # phrase means something narrower; a human needs to look, not us).
    cash_hit = any(m["platform"] == "marker:cash_only" for m in markers)
    if cash_hit and all_html:
        for m in re.finditer(r"cash\s*only", all_html, re.I):
            window = all_html[max(0, m.start() - 50):m.start()].lower()
            if re.search(r"(no longer|not\b|used to be|isn.?t|accepts? card|now accept)", window):
                cash_hit = False
                break
    marker_names = [m["platform"].split(":", 1)[1] for m in markers
                    if m["platform"] != "marker:cash_only"]
    if cash_hit:
        if row["platform"] in ("square", "toast", "clover"):
            marker_names.append(f"cash_only ⚠CONTRADICTS detected platform "
                                f"'{row['platform']}' — verify by hand")
        else:
            marker_names.append("cash_only")
            if not row["angle_hint"]:
                row["angle_hint"] = "12 (cash only on own site)"
    row["markers"] = "; ".join(marker_names)

    # Entity sanity check: does the evidence URL actually mention this
    # business? (Apapachó-DC, FUKUROU->Foozo — both from real sessions.)
    if row["ordering_evidence"] and evidence_mismatch(name, row["ordering_evidence"]):
        row["angle_hint"] = (row["angle_hint"] + " ⚠VERIFY ENTITY — evidence URL "
                             "doesn't share a word with the business name").strip()

    if row["website_status"].startswith(("BLOCKED", "error")) and row["platform"] == "none":
        hit = search_fingerprint(name, city_hint) if SERPER_KEY else None
        if hit:
            row["platform"] = hit["platform"]
            row["ordering_evidence"] = hit["evidence"]
            row["ordering_evidence_page"] = "via search index (site blocked direct fetch)"
            row["angle_hint"] = hit["angle"] + " (search-index evidence — spot-check the URL)"
            row["scan_method"] = "search_fallback"
        else:
            row["platform"] = "unknown"
            row["scan_method"] = "blocked"
            row["angle_hint"] = ("MANUAL CHECK — site blocked the scan"
                                 + ("" if SERPER_KEY else "; no SERPER_API_KEY set for search fallback"))
    providers, status, evidence = check_delivery(name, all_html, urls, city_hint, confirm)
    row["delivery_providers"] = "; ".join(sorted(providers))
    row["delivery_status"] = status
    row["delivery_evidence"] = evidence

    # --- let the delivery findings inform platform + angle -----------------
    # (a) A white-label provider IS an ordering platform. If the platform scan
    #     missed it (their site doesn't link it, but the search index knows),
    #     promote it rather than leaving the columns contradicting each other.
    if row["platform"] == "none":
        for prov, angle in WHITE_LABEL_PLATFORMS.items():
            if prov in providers:
                row["platform"] = prov
                row["ordering_evidence"] = providers[prov]
                row["ordering_evidence_page"] = "via delivery scan"
                row["angle_hint"] = f"{angle} (white-label ordering found via delivery scan)"
                break

    # (b) Marketplace delivery + no owned ordering platform = angle 10a.
    #     This is the whole 10a batch and it was previously being dropped:
    #     the delivery scan found these leads, the angle logic ignored them.
    if row["platform"] == "none" and status.startswith("third_party_only"):
        row["angle_hint"] = ("10a (marketplace delivery only, no owned ordering platform): "
                             + ", ".join(sorted(providers)))

    row["hosting"], row["registrar"], row["hosting_evidence"] = check_hosting(final_url or website)
    if "godaddy" in (row["hosting"] + row["registrar"]).lower():
        row["markers"] = (row["markers"] + "; godaddy_touch").strip("; ")
    return row


def search_fingerprint(name, city_hint):
    """When a site blocks us (Cloudflare 403, etc.), ask the public search index
    instead of trying to force the door. Search engines have already crawled the
    ordering pages we care about.

    Returns a fingerprint hit dict, or None. Costs one Serper search.
    We do NOT attempt to bypass bot protection — that's a ToS problem and a
    'public information, collected responsibly' problem."""
    if not SERPER_KEY:
        return None
    if not name or name.startswith("("):     # placeholder from --url with no --name
        print("    [note] no business name given — skipping search fallback "
              "(re-run with --name \"The Grand\")", file=sys.stderr)
        return None
    q = (f'"{name}" {city_hint} '
         '(toasttab OR "clover.com/online-ordering" OR square.site OR '
         '"order.online" OR getsauce OR doordash OR grubhub)')
    try:
        r = requests.post("https://google.serper.dev/search",
                          headers={"X-API-KEY": SERPER_KEY},
                          json={"q": q}, timeout=TIMEOUT)
        urls = [i.get("link", "") for i in r.json().get("organic", [])]
    except (requests.RequestException, ValueError):
        return None
    hits = classify_urls(urls)
    # Prefer a real platform over a marketplace listing.
    for h in hits:
        if not h["platform"].startswith("marketplace:"):
            return h
    return hits[0] if hits else None



# --------------------------------------------------------------- places sweep

def places_sweep(query, limit):
    """Text-search a neighborhood. Returns [(name, address, phone, place_id,
    business_status, website), ...]. Announces every paid request."""
    if not PLACES_KEY:
        env_path = Path(__file__).parent / ".env"
        sys.exit(
            "No GOOGLE_PLACES_API_KEY found.\n"
            f"  Looked for a .env file at: {env_path}\n"
            f"  That file exists: {env_path.exists()}\n"
            "  Expected a line exactly like:  GOOGLE_PLACES_API_KEY=AIza...\n"
            "  (no quotes, no spaces around the =)\n"
            "  You can also set it just for this run:\n"
            "    export GOOGLE_PLACES_API_KEY=your_key_here"
        )
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

    # --- 2026-07-09 bug-fix checks ---
    checks = []

    # Social-only "website" must not be treated as an owned site.
    checks.append(("social-only detected",
                   bool(SOCIAL_ONLY.search("https://www.instagram.com/tora_nyc"))))
    checks.append(("real site not flagged social",
                   not SOCIAL_ONLY.search("https://thegrandastoria.com")))

    # Evidence/name mismatch: FUKUROU vs. a Foozo evidence URL should flag;
    # a real match should not.
    checks.append(("mismatch flags wrong entity",
                   evidence_mismatch("FUKUROU BROOKLYN",
                                     "https://www.getsauce.com/order/foozo-artisan-ramen")))
    checks.append(("match does not false-flag",
                   not evidence_mismatch("Choice Market",
                                         "https://order.toasttab.com/online/choicebrooklyn")))

    # Delivery provider scan: multiple providers found from links.
    provs = scan_delivery_links([
        "https://www.doordash.com/store/some-place-123",
        "https://www.ubereats.com/store/some-place",
        "https://instagram.com/some_place",
    ])
    checks.append(("delivery scan finds 2 providers", set(provs) == {"doordash_marketplace", "ubereats"}))

    # Direct-delivery text signal vs. explicit no-delivery signal.
    checks.append(("direct-delivery text detected",
                   bool(DIRECT_DELIVERY_SIGNAL.search("Free delivery within 2 miles!"))))
    checks.append(("no-delivery text detected",
                   bool(NO_DELIVERY_SIGNAL.search("We are pickup only, no delivery."))))
    checks.append(("delivery_status label: third_party_only",
                   delivery_status_label({"doordash_marketplace": "x"}, False, False) == "third_party_only"))
    checks.append(("delivery_status label: no_delivery_stated",
                   delivery_status_label({}, False, True) == "no_delivery_stated"))
    checks.append(("searched-but-empty != unknown",
                   delivery_status_label({}, False, False, searched=True).startswith("no_delivery_found")
                   and delivery_status_label({}, False, False, searched=False).startswith("unknown")))
    checks.append(("white-label + 'we deliver' is not credited as direct",
                   delivery_status_label({"doordash_storefront": "x"}, True, False).startswith("third_party_only")))
    checks.append(("real direct + marketplace = direct_and_third_party",
                   delivery_status_label({"grubhub_seamless": "x"}, True, False) == "direct_and_third_party"))

    for label, passed in checks:
        print(f"  {'PASS' if passed else 'FAIL'}  {label}")
        ok = ok and passed

    print("SELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


# --------------------------------------------------------------- main

OUT_COLS = ["name", "address", "phone", "place_id", "business_status",
            "website", "website_status", "platform", "ordering_evidence",
            "ordering_evidence_page",
            "delivery_providers", "delivery_status", "delivery_evidence",
            "hosting", "registrar", "hosting_evidence", "markers",
            "angle_hint", "scan_method", "checked_at"]
# NOTE for Brad / DB ingest: the old single "doordash" column (unknown/listed/
# third_party_only) is gone — replaced by three richer columns:
#   delivery_providers = every provider found, semicolon-separated
#                         (doordash_marketplace, doordash_storefront, ubereats,
#                          grubhub_seamless, caviar, postmates, sauce, chownow)
#   delivery_status     = third_party_only / direct_and_third_party /
#                         direct_mentioned_unverified / no_delivery_stated / unknown
#   delivery_evidence   = "provider:url" pairs backing delivery_providers

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
    ap.add_argument("--debug", action="store_true",
                    help="show every page fetched: HTTP status, size, link count, blocked/clean")
    ap.add_argument("--name", help='business name, used with --url so the search fallback works: --name "The Grand"')
    ap.add_argument("--city", default="NYC", help="location hint for the search fallback (default: NYC)")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if args.url:
        row = classify_business(name=args.name or "(single-url test)", website=args.url,
                                confirm=True, city_hint=args.city, debug=args.debug)
        for k in OUT_COLS:
            print(f"{k:20s} {row.get(k, '')}")
        return

    rows = []
    if args.sweep:
        for name, addr, phone, pid, status, site in places_sweep(args.sweep, args.limit):
            print(f"- {name}: {site or 'NO WEBSITE'}")
            # A street address is a far better search hint than "restaurants in Bushwick".
            hint = " ".join(addr.split(",")[1:3]).strip() or args.city
            row = classify_business(name, site, confirm=args.confirm,
                                    city_hint=hint, debug=args.debug)
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
                rows.append(classify_business(name, site, confirm=args.confirm,
                                              city_hint=args.city, debug=args.debug))
                time.sleep(0.5)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    n_platform = sum(1 for r in rows if r["platform"] not in ("none", "unknown"))
    n_10a = sum(1 for r in rows if r["angle_hint"].startswith("10a"))
    n_blocked = sum(1 for r in rows if r.get("scan_method") == "blocked")
    n_fallback = sum(1 for r in rows if r.get("scan_method") == "search_fallback")
    n_social = sum(1 for r in rows if "social_only" in r.get("website_status", ""))
    n_mismatch = sum(1 for r in rows if "VERIFY ENTITY" in r.get("angle_hint", ""))
    n_contra = sum(1 for r in rows if "CONTRADICTS" in r.get("markers", ""))
    from collections import Counter
    delivery_counts = Counter(r["delivery_status"] for r in rows)
    print(f"\nWrote {len(rows)} rows -> {args.out}")
    print(f"  platform detected: {n_platform} | third-party-only candidates: {n_10a}")
    print(f"  sites that blocked the scan: {n_blocked} | rescued via search index: {n_fallback}")
    if n_blocked and not SERPER_KEY:
        print("  (set SERPER_API_KEY in .env to recover blocked sites via search)")
    print("  delivery: " + " | ".join(f"{v} {k}" for k, v in delivery_counts.most_common()))
    if n_social:
        print(f"  social-only 'website' (Instagram/FB, not owned — 10a signal): {n_social}")
    if n_mismatch:
        print(f"  ⚠ evidence/name mismatches to verify by hand: {n_mismatch}")
    if n_contra:
        print(f"  ⚠ cash-only vs. detected-platform contradictions to verify: {n_contra}")
    print("Next: spot-check a few rows by hand, then hand the CSV to the ingest side.")


if __name__ == "__main__":
    main()
