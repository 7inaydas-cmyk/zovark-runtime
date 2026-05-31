# FINAL_ACCEPTANCE — outputs & stop conditions

## Required final outputs

On `main`:
- Slice 3 + Slice 4 commits (if green + self-audited + independently audited).
- `docs/slices/SLICE_3_PLAN.md`, `VERIFY_SLICE_3.md`, `AUDIT_SLICE_3.md`, `INDEP_AUDIT_SLICE_3.md`.
- `docs/slices/SLICE_4_PLAN.md`, `VERIFY_SLICE_4.md`, `AUDIT_SLICE_4.md`, `INDEP_AUDIT_SLICE_4.md`.

On `slices-5-8-staging`:
- Slice 5, 6, 7, 8 commits.
- `SLICE_5..8_PLAN.md`, `VERIFY_SLICE_5..8.md`, `AUDIT_SLICE_5..8.md`, `INDEP_AUDIT_SLICE_5..8.md`.
- `docs/slices/REVIEW_REQUIRED.md`.

Global:
- `docs/slices/SLICES_PROGRESS.md`
- `docs/slices/INDEP_AUDIT_SUMMARY.md`
- `docs/slices/FINAL_OVERNIGHT_REPORT.md`

## FINAL_OVERNIGHT_REPORT.md must include
starting HEAD; final main HEAD; final staging HEAD; commit SHA per slice; merged-vs-staged
table; command log with exit codes; test summary; proof-package hashes; verifier statuses;
old/new baseline changes and reasons; all audit findings; unresolved FAIL-SAFE notes;
zero-unresolved-DANGEROUS-DIRECTION confirmation; architecture-untouched confirmation;
ReviewOps-untouched confirmation; no-secrets confirmation; no-network/live-LLM-in-
deterministic/replay/verdict-path confirmation; no-readiness/SLA/compliance/customer-claims
confirmation; exact morning operator decisions.

## REVIEW_REQUIRED.md must state (per staged slice 5–8)
- Slice 5: old hash; new hash; exact bytes/artifacts changed; reason for baseline
  divergence; semantic-equivalence evidence; whether architecture oracle update is needed
  later; operator decision: approve runtime report baseline or request changes.
- Slice 6: connector boundary description; proof deterministic/replay paths are
  network-free; secret-scan result; operator decision: approve connector boundary or
  request changes.
- Slice 7: model record-time boundary; replay no-live-call proof; model I/O hash
  evidence; model_contribution behavior; operator decision: approve recorded-AI boundary
  or request changes.
- Slice 8: runtime schema enforcement points; proof-status behavior; ADR-0053 authority
  status; operator decision: approve schema/proof-status integration or request changes.

## Final commands before stopping (where applicable)
`git status --short`; `git branch --show-current`; `git log --oneline -8`; full
suite/check; targeted slice tests; proof-package twice on canonical fixture;
proof-package-verify; schema validation tests; replay validation tests; connector
recorded-fixture offline test; live-AI recorded replay test (fake provider); secret scan;
`git diff --stat main..slices-5-8-staging`; `git status` on both branches.

## Success stop conditions (stop only when one is true)
- **A. Preferred:** Slices 3+4 merged green+audited to main; slices 5–8 implemented,
  tested, verified, independently audited, committed on `slices-5-8-staging`;
  REVIEW_REQUIRED.md + FINAL_OVERNIGHT_REPORT.md written; zero unresolved
  DANGEROUS-DIRECTION; main safe + deterministic.
- **B. Safe partial:** some slices committed; no unsafe partial work; CONTINUATION.md
  gives exact resume `/goal`; no fake done.
- **C. Blocked:** BLOCKER.md explains exact tripwire, command, output, inspected files,
  HEAD, safest next action.

Do NOT ask for clarification unless real credentials, external account access, or an
explicit operator business decision is required. Otherwise use placeholders, recorded
fixtures, mocks/fakes, and fail-closed behavior.
