# classify_website.md
<!-- Attach: PIPELINE.md (fingerprint section). Use for sites the detector scripts can't resolve,
     or to spot-check detector output. Paste page source / observed URLs below. -->

Classify this restaurant website's ordering platform and hosting from the evidence below.

Known fingerprints (also see PIPELINE.md — that list wins if they conflict):
- Toast: links/redirects to `order.toasttab.com`, toasttab scripts
- Square: `*.square.site`, `squareup.com` checkout, Square JS
- Third-party-only: ordering resolves only to DoorDash/UberEats/Grubhub
- GoDaddy hosting: NS records at `domaincontrol.com`, GoDaddy site-builder markup

Rules:
- Classify only from evidence present. No inference from vibes. Unknown is a valid answer.
- Note NEW fingerprint patterns you spot — they get added to the detector's data file.

Output:
```
platform: Toast/Square/third-party-only/none/other/unknown
hosting: GoDaddy/other/unknown
evidence: the exact URLs/snippets that decided it
new_fingerprints: any reusable pattern spotted, or none
```

---
EVIDENCE (URLs visited, redirects observed, HTML source):
<!-- paste here -->

<!-- Changelog: v1 2026-07 initial -->
