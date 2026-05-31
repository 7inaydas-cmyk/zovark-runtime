# AUDIT_SLICE_4 (self-audit) — multi-alert / multi-evidence

Scope: `ingest._dedupe_entries` (new), 3 fixtures (`edr-multi-001/002/003.json`),
`tests/test_multi_evidence.py`. No verifier/verdict/replay/schema change.

| Check | Result |
|---|---|
| Deterministic ordering | PASS — input-order (alert, fixed collection order, array order); two runs byte-identical. |
| Deterministic dedup | PASS — first-occurrence-wins by evidence_id; multi-002 5→4 evidence. |
| Out-of-order timestamps fail closed | PASS — `ZovarkValidationError` (timeline non-decreasing invariant). |
| One-alert compatibility / canonical hash unchanged | PASS — dedup no-op without dups; `8749bf8a…` unchanged. |
| LSASS/SMB rule paths exercised | PASS — multi-001/003 fire RULE-LSASS-DUMP + RULE-SMB-LATERAL-MOVEMENT. |
| No benign/notify-only | PASS — only `confirmed_malicious` derivable; isolate_host handoff. |
| Verifier unchanged + rejects forgery | PASS — strict verify rejects a forged multi package. |
| No network/model/secrets | PASS — ingest parses recorded JSON only. |
| Architecture/ReviewOps untouched | PASS. |

## Classified findings
- **DANGEROUS-DIRECTION: none.**
- **FAIL-SAFE (documented):** true multi-*independent-alert* campaigns are out of scope;
  the model is one alert-context + many events. Documented in SLICE_4_PLAN. Worst case is
  under-coverage (not a wrong result).
