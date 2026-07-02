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
