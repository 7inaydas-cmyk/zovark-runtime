# INDEPENDENT AUDIT — SLICE 4 (deterministic evidence dedup + multi-evidence)

Fresh adversarial auditor, read/run-only (one mutation test applied to `ingest.py` then
restored byte-identical). Diff scope: `ingest.py` dedup (+20/-1), 3 fixtures, test file.

## VERDICT: PASS — no DANGEROUS-DIRECTION findings.

- **Determinism:** 9-artifact sha256 identical across double-runs for all 3 multi
  fixtures; dedup uses an insertion-ordered list + set-for-membership only (no
  iteration nondeterminism).
- **Canonical `edr-sample-001` hash unchanged:**
  `8749bf8af7a403110b3a622a22107cc0645e7fe8c455291da9c945e9513445a0`.
- **Dedup (no data loss):** exact byte-identical events collapse to one; any
  single-field difference (incl. `pid`, `command_line`, `timestamp`) keeps both;
  cross-source-type same-body kept; first-occurrence order preserved.
- **Forgery still rejected on multi packages:** verdict/findings/ledger tampering all →
  `extracted_view_mismatch`; `verify_proof_package_strict` re-derives findings from the
  hash-verified ledger.
- **No benign/notify-only reachable:** no-rule-match inputs fail closed at "handoff
  requires non-empty verdict evidence_refs"; no package written. All 3 fixtures →
  `confirmed_malicious` + `isolate_host`.
- **Out-of-timestamp-order input fails closed** with zero partial artifacts on disk.
- **No network/model/secret/architecture/ReviewOps change** in the diff.
- **Guard mutation-tested:** disabling dedup (`return entries`) breaks 4 tests
  (non-vacuous), failing at `findings.py … evidence_id must be unique`.

## Findings classified
- **DANGEROUS-DIRECTION: none.**
- **FAIL-SAFE:** (1) duplicate-content evidence now collapses (first wins) instead of
  hard-failing downstream — only removes byte-identical dups, never distinct evidence;
  safe direction. (2) Cross-source-type identical-body events share a content_hash in
  the memory store (idempotent put; both ledger entries survive); pre-existing, unchanged
  by this slice.

(Auditor's plain-pytest run reported 169 passed / 18 skipped — jsonschema-dependent
tests skip without the extra; the controller's `uv run` with jsonschema shows 290 passed.)
