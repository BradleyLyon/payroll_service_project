# LEAD_SPEC.md
<!-- Purpose: the definition of "done" for a lead. The bot, the enrichment prompts, and the output spreadsheet all conform to this. Update the rubric after every Simon feedback round. -->

## Definition of a qualified lead
A business is a **qualified lead** when ALL are true:
1. Independent (not a corporate chain; franchise only if services aren't brand-controlled — verify).
2. In a target segment (see segments below).
3. At least one pitch angle from PITCH_ANGLES.md applies, backed by a *verifiable observation*.
4. Enrichment fields below are filled (or marked unknown deliberately, not lazily).
5. Not previously delivered to Simon (check `leads` table).

## Target segments
<!-- Ranked. Reorder when Simon's feedback says otherwise. -->
- **S1 — Ownership change:** license transfer / new LLC on filing. Established place with proven income, no loyalty to inherited vendors — contracts up for review. Pre-opens may have locked plans months before we find them; new owners are actively deciding.
- **S2 — Pre-open:** pending liquor license and/or 1/1/1900 DOHMH record; no website; no DoorDash. Angle: full bundle, website+DoorDash hook.
- **S3 — Established sweet spot:** multi-location independent, ~10–50 employees. Angle: payroll/compliance value.
- **S4 — Competitor conversion:** on Toast or Square (single-platform batches only).

## Hard disqualifiers
- Corporate chain or chain-scale brand (McDonald's/Chipotle tier).
- Brand-controlled franchise (services decided by franchisor). <!-- pending Simon's franchise rules -->
- Already a Heartland/Global Payments client. <!-- ASK SIMON: can he check a list for us? -->
- Rate-shopper profile: lead whose ONLY angle is "cheaper rates" — not Heartland's strength, skip.
- Business appears closed/permanently closed on Google Places.

## Enrichment fields (one row per lead)
<!-- These are the spreadsheet columns. Bot fills what it can; manual/AI fills the rest. -->
| Field | Source | Req? |
|---|---|---|
| business_name | SLA / Places | yes |
| address, borough | SLA / Places | yes |
| segment (S1–S4) | derived | yes |
| license_status + serial | SLA | S1/S2 |
| google_status (open/pre-open/no listing) | bot | yes |
| chain_flag | bot | yes |
| website (Y/N + URL) | manual/bot | yes |
| doordash_presence (Y/N) | manual | yes |
| ordering_platform (Toast/Square/none/other) | detector | when live |
| hosting (GoDaddy flag) | detector | when live |
| size_estimate (headcount range, # locations) | manual | yes |
| contact (name, phone/email) | manual | best effort |
| primary_angle (from PITCH_ANGLES.md) | manual/AI | yes |
| pitch_line (one sentence, specific) | manual/AI | yes |
| score + rank | rubric below | yes |
| evidence_links (Maps URL, site, listing) | all | yes |

## Scoring rubric v0
<!-- Draft. Calibrate against Simon's "which would you call first" answer. -->
Start at 0, add:
- +3 confirmed ownership change (S1 — verify the transfer actually happened, filings lag)
- +3 pre-open with no website AND no DoorDash (S2 perfect)
- +2 multi-location independent
- +2 headcount estimate 10+ (payroll value)
- +2 verifiable compliance angle (surcharge signage, biweekly pay in job post, paper-era ops)
- +2 direct contact found (owner name + phone/email)
- +1 third-party-only delivery (commission bleed angle)
- +1 GoDaddy hosting <!-- unvalidated signal, see PITCH_ANGLES #11 -->
- −2 weak/no pitch angle
- −3 any ambiguity about chain/franchise status (resolve or drop)

Deliver only leads scoring ≥ <!-- set after Pilot A -->. Rank descending.

## Output format
- One spreadsheet per batch: `leads_batch_{N}_{YYYY-MM-DD}.xlsx`, sorted by rank.
- Row 1 frozen headers = fields above. One tab. No colors/merged cells — his team will import it.
- Every batch logged in `leads` table with delivery date + later outcome (called / closed / rejected + reason).
<!-- Outcome tracking is what makes the 3–5% measurable. Nag Simon for outcomes monthly. -->
