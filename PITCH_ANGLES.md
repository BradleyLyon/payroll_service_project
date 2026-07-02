# PITCH_ANGLES.md
<!-- Purpose: the enrichment brain. Every lead we deliver gets ONE primary angle from this file (plus optional secondaries). Written so both a human and an AI prompt can pick the right angle from detected signals. Update when Simon's feedback kills or promotes an angle. -->

## How to use this file
1. Look at the lead's detected signals (from the bot, detectors, or manual research).
2. Pick the **highest-priority angle whose trigger matches** — that becomes the lead's "one compliance/pain-point flag" and drives the one-line pitch.
3. Note secondary angles in the enrichment row if obvious, but never pitch more than one problem at first contact.
4. Every pitch line must contain a **specific, verifiable observation** about that business. Generic versions of these angles get hung up on.

**Angle priority order (default, pending Simon feedback):**
Timing beats everything → pre-open > ownership change > compliance risk > money-left-on-table > operational duct tape > platform conversion.

---

## TIER 1 — Timing angles (highest close probability)

### 1. Pre-open / nothing configured yet
- **Trigger:** pending SLA liquor license; DOHMH inspection date 1/1/1900; no website; no DoorDash/online ordering presence.
- **Problem:** they haven't picked a POS, processor, payroll, or ordering stack yet — no incumbent to displace.
- **Heartland fix:** full bundle. Simon can get them a website + DoorDash setup as the door-opener, then POS/payments/payroll behind it.
- **Pitch template:** "Saw you're opening at [address] — congrats. Most spots don't have their ordering, site, or payroll set up until after the doors open and it's chaos. Simon can have your website, DoorDash, and payment stack live before day one."
- **Caveats:** verify it's genuinely independent (not a chain/brand-controlled franchise → disqualify per LEAD_SPEC).

### 2. New ownership / leadership change
- **Trigger:** license transfer, LLC change on filing, press coverage, LinkedIn change.
- **Problem:** all vendor contracts are up for review; new owner has no loyalty to the old processor.
- **Heartland fix:** whatever the audit finds — usually payments + POS first.
- **Pitch template:** "New ownership usually inherits the old processor's contract and fees by default — worth a 15-minute review before the renewal locks you in."
- **Caveats:** confirm the change actually happened (filings lag reality both ways).

---

## TIER 2 — Compliance risk angles (NY-specific, strongest for restaurants)

### 3. NY tip & wage compliance
- **Trigger:** tipped-staff restaurant, independent, no evidence of a payroll provider (small headcount, older operation, paper-era vibes). This one is *assumed risk*, not detected — use when no harder signal exists but the business profile fits.
- **Problem:** tip-credit written notice ($50/day penalties up to $5k/yr/employee), 80/20 rule, tip pooling records (6-yr retention, no managers), wage statement violations ($250/day up to $5k/yr/employee). Real settlements run six figures.
- **Heartland fix:** POS tip tracking/payout + Payroll (records, compliant wage statements).
- **Pitch template:** "One disgruntled employee and a paper tip log is a lawsuit. NY tip-credit and wage-statement penalties stack per employee, per day — the POS and payroll handle the records automatically."
- **Caveats:** don't accuse — frame as "most places we talk to didn't know."

### 4. New federal tip reporting (2026 hook — timely, low saturation)
- **Trigger:** any tipped-staff business, especially ones on manual payroll or generic providers.
- **Problem:** the "no tax on tips" deduction (up to $25k/employee) requires employers to report tips with new W-2 codes. Botch it and staff lose the deduction — and blame the owner.
- **Heartland fix:** Payroll+ handles the new W-2 coding.
- **Pitch template:** "Your staff can now deduct up to $25k in tips — but only if your W-2s use the new codes. If payroll's manual or on a generic provider, they may lose it."
- **Caveats:** verify current-year specifics before each batch — rules are new and guidance is evolving. Nobody else is cold-calling on this yet; that's the value.

### 5. NY surcharge signage
- **Trigger:** visible in Google/Yelp photos or on the menu site: "3% card fee added" style signage without the total surcharged price posted.
- **Problem:** NY law requires posting the full surcharged price. Sloppy signage = exposure.
- **Heartland fix:** compliant surcharge / cash-discount program.
- **Pitch template:** "Your card-fee sign at [location] doesn't meet NY's posting rule — easy fix, and Heartland runs the surcharge program compliantly."
- **Caveats:** this is a *verifiable observation* angle — only use when we've actually seen the signage.

### 6. NY weekly pay frequency
- **Trigger:** restaurant/manual-labor business, evidence of biweekly payroll (job postings sometimes say it).
- **Problem:** NY generally requires weekly pay for manual workers; biweekly payroll is an active class-action trend.
- **Heartland fix:** Payroll+ configured for weekly runs.
- **Pitch template:** "If your kitchen staff is paid biweekly, that's the exact fact pattern in a current wave of NY class actions. Weekly payroll setup fixes it."

