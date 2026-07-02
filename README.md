# prompts/
<!-- Reusable AI prompts, one file per task. Convention:
     1. Every prompt names the context docs to attach (keeps prompts short — context lives in the docs).
     2. Every prompt defines its output format so results paste cleanly into the spreadsheet/DB.
     3. When a prompt produces bad output twice for the same reason, fix the prompt (or the doc it
        references), and note what changed at the bottom of the prompt file.
     4. New task type → new file. Don't grow one mega-prompt. -->

| Prompt | Task | Attach |
|---|---|---|
| `enrich_lead.md` | fill enrichment fields for one candidate | LEAD_SPEC, PITCH_ANGLES, FEEDBACK_LOG |
| `pitch_line.md` | one-line pitch from detected signals | PITCH_ANGLES, CLIENT_PROFILE |
| `classify_website.md` | platform/hosting/ordering from a site's HTML | PIPELINE (fingerprints section) |
<!-- add rows as prompts are created -->
