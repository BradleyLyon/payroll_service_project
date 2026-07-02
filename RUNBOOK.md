# RUNBOOK.md
<!-- Purpose: the literal weekly loop. Either of us runs it alone, start to finish. Update commands as scripts ship — a wrong runbook is worse than none. -->

## One-time setup (per machine)
- [ ] Google Places API key in `.env` (never commit it; `.env` is in `.gitignore`)
- [ ] `pip install -r requirements.txt`
- [ ] `leads.db` present (or run `init_db.py` <!-- to write -->)

## Weekly loop (~half day once automated; Pilot A = most of a week)

### 1. Pull (Mon)
- [ ] LAMP → filter pending, On-Premises only, NYC → export CSV
- [ ] Save as `data/pulls/pending_YYYY-MM-DD.csv` (quote the path — filename has a space if using LAMP's default name)
- [ ] Ingest: `python ingest_sla.py "data/pulls/pending_YYYY-MM-DD.csv"` <!-- until built: manual import, note pulled_at -->
- [ ] Diff output = this week's candidates (first run: everything is new)

### 2. Bot pass (Mon)
- [ ] `python restaurant_status_bot.py` on the candidates
- [ ] Sanity-check output: row count matches input, no all-error runs, no obvious API failures

### 3. Spot-check (Tue)
- [ ] Pick 10 random rows → verify against Google Maps by hand
- [ ] Chain flags correct? No-listing rows genuinely unlisted?
- [ ] <2 errors in 10 = proceed. More = fix bot before enriching garbage.

### 4. Select + enrich (Tue–Wed)
- [ ] Rank raw candidates by gut vs LEAD_SPEC segments; take top ~15 (deliver ~10)
- [ ] Per lead: website? DoorDash? platform/hosting (when detectors live)? size estimate? contact? angle + one-line pitch (PITCH_ANGLES.md)
- [ ] Drop any lead where chain/franchise status stays ambiguous
- [ ] Log every enrichment step you do by hand → future automation list

### 5. Score + package (Thu)
- [ ] Apply LEAD_SPEC rubric, sort descending
- [ ] Build `leads_batch_{N}_{YYYY-MM-DD}.xlsx` per LEAD_SPEC output format
- [ ] Record batch in `leads` table

### 6. Deliver (Fri)
- [ ] Send to Simon with ≤3 questions (always include: "which would you call first, and why?")
- [ ] Log his reply verbatim in FEEDBACK_LOG.md
- [ ] Commit: new pull file, DB, batch xlsx, doc updates

### 7. Outcomes (monthly nag)
- [ ] Ask Simon: per delivered lead — called? closed? rejected why?
- [ ] Update `leads.outcome`. This is the only proof the 3–5% is real.

## When something breaks
- Places API errors → check quota/billing on the GCP console first.
- LAMP export looks wrong → compare row count to last week's; SLA changes formats without notice (note it in DATA_SOURCES.md).
- Can't find a contact → deliver anyway with contact marked unknown, note it; don't sink >15 min per lead.

## Pilot A deviation (this week only)
Skip steps that need unbuilt scripts: ingest manually, score by hand, enrich everything manually. The point is the deliverable and the feedback, not the automation.
