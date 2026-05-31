# VERIFY_SLICE_5 — fully evidence-backed SOC report (STAGING ONLY)

Branch `slices-5-8-staging`. **Not merged to main.** Intentionally forks report bytes.

## Baseline fork (old → new)
- `edr-sample-001` combined 9-artifact SHA-256:
  - OLD (main): `8749bf8af7a403110b3a622a22107cc0645e7fe8c455291da9c945e9513445a0`
  - NEW (staging): `424d858c40e87730a09fc1e9b610194e76dd1e22dc5e219c9f50ca7e412bcf39`
- Only artifact changed for `edr-sample-001`: **`edr-handoff.json`** (the unconditional
  "given the LSASS access event" recovery-note removed — no LSASS evidence exists).
- **Semantic equivalence retained**: `verdict.json`, `evidence-ledger.json`,
  `findings.json`, `timeline.json`, `investigation-tape.json`, `audit-chain-entry.json`,
  `replay-report.json`, `customer-report.md` all **UNCHANGED** for `edr-sample-001`.
- `edr-multi-001/003` (full report path): `customer-report.md` changed — removed
  unsupported "Microsoft Word"/"opened a document"/"phishing implant" framing; kept
  evidence-backed LSASS/SMB lines (those packages have credential_access + lateral
  evidence). verdict/evidence/replay unchanged.

## Changes
- `writer.py` "What happened?" full-path narrative: evidence-derived; no Word/document/
  phishing/"downloaded N KB" claims.
- `handoff.py`: LSASS recovery-note clause now gated on `_has_lsass_evidence(tape)`
  (credential_access evidence referencing LSASS).
- Pinned-hash test constants repointed to the staging baseline `424d858c…` (documented
  fork; main keeps `8749bf8a…`).

## Commands & results
- Traceability tests `tests/test_report_traceability.py` → **10 passed** (no Word/
  phishing/document/implant; LSASS only with credential_access evidence; edr-sample-001
  handoff drops LSASS; multi-001 keeps evidence-backed LSASS).
- Full suite → **300 passed**. Determinism: edr-sample-001 two runs byte-identical.
- All affected fixtures still `proof-package-verify` exit 0.

## Provisional baseline
The new runtime report baseline is **provisional**. Whether/how to update the
architecture oracle (which still carries the old slice001 narrative) is a **separate
operator decision** — see REVIEW_REQUIRED.md.
