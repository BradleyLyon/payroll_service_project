# enrich_lead.md
<!-- Attach: LEAD_SPEC.md, PITCH_ANGLES.md, FEEDBACK_LOG.md. Paste candidate data below the line. -->

You are enriching one restaurant lead for the Simon/Heartland project. Attached docs define a
qualified lead (LEAD_SPEC), available pitch angles (PITCH_ANGLES), and client feedback that
overrides defaults (FEEDBACK_LOG).

Rules:
- Only claim what the provided data supports. Anything unverifiable = "unknown", never guessed.
- Check disqualifiers first (chain, franchise, closed, rate-shopper). If disqualified, stop and say why.
- Pick ONE primary angle — the highest-priority angle whose trigger matches a verifiable observation.
- Pitch line must contain a specific fact about THIS business (name, address, observed platform, etc.).

Output exactly this, one field per line (matches LEAD_SPEC columns):
```
qualified: yes/no (+ reason if no)
segment: S1/S2/S3/S4
website: Y/N + URL
doordash: Y/N/unknown
platform: Toast/Square/none/other/unknown
hosting: GoDaddy/other/unknown
size_estimate: headcount range + # locations, or unknown
contact: name + phone/email, or unknown
primary_angle: angle # + name from PITCH_ANGLES
pitch_line: one sentence
flags: anything odd a human should check
```

---
CANDIDATE DATA:
<!-- paste bot output row + anything found manually -->

<!-- Changelog: v1 2026-07 initial -->
