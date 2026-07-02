# Project Plan — Next Two Weeks + Repo Doc Structure
*Brad & Jack · Simon lead-gen project · July 2026*

---

## Part 1: Doc types for the GitHub repo

Goal: any AI model (or a new person) can pick up any task with zero re-explaining. Keep each doc short and current — stale docs are worse than none.

**Context docs (the "who/what/why" layer)**
1. `PROJECT_OVERVIEW.md` — the business model in one page: who Simon is, what we do (qualify, not close), close-rate numbers (referral 75%, cold 15–20%, CPA 95%), pilot plan (A → B → weekly feed), NYC focus.
2. `CLIENT_PROFILE.md` — Heartland/Global Payments products, what Simon actually sells, his handoff process, his feedback verbatim. (The Heartland report covers most of this — commit it here.)
3. `PITCH_ANGLES.md` — the niche problem angles (tip compliance, W-2 tip codes, WOTC, surcharge signage, no-website/no-DoorDash, GoDaddy, competitor pain points). This is the enrichment brain.

**Spec docs (the "what counts" layer)**
4. `LEAD_SPEC.md` — definition of a qualified lead, hard disqualifiers (chains, brand-controlled franchises), enrichment fields required per lead, scoring/ranking rubric, output spreadsheet format.
5. `DATA_SOURCES.md` — every source (SLA LAMP, DOHMH inspections, DOB NOW, DCWP, community boards, Google Places), what each signals, export format, refresh cadence, quirks (e.g. 1/1/1900 = new establishment).

**Technical docs (the "how" layer)**
6. `PIPELINE.md` — how data flows: CSV export → bot → enrichment → DB → ranked output. One diagram, list of scripts and what each does.
7. `DB_SCHEMA.md` — tables, fields, why snapshots exist (license re-evaluation a year later = the treasure trove).
8. `RUNBOOK.md` — the literal weekly checklist: export this, run this command, spot-check this, deliver this. Written so either of you can run the whole loop alone.

**Working docs (the "memory" layer)**
9. `DECISIONS.md` — running log of choices and why (e.g. "SQLite over Postgres for now"). One line each.
10. `FEEDBACK_LOG.md` — Simon's reaction to every batch. This drives Pilot B and the ranking rubric.
11. `prompts/` folder — reusable AI prompts per task (enrich a lead, write a pitch line, classify a website), each referencing the context docs.

Skip anything else until you feel the pain of not having it.

---

## Part 2: The two weeks

**Principle:** Pilot A out the door by end of Week 1. Everything else is secondary — Simon's feedback is the input for half of Week 2, so the sooner it ships, the less dead time.

### Week 1 — ship Pilot A

**Monday — unblock + skeleton**
- Finish Google Places API key, run `restaurant_status_bot.py` end-to-end on `Pending Licenses.csv`.
- Set up repo structure: create all doc files above as skeletons, fill in `PROJECT_OVERVIEW` and `LEAD_SPEC` (30 min each, rough is fine).

**Tuesday — verify the bot**
- Manually spot-check ~20 bot output rows against Google Maps. Tune chain detection and "no listing found" logic.
- Start `DATA_SOURCES.md` while the checks are fresh.

**Wednesday — build Pilot A (manual)**
- Pick the 10 best pre-opens from bot output. Enrich each by hand: website/DoorDash presence, contact info, size estimate, one compliance flag, one-line pitch angle.
- This manual pass IS the research — write down every step you take, it becomes the automation spec later.

**Thursday — database v1**
- SQLite (zero setup, one file, upgrade to Postgres later if the data business materializes).
- Minimum schema: `licenses` (raw SLA rows + `pulled_at` date), `businesses` (deduped entities), `enrichments`, `leads` (what went to Simon + status).
- Import the current CSV as snapshot #1. Every future export gets its own `pulled_at` — that's what makes year-later re-evaluations queryable.

**Friday — deliver**
- Package Pilot A as the ranked spreadsheet, send to Simon with 2–3 pointed questions max (which lead would you call first and why; what's missing; how many per week).
- Commit everything, quick retro: what took longest this week → that's the first automation target.

### Week 2 — automate the loop + Pilot B

**Monday — platform detection prototype**
- The Toast/Square fingerprint script (redirect capture + HTML signatures). Lightweight scan first, skip headless browser until needed.

**Tuesday — hosting detection**
- GoDaddy flag via domain lookups. Wire both detectors into the enrichment output.

**Wednesday — the diff engine (treasure trove mechanic)**
- Script: ingest a fresh SLA export, diff against DB → new licenses = this week's fresh leads, disappeared/changed ones get status updates. This turns the DB from storage into a lead generator.

**Thursday — Pilot B**
- Fold in Simon's feedback (log it in `FEEDBACK_LOG.md` first). Build the refined batch — semi-automated this time: bot + detectors do the finding, you do final judgment and pitch lines.

**Friday — lock the cadence**
- Write `RUNBOOK.md` from what you actually did. Deliver Pilot B. Backlog next steps: CPA referral track, DOHMH/DOB sources, competitor conversion batches.

---

## Split between you and Jack

Suggested: one of you owns **pipeline/code** (bot, DB, detectors), the other owns **leads/client** (manual enrichment, pitch lines, Simon comms, feedback log). Swap roles for Pilot B so you both can run everything. Wednesday W1 and Thursday W2 are pair days — enrichment goes 2x faster with one person researching and one writing.

## If you stall

Waiting on Simon, blocked on an API, whatever — default filler tasks, in order:
1. Manually verify more bot output rows (accuracy compounds).
2. Fill in the weakest doc in the repo.
3. Hand-check 5 restaurants from the DOHMH 1/1/1900 list (validates source #2 before you code it).
4. Draft the CPA outreach angle (95% close channel, zero code required).
