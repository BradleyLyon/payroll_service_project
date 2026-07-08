# PITCH_ANGLES.md
<!-- Purpose: the enrichment brain. Every lead we deliver gets ONE primary angle from this file (plus optional secondaries). Written so both a human and an AI prompt can pick the right angle from detected signals. Update when Simon's feedback kills or promotes an angle. -->
<!-- Updated 2026-07-06 from manual bot session: split #10 into 10a/10b, added #15 fragmented stack, added institution-holdout profile to #12, added hotel auto-DQ, new Simon questions. -->

## How to use this file
1. Look at the lead's detected signals (from the bot, detectors, or manual research).
2. Pick the **highest-priority angle whose trigger matches** — that becomes the lead's "one compliance/pain-point flag" and drives the one-line pitch.
3. Note secondary angles in the enrichment row if obvious, but never pitch more than one problem at first contact.
4. Every pitch line must contain a **specific, verifiable observation** about that business. Generic versions of these angles get hung up on.
5. **Angle co-occurrence is a super-signal.** When two angles are simultaneously true (e.g. paying for Toast POS *and* bleeding marketplace commissions — a stack contradiction), the lead is stronger than either angle alone: the owner already bought a fix and isn't using it. Flag stack contradictions explicitly in the enrichment row.
6. **Timing stacks with everything.** A recent capital event (new location, expansion, build-out) layered on any base angle bumps the lead's rank — the owner is already in decision mode.

**Angle priority order (default, pending Simon feedback):**
Timing beats everything → pre-open > ownership change > compliance risk > money-left-on-table > operational duct tape > platform conversion.

---

## TIER 1 — Timing angles (highest close probability)

### 1. Pre-open / nothing configured yet
- **Trigger:** pending SLA liquor license; DOHMH inspection date 1/1/1900; no website; no DoorDash/online ordering presence. Also matches *just-opened* spots (weeks old) with no stack detected — signal decays fast, verify freshness.
- **Problem:** they haven't picked a POS, processor, payroll, or ordering stack yet — no incumbent to displace.
- **Heartland fix:** full bundle. Simon can get them a website + DoorDash setup as the door-opener, then POS/payments/payroll behind it.
- **Pitch template:** "Saw you're opening at [address] — congrats. Most spots don't have their ordering, site, or payroll set up until after the doors open and it's chaos. Simon can have your website, DoorDash, and payment stack live before day one."
- **Caveats:** verify it's genuinely independent (not a chain/brand-controlled franchise → disqualify per LEAD_SPEC). **Hotel-address auto-DQ:** a restaurant inside a hotel is enterprise-controlled (POS/payments/payroll decided by the hotel group) unless verified as an independent tenant. **Bonus signal:** owner operates other venues → one relationship, multiple accounts.

### 2. New ownership / leadership change
- **Trigger:** license transfer, LLC change on filing, press coverage, LinkedIn change.
- **Problem:** all vendor contracts are up for review; new owner has no loyalty to the old processor.
- **Heartland fix:** whatever the audit finds — usually payments + POS first.
- **Pitch template:** "New ownership usually inherits the old processor's contract and fees by default — worth a 15-minute review before the renewal locks you in."
- **Caveats:** confirm the change actually happened (filings lag reality both ways).

---

## TIER 2 — Compliance risk angles (NY-specific, strongest for restaurants)

