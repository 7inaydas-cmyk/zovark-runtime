# VERIFY_SLICE_4 — multi-alert / multi-evidence inputs

State at build: branch `main` HEAD `c40b4bc` (+ working changes), clean before.

## Commands & results
- 3 multi fixtures generate + strict-verify (each exit 0, status verified):
  - `edr-multi-001`: 5 evidence; rules OFFICE-SPAWN, PS-C2, **LSASS-DUMP, SMB-LATERAL**;
    verdict `confirmed_malicious`.
  - `edr-multi-002`: duplicate process event → **deduped** (5 input events → 4 unique
    evidence); rules OFFICE-SPAWN, PS-C2; verdict `confirmed_malicious`.
  - `edr-multi-003`: 6 evidence; all 4 rules incl LSASS + two SMB attempts; verdict
    `confirmed_malicious`.
- Dedup: `normalize_evidence` of multi-002 yields 4 unique evidence_ids (no collision).
- Determinism: two runs per fixture byte-identical.
- Out-of-timestamp-order input → **fail-closed** (`ZovarkValidationError`).
- Same-timestamp reorder → same verdict + same evidence-hash set (semantic equivalence).
- One-alert fixture (`edr-sample-001`) combined hash =
  `8749bf8af7a403110b3a622a22107cc0645e7fe8c455291da9c945e9513445a0` — **UNCHANGED**
  (dedup is a no-op without duplicates).
- Forgery on a multi package (verdict→benign) → strict verify **fails closed**.
- Targeted `tests/test_multi_evidence.py` → **15 passed**. Full suite → **290 passed**.
  Phase-0 checks → PASS.

## Acceptance mapping
- N source types / many events: all 5 collection types supported; LSASS + SMB exercised.
- ≥3 distinct multi-event fixtures generate + verify: ✅.
- Deterministic ordering + dedup, documented: ✅ (SLICE_4_PLAN §"Ordering & dedup").
- One-alert compatibility: ✅ (canonical hash unchanged).
- No benign/notify-only: ✅ (only `confirmed_malicious` derivable; isolate_host handoff).
- True multi-independent-alert campaigns: documented out-of-scope.

## Invariants held
Only `ingest._dedupe_entries` added (no verifier/verdict/replay change). Deterministic;
no network/model. proof-package-verify unchanged + still rejects forgery. Architecture/
ReviewOps untouched.