---

## TIER 3 — Money left on the table

### 7. WOTC (hiring credit forfeiture)
- **Trigger:** business that hires frequently (job postings, high-turnover category) with no ATS evidence.
- **Problem:** restaurants constantly hire WOTC-eligible workers and never claim the federal credit because screening is annoying.
- **Heartland fix:** ATS with automatic WOTC screening.
- **Pitch template:** "You're likely forfeiting a federal tax credit every time you hire. The applicant system screens for it automatically."

### 8. ACA large-employer threshold
- **Trigger:** growing multi-location business plausibly near ~50 FTEs.
- **Problem:** crossing 50 FTEs triggers 1094-C/1095-C reporting most owners don't track.
- **Heartland fix:** Payroll+ ACA reporting tier.
- **Pitch template:** "At your size you may already be an ACA 'large employer' without knowing — the reporting penalty math is ugly and the payroll tier handles it."
- **Caveats:** headcount estimate must be in the enrichment row to use this.

### 9. Certified payroll (construction — non-restaurant track)
- **Trigger:** building permits for public works; construction company signals.
- **Problem:** certified payroll for public contracts is a genuine, hated workflow.
- **Heartland fix:** Payroll+ certified payroll support.
- **Pitch template:** "Public-works certified payroll by hand is why contractors miss bids — the payroll system generates it."

---

## TIER 4 — Operational duct tape (bot-detectable)

### 10. Third-party-only delivery / commission bleed
- **Trigger:** ordering resolves only to DoorDash/UberEats/Grubhub; no direct online ordering.
- **Problem:** paying ~15–30% commission on every order with no owned channel.
- **Heartland fix:** POS with direct online ordering ("own your ordering").
- **Pitch template:** "Every order at [name] goes through DoorDash — that's ~25% off the top. Direct ordering through your own site keeps it."
- **Notes:** this is the strongest *specific verifiable observation* opener we have. Cite the actual platform we saw.

### 11. GoDaddy-hosted site
- **Trigger:** DNS/WHOIS resolves to GoDaddy.
- **Problem/fix:** website + hosting cross-sell (Simon's existing angle).
- **Pitch template:** pair with another angle — hosting alone is weak.
- **Status:** ⚠️ **unvalidated** — Simon hasn't confirmed this signal matters. Treat as secondary-only until he does. <!-- Update after pilot feedback -->

### 12. Cash-only / legacy terminal
- **Trigger:** "cash only" in Google listing/reviews; old countertop terminal visible in photos.
- **Problem:** lost card sales; likely non-EMV → liability shift and PCI exposure.
- **Heartland fix:** whole-stack modernization (payments + POS).
- **Pitch template:** "Cash-only is costing you every customer who doesn't carry it — and old terminals shift fraud liability onto you."

---

## TIER 5 — Competitor conversion batches

### 13. On Toast
- **Trigger:** ordering redirects to order.toasttab.com.
- **Pain to press:** Toast's per-order consumer fees (guests pay it, owners field the complaints); hardware lock-in.
- **Pitch template:** "Your guests pay Toast's order fee on every checkout at [name] — Heartland's ordering doesn't pass a fee to them."

### 14. On Square
- **Trigger:** *.square.site or Square checkout fingerprint.
- **Pain to press:** rate hikes; outgrowing Square's SMB feature set (multi-location, real payroll).
- **Pitch template:** "Square's great until location two. Multi-location reporting, tip payouts, and payroll are where it starts duct-taping."

<!-- Add Clover/Stripe fingerprints + angles when detectors support them. -->

**Batching rule:** conversion leads ship in single-platform batches (all Toast, all Square) so the pitch stays consistent — per Simon's one-platform-at-a-time preference.

---

## ANTI-ANGLES — never lead with these
- **"We'll lower your processing rates."** Most cold-called line in the industry, owners assume hidden fees, and it's not Heartland's strength (add-on fee reputation, $295/location ETF). A rate-shopping lead is a *bad* lead.
- **Generic POS demo offer** with no knowledge of the business.
- **Anything during service hours.** Call window: 2:30–4:30pm, or in-person (our NYC edge).
- Don't cite Heartland's own weak spots unprompted (fees, BBB) — but be ready for the objection: counter with bundling, compliance, US support, breach warranty.

---

## Open questions for Simon
<!-- Move answers into the angles above, then delete -->
- Which of these angles has actually closed for you before? (ranks the tiers with real data)
- Is GoDaddy hosting a real signal or noise? (#11)
- Any angles here you're *not allowed* to pitch (legal/compliance framing restrictions from Heartland)?
- For conversion batches: Toast first or Square first?
