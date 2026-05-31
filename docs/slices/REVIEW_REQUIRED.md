# REVIEW_REQUIRED — operator decisions for staged slices (5–8)

Branch: `slices-5-8-staging` (built from `main` `43f5812`). **Slices 5–8 are NOT merged
to `main`.** `main` remains the V1 baseline (canonical combined hash
`8749bf8af7a403110b3a622a22107cc0645e7fe8c455291da9c945e9513445a0`, unchanged). Each
slice below needs an explicit operator decision before any adoption to `main`.

## Slice 5 — fully evidence-backed SOC report
- **Old hash (main):** `8749bf8af7a403110b3a622a22107cc0645e7fe8c455291da9c945e9513445a0`
- **New hash (staging, edr-sample-001):** `424d858c40e87730a09fc1e9b610194e76dd1e22dc5e219c9f50ca7e412bcf39`
- **Exact bytes/artifacts changed:** for `edr-sample-001`, only `edr-handoff.json`
  (removed the unconditional "given the LSASS access event" recovery note — no LSASS
  evidence). For `edr-multi-001/003/004` (full report path), `customer-report.md`
  changed: removed unsupported "Microsoft Word / opened a document / phishing implant /
  downloaded N KB / C:\Temp\svchost.exe" claims; LSASS/SMB language now gated on actual
  credential_access/lateral evidence.
- **Reason for divergence:** every report/handoff sentence must be traceable to recorded
  evidence or deterministic verdict metadata; the V1 report carried hard-coded
  un-evidenced narrative inherited from the slice001 oracle.
- **Semantic equivalence:** `verdict.json`, `evidence-ledger.json`, `findings.json`,
  `replay-report.json`, `timeline.json`, `investigation-tape.json`, `audit-chain-entry.json`
  are byte-UNCHANGED for `edr-sample-001`. Verdict/evidence/replay semantics are intact;
  only narrative bytes changed.
- **Architecture oracle:** `zovark-architecture`'s slice001 still emits the old narrative.
  The runtime baseline now diverges from oracle byte-conformance for the report.
- **OPERATOR DECISION REQUIRED:** (a) approve the new runtime report baseline
  (`424d858c…`) for `main`, or request changes; and (b) decide whether/how to update the
  architecture oracle separately (architecture is read-only in this work — a separate,
  explicit architecture change would be required; not done here).

## Slice 6 — EDR connector ingest boundary
- _(to be completed when Slice 6 is built on staging)_

## Slice 7 — recorded live-AI investigation
- _(to be completed when Slice 7 is built on staging)_

## Slice 8 — runtime schema enforcement + proof-status
- _(to be completed when Slice 8 is built on staging)_
