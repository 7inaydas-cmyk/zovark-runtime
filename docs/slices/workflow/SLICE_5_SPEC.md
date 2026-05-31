# SLICE 5 — fully evidence-backed SOC report

Target branch: `slices-5-8-staging` (**STAGE ONLY — do not merge to main**).
Commit message: `feat(slice5): evidence-backed SOC report baseline`

## Goal
Make `customer-report.md` and the `edr-handoff.json` narrative fully evidence-backed.

## Acceptance
- Every sentence in `customer-report.md` is traceable to recorded evidence or
  deterministic verdict metadata.
- Every narrative field in `edr-handoff.json` is traceable to recorded evidence or
  deterministic verdict metadata.
- Tests assert no un-evidenced claim strings.
- Fix the inherited FAIL-SAFE quirk: do **not** mention LSASS unless LSASS evidence
  exists (the V1 `rollback_plan.recovery_notes` hard-codes a "LSASS access event" line
  for any isolate_host).
- This may intentionally fork byte-conformance from strict slice001 **only** if
  `customer-report.md` / `edr-handoff.json` narrative bytes change. Record old hash, new
  hash, and the exact reason for divergence in VERIFY_SLICE_5.md + REVIEW_REQUIRED.md.
- Semantic equivalence retained on verdict / evidence / replay (those hashes unchanged).
- No readiness/SLA/compliance/customer claims introduced.
- `zovark-architecture` remains untouched. The new runtime baseline is **provisional**;
  whether/how to update the architecture oracle is a **separate operator decision**.

## Implementation guidance
- Build a **traceability helper** (report sentences/narrative fields derive from
  evidence refs, finding ids, verdict metadata), not one-off string checks.
- Do not add unsupported LSASS/SMB/credential/lateral-movement/containment claims.
- Do not change verdict/evidence semantics unless explicitly required + documented.

## Tests
- Canonical report has no unsupported LSASS claim; LSASS language appears only when
  LSASS evidence exists.
- Report-sentence traceability passes; edr-handoff narrative traceability passes.
- New baseline hash recorded; `proof-package-verify` still passes.
- verdict/evidence/replay semantic hashes remain equivalent where expected.

## Independent audit
- Search report + handoff for unsupported claims. Remove LSASS evidence → confirm LSASS
  language disappears. Confirm old→new baseline documented. Confirm `main` baseline
  untouched. Confirm REVIEW_REQUIRED.md asks the operator whether/how to update the
  architecture oracle separately.