### 3. NY tip & wage compliance
- **Trigger:** tipped-staff restaurant, independent, no evidence of a payroll provider (small headcount, older operation, paper-era vibes). This one is *assumed risk*, not detected — use when no harder signal exists but the business profile fits. Cash-only operations (see #12) fit this profile almost by definition.
- **Problem:** tip-credit written notice ($50/day penalties up to $5k/yr/employee), 80/20 rule, tip pooling records (6-yr retention, no managers), wage statement violations ($250/day up to $5k/yr/employee). Real settlements run six figures.
- **Heartland fix:** POS tip tracking/payout + Payroll (records, compliant wage statements).
- **Pitch template:** "One disgruntled employee and a paper tip log is a lawsuit. NY tip-credit and wage-statement penalties stack per employee, per day — the POS and payroll handle the records automatically."
- **Caveats:** don't accuse — frame as "most places we talk to didn't know."
- **Banquet/catering variant (⚠️ unvalidated):** NY treats mandatory service charges as gratuities unless clearly disclosed otherwise — banquet-heavy restaurants (detectable via catering pages) are a distinct sub-profile where this may beat the platform angle. <!-- ASK SIMON: pitchable or too accusatory? F&J Pine is the test case. -->

### 4. New federal tip reporting (2026 hook — timely, low saturation)
- **Trigger:** any tipped-staff business, especially ones on manual payroll or generic providers.
- **Problem:** the "no tax on tips" deduction (up to $25k/employee) requires employers to report tips with new W-2 codes. Botch it and staff lose the deduction — and blame the owner.
- **Heartland fix:** Payroll+ handles the new W-2 coding.
- **Pitch template:** "Your staff can now deduct up to $25k in tips — but only if your W-2s use the new codes. If payroll's manual or on a generic provider, they may lose it."
- **Caveats:** verify current-year specifics before each batch — rules are new and guidance is evolving. Nobody else is cold-calling on this yet; that's the value. Hits hardest on **cash-tip environments** (#12 leads) where reporting is most likely botched.

### 5. NY surcharge signage
- **Trigger:** visible in Google/Yelp photos or on the menu site: "3% card fee added" style signage without the total surcharged price posted. **Also detectable on Toast/Clover ordering pages** — surcharge disclosures appear in the checkout config (e.g. The Grand's 3% disclosure on its Toast page).
- **Problem:** NY law requires posting the full surcharged price. Sloppy signage = exposure.
- **Heartland fix:** compliant surcharge / cash-discount program.
- **Pitch template:** "Your card-fee sign at [location] doesn't meet NY's posting rule — easy fix, and Heartland runs the surcharge program compliantly."
- **Caveats:** this is a *verifiable observation* angle — only use when we've actually seen the signage. **Bonus read:** an active surcharge means processing cost is a felt pain right now — pair with #13/#14 for a receptive owner, but keep the framing on guest-facing fees and compliance, never rate-shopping.

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

### 10a. Third-party-only delivery / commission bleed
- **Trigger:** ordering resolves only to DoorDash/UberEats/Grubhub marketplaces; no direct online ordering; typically no website or website = marketplace URL.
- **Problem:** paying ~15–30% commission on every order with no owned channel.
- **Heartland fix:** POS with direct online ordering ("own your ordering").
- **Pitch template:** "Every order at [name] goes through DoorDash — that's ~25% off the top. Direct ordering through your own site keeps it."
- **Notes:** this is the strongest *specific verifiable observation* opener we have. Cite the actual platform we saw.
- **⚠️ Sourcing note (2026-07-06):** this population is **search-resistant** — spots findable by web search have overwhelmingly adopted direct ordering; genuinely third-party-only spots have no indexable footprint. **Bot-only angle:** pull marketplace listings per neighborhood → Google Places per name → filter to `website: none / marketplace URL`. Do not hand-hunt this one.

### 10b. White-label-dependent ordering (NEW — split from #10)
- **Trigger:** the business's "direct" ordering runs on a platform-owned white-label: `order.online` (= **DoorDash Storefront**), `getsauce.com` (= Sauce), or similar — often alongside active marketplace listings.
- **Problem:** the owned channel isn't owned — payments, customer data, and menus live inside DoorDash's (or another platform's) ecosystem, marketplace listings still bleed commission, and marketplace menus are often marked up above house prices (customers visibly pay more).
- **Heartland fix:** genuinely owned direct ordering via Heartland POS.
- **Pitch template:** "Your 'direct' ordering is DoorDash Storefront — everything still runs through their system, and the marketplace listings take up to 30% while charging your customers more than your menu prices. Direct ordering through your own stack keeps the margin and the customer data."
- **Notes:** highly searchable (the white-label URLs are indexable), so this variant CAN be hand-hunted. Examples from 2026-07-06 batch: Lincoln Station, Burger Queens.

### 11. GoDaddy-hosted site
- **Trigger:** DNS/WHOIS resolves to GoDaddy.
- **Problem/fix:** website + hosting cross-sell (Simon's existing angle).
- **Pitch template:** pair with another angle — hosting alone is weak.
- **Status:** ⚠️ **unvalidated** — Simon hasn't confirmed this signal matters. Treat as secondary-only until he does. <!-- Update after pilot feedback -->

### 12. Cash-only / legacy terminal
- **Trigger:** "cash only" in Google listing/reviews; old countertop terminal visible in photos; stated on the business's own site/menu.
- **Problem:** lost card sales; likely non-EMV → liability shift and PCI exposure; and under NY's new payment law (GBL § 396-ii, eff. March 2026) the tide is all toward card acceptance (cashless is now banned; cash-only is legal but increasingly anachronistic).
- **Heartland fix:** whole-stack modernization (payments + POS + payroll).
- **Pitch template:** "Cash-only is costing you every customer who doesn't carry it — and old terminals shift fraud liability onto you."
- **Strongest framing found (2026-07-06): "you're already paying someone else to take cards."** Many cash-only spots list on Grubhub/Seamless for delivery — meaning the only card payments they accept are the ones a marketplace processes at commission (Tom's). Others outsource card acceptance to the corner ATM's fees (J.G. Melon). Cite the specific mechanism.
- **⚠️ Sub-profile — institution holdout:** decades of deliberate cash-only (est.-1930s/40s/70s landmarks) = **low conversion probability, high payroll value.** Label these honestly in the batch. The exception that converts: **holdout + recent capital event** (Wo Hop: first expansion in 87 years) — an owner in modernization mode. Without a modernization signal, rank these below signal-fresh leads. <!-- ASK SIMON: are pure holdouts worth calls at all? -->
- **Verification rule:** cash-only status MUST be confirmed by a primary source dated within 12 months. Yelp's cash-only category and old reviews are full of stale false positives (John's of Bleecker took cards in **2016** and still appears cash-only in crowd signals).

### 15. Fragmented multi-platform stack (NEW)
- **Trigger:** multiple locations (or functions) on *different* systems — e.g. Toast at one location + Clover at another + a separate white-label ordering site (Nippon Cha); or POS + two reservation platforms simultaneously (F&J Pine on Toast + Resy + OpenTable); or a paid POS whose built-in ordering sits unused while marketplaces bleed commission (Burger Queens — a **stack contradiction**).
- **Problem:** duplicated fees, split reporting, per-system menu maintenance, no unified customer data — and it compounds with every location added.
- **Heartland fix:** the bundle IS the pitch — one system for ordering, POS, payments, payroll across all locations.
- **Pitch template:** "Your [N] locations run [N] different systems — [name them]. Every one has its own fees, reporting, and menus to maintain. Heartland consolidates ordering, POS, and payroll under one system."
- **Notes:** fully bot-detectable (fingerprint per location, diff the results). Arguably a stronger opener than single-platform conversion because the observation is undeniable and the fix is exactly Heartland's differentiator. <!-- ASK SIMON: does consolidation fly as its own batch, or fold these into the dominant platform's batch? -->

---

## TIER 5 — Competitor conversion batches

### 13. On Toast
- **Trigger:** ordering redirects to order.toasttab.com.
- **Pain to press:** Toast's per-order consumer fees (guests pay it, owners field the complaints); hardware lock-in.
- **Pitch template:** "Your guests pay Toast's order fee on every checkout at [name] — Heartland's ordering doesn't pass a fee to them."
- **Detector note:** Toast ordering pages leak enrichment — surcharge disclosures, gift card programs, delivery config. Scrape the page, don't just fingerprint the URL.

### 14. On Square
- **Trigger:** *.square.site or Square checkout fingerprint.
- **Pain to press:** rate hikes; outgrowing Square's SMB feature set (multi-location, real payroll).
- **Pitch template:** "Square's great until location two. Multi-location reporting, tip payouts, and payroll are where it starts duct-taping."

<!-- Add Clover (clover.com/online-ordering/*) + Stripe fingerprints + angles when detectors support them. Clover fingerprint confirmed in the wild 2026-07-06 (Nippon Cha Williamsburg). -->

**Batching rule:** conversion leads ship in single-platform batches (all Toast, all Square) so the pitch stays consistent — per Simon's one-platform-at-a-time preference. Fragmented-stack (#15) leads pend Simon's answer on whether they ship as their own batch.

---

## ANTI-ANGLES — never lead with these
- **"We'll lower your processing rates."** Most cold-called line in the industry, owners assume hidden fees, and it's not Heartland's strength (add-on fee reputation, $295/location ETF). A rate-shopping lead is a *bad* lead. (Surcharging owners — #5 — are the tempting case: they feel processing costs. Still frame as guest-facing fees + compliance, never rates.)
- **Generic POS demo offer** with no knowledge of the business.
- **Anything during service hours.** Call window: 2:30–4:30pm, or in-person (our NYC edge).
- Don't cite Heartland's own weak spots unprompted (fees, BBB) — but be ready for the objection: counter with bundling, compliance, US support, breach warranty.

## HARD DISQUALIFIERS (mirror of LEAD_SPEC — check before any angle)
- Large corporate chains; brand-controlled franchises (verify which services are franchise-controlled).
- **Hotel-based restaurants** — auto-DQ unless verified as an independently operated tenant (hotel groups control F&B vendor decisions; e.g. a Standard/Hyatt property restaurant).
- **Entity-resolution failure** — if name+address+entity can't be matched cleanly (same-name businesses under different owners: the Apapacho-DC / Wo-Hop-Next-Door / Peppa's pattern), the lead is *parked*, not shipped.

---

## Open questions for Simon
<!-- Move answers into the angles above, then delete -->
- Which of these angles has actually closed for you before? (ranks the tiers with real data)
- Is GoDaddy hosting a real signal or noise? (#11)
- Any angles here you're *not allowed* to pitch (legal/compliance framing restrictions from Heartland)?
- For conversion batches: Toast first or Square first?
- **NEW:** Is a restaurant on **Owner.com** (website+ordering solved, no POS/payroll) a good lead (proven tech buyer) or a bad one (ordering already displaced)? The pattern is everywhere — the answer redirects a lot of pipeline.
- **NEW:** Are **institution holdouts** (decades of deliberate cash-only) worth your team's calls at all, or should #12 filter to modernization-signal cases only?
- **NEW:** Does the **fragmented-stack consolidation** pitch (#15) fly, or do you prefer pure single-competitor batches?
- **NEW:** Banquet/catering **service-charge disclosure** (#3 variant) — pitchable, or too accusatory?
