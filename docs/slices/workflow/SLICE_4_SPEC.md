# SLICE 4 — multi-alert / multi-evidence inputs

Target branch: `main` (mergeable if green + audited).
Commit message: `feat(slice4): multi-alert multi-evidence proof packages`

## Goal
Support deterministic multi-alert / multi-evidence inputs while preserving one-alert
compatibility.

## Acceptance
- Command accepts input with N alerts and many events using the repo-real supported
  event/source types (from `ingest.py`: `edr_alert`, `process_event`, `network_event`,
  `network_flow`, `credential_access`, `lateral_movement_attempt`).
- The existing one-alert fixture (`tests/fixtures/edr-sample-001.json`) still generates
  and verifies unchanged.
- At least 3 distinct multi-event fixtures generate + pass the strict verifier:
  `tests/fixtures/edr-multi-001.json`, `edr-multi-002.json`, `edr-multi-003.json`.
- Evidence ordering is deterministic and documented.
- Deduplication is deterministic and documented.
- Richer rule paths exercised, incl. LSASS (RULE-LSASS-DUMP) and SMB
  (RULE-SMB-LATERAL-MOVEMENT) **if existing rule semantics support them** — do not
  invent rules.
- No benign/notify-only logic.

## Implementation guidance
- Scout current input validators (`ingest.normalize_evidence`, `tape`, `findings.RULES`)
  before changing input shape. Maintain backward compatibility.
- Use actual event/source type names from the repo. Do not invent product semantics the
  rule table does not support.
- Keep canonicalization deterministic: a shuffled-equivalent input must canonicalize to
  the same output (or to documented same semantic hashes).

## Tests
- One-alert fixture still generates + verifies (combined hash unchanged for it).
- Each of the 3 multi fixtures generates + verifies.
- Shuffled-equivalent input → same output / documented same semantic hashes.
- Duplicate evidence deduped deterministically.
- LSASS/SMB paths exercised where supported.
- `proof-package-verify` still rejects a semantic forgery.

## Independent audit
- Shuffle events repeatedly; add duplicates; try edge ordering. Confirm deterministic
  canonicalization. Confirm no benign/notify-only logic appeared.
