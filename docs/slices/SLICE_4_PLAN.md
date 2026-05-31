# SLICE 4 PLAN — multi-alert / multi-evidence inputs

## State (re-derived)
main `c40b4bc` (Slice 3 merged), clean, baseline green.

## Findings from scout
- `ingest.normalize_evidence` already supports all 5 event collections
  (`process_events`, `network_events`, `network_flows`, `credential_access_events`,
  `lateral_movement_events`) → the 6 source types. Ordering is deterministic: alert
  first, then collections in fixed order, then array insertion order.
- It did **not** dedup; two identical events produced the same content-addressed
  evidence_id and would collide on the unique-id invariant.
- The deterministic rule engine (`findings.RULES`) yields only high/critical findings →
  only `confirmed_malicious` is derivable. (No benign/notify-only — preserved.)

## Smallest change
1. `ingest._dedupe_entries`: drop exact-duplicate evidence by evidence_id, first
   occurrence wins, order preserved. No-op when no duplicates → V1 fixture + canonical
   hash unchanged (verified).
2. Three multi-event fixtures exercising all five source types incl LSASS
   (`credential_access_events`, RULE-LSASS-DUMP) and SMB (`lateral_movement_events`,
   RULE-SMB-LATERAL-MOVEMENT):
   - `edr-multi-001.json` — full multi-stage, all 4 rules, 5 evidence.
   - `edr-multi-002.json` — duplicate process event + multiple network events (dedup
     case): 5 input events → 4 unique evidence.
   - `edr-multi-003.json` — LSASS + two SMB attempts, all 4 rules, 6 evidence.

## Ordering & dedup semantics (documented)
- **Ordering** is deterministic for a fixed input: edr_alert, then event collections in
  the fixed `_EVENT_COLLECTIONS` order, then each array's insertion order. Same input →
  byte-identical output (determinism test).
- The timeline enforces **non-decreasing timestamps**: an input whose events are
  reordered into a timestamp-violating sequence is **rejected fail-closed**
  (`ZovarkValidationError`), not silently reordered or accepted. When reordered events
  share the same timestamp (monotonicity preserved), byte output may differ but the
  **verdict value** and the **set of evidence content hashes** are invariant
  (documented semantic-equivalence property).
- **Dedup**: exact-duplicate evidence (same source_type + content) is dropped
  deterministically (first wins), so duplicate telemetry cannot break the unique-id
  invariant or change the verdict.

## "N alerts" scope (honest boundary)
The slice001 model is one alert-context per investigation/package (one edr_alert +
many events of all types). This slice delivers the substantive multi-evidence
capability across all five source types. True multi-*independent-alert* campaigns
(multiple edr_alerts → multiple packages or a campaign_record) are a larger product
change and are **out of scope** for this slice; documented, not silently dropped.

## Merge
Slice 4 may merge to `main` after green + self-audit + independent audit. After Slice 4
lands, create `slices-5-8-staging`.
