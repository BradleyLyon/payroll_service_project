# DECISIONS.md
<!-- One line per decision: DATE | decision | why | revisit-when. Newest on top.
     AI sessions: read this before proposing architecture or process changes — if your idea was already
     rejected here, don't re-propose it without new information. Add a line whenever a choice gets made
     that a future session might otherwise re-litigate. Never delete lines; strike through reversed ones. -->

- 2026-07 | Ownership-change leads ranked S1, above pre-opens | established income + actively re-deciding vendors; pre-opens may have locked plans before we find them | revisit after Pilot A/B outcome data
- 2026-07 | SQLite over Postgres | zero setup, one file, schema ports later | revisit if data-resale business materializes or concurrent writers needed
- 2026-07 | Append-only snapshots, never overwrite pulls | diff engine + 1yr license re-evaluation trove | permanent
- 2026-07 | GoDaddy hosting = secondary signal only (+1, never primary angle) | unvalidated — Simon hasn't confirmed it matters | revisit on Simon's feedback
- 2026-07 | Conversion batches ship single-platform (all Toast or all Square) | consistent research + pitch per batch | per Simon preference
- 2026-07 | Never rank a lead on "cheaper rates" | oversaturated pitch + Heartland's weak spot | permanent
- 2026-07 | NYC focus over Maine | in-person access is our edge; Simon serves any state remotely | revisit if NYC pipeline saturates
- 2026-07 | Manual enrichment first, automate what's measured slowest | manual pass = the automation spec | ongoing
- 2026-07 | Docs use HTML comments for meta-notes | invisible on GitHub render, visible to AI reading raw | permanent
2026-07-06 — Split angle #10 into 10a (third-party-only; bot-only, search-resistant) and 10b (white-label-dependent: order.online/Sauce); added #15 fragmented multi-platform stack. See PITCH_ANGLES.md.
2026-07-06 — Entity resolution by name+address+entity is mandatory; 4 name collisions hit in one session. Places API place_id becomes the canonical business key once the key is live.
2026-07-06 — Hotel-address auto-DQ (hotel F&B = enterprise-controlled vendor decisions).
2026-07-06 — Every sourced fact carries verified_as_of; crowd signals expire ~12mo (John's of Bleecker appeared cash-only in Yelp's category a decade after taking cards), map-scrape candidate lists expire in weeks (all four seed candidates from the June notes had drifted by July).
2026-07-06 — Detector priority reordered: (1) marketplace-residue (10a: marketplace listings → Places lookup → no-website filter), (2) platform fingerprints incl. new table entries, (3) hosting DNS. Rationale: 10a is the one thing manual work cannot approximate; hosting was blank on 13/13 manual leads but is mechanical once built.
2026-07-06 — Detectors scrape competitor ordering pages, not just fingerprint URLs — Toast/Clover pages leak surcharge disclosures, gift-card programs, delivery config (case: The Grand's 3% surcharge found on its Toast page).
2026-07-06 — Manual pilot delivery format = pilot_batch_leads_YYYY-MM-DD.csv; filename date maps to the batch's pulled_at on ingest, matching the SLA export convention.
