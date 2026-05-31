# V1 Product Slice — Deterministic Proof-Package Command

Status: design (Phase 1). This document is committed **before** the implementation
and is the contract the Phase-4 adversarial audit checks the diff against.

## 1. What this slice produces

One end-to-end, offline, deterministic command in `zovark-runtime`:

```
zovark-runtime proof-package --input <edr-alert.json> --output <dir> [--tenant-id ...] [--memory-dir <dir>]
zovark-runtime proof-package verify --package <dir>
```

`proof-package` ingests one static EDR-style alert JSON and writes the **9-file
proof package** — the same contract `architecture/zovark.slice001` emits — plus a
SOC-readable customer report:

1. `investigation-tape.json` — internal proof substrate (sealed tape)
2. `evidence-ledger.json` — content-addressed evidence with SHA-256 hashes
3. `timeline.json` — chronological reconstruction
4. `findings.json` — rule-based, evidence-backed findings
5. `verdict.json` — deterministic verdict (no model contribution)
6. `edr-handoff.json` — approval-required EDR action card (nothing dispatched)
7. `audit-chain-entry.json` — hash-chained close entry
8. `replay-report.json` — offline replay result (re-derives + re-hashes; no live calls)
9. `customer-report.md` — the SOC report (alert, investigation steps + evidence,
   verdict, approval mode, blast radius, reversal, and explicit replay instructions)

This is `Lane B` (build in runtime). ADR-0053 import is **not** a prerequisite —
the proof package is produced without `runtime_proof_loop` being `complete`.

## 2. Artifact → producing primitive → validating mechanism

| Artifact | Produced by (runtime module) | Validated by |
|---|---|---|
| `evidence-ledger.json` | `proof_package.ingest.normalize_evidence` — content-addressed `ev-<sha256>` via `proof_package.canonical`/`hashing`; **also recorded to the runtime `investigation_memory` store** | `package_verifier` re-derivation + `investigation_memory.LocalInvestigationMemoryStore.verify()` (hash + size) + replay re-hash |
| `investigation-tape.json` | `proof_package.tape.create_tape` + `attach_*` | `package_verifier`; `tape_id = sha256(tenant:alert_ref)[:16]` |
| `timeline.json` | `proof_package.timeline.build_initial_timeline` | `package_verifier`; non-decreasing timestamps |
| `findings.json` | `proof_package.findings.derive_findings` (deterministic rule table) | `package_verifier`; unique `rule_id`s; evidence-ref closure |
| `verdict.json` | `proof_package.verdict.derive_verdict` (severity → class) | `package_verifier`; `signing_tag = sha256(snapshot)` |
| `edr-handoff.json` | `proof_package.handoff.derive_handoff` (`approval_required`, nothing dispatched) | `package_verifier`; idempotency/policy-snapshot hashes recomputed |
| `audit-chain-entry.json` | `proof_package.audit.derive_audit_entry` (hash-chained, genesis-anchored) | `package_verifier`; `this_entry_hash` recompute |
| `replay-report.json` | `proof_package.replay.derive_replay_report` (offline; re-derives verdict, re-hashes evidence; `no_live_llm_call`/`no_live_edr_call` true) | `package_verifier`; replay re-validates every evidence hash + recomputes the verdict |
| `customer-report.md` | `proof_package.writer.render_customer_report` | `package_verifier` (`customer_report` component) |

### Honest reconciliation — which schemas are "authority" here

The `/goal` assumed each of the 9 artifacts has an authority JSON Schema. **It does
not.** Investigated in Phase 1:

- `architecture` ships **zero** JSON Schemas for the slice001 proof-package
  artifacts (no slice/proof/tape/handoff/evidence/ledger/customer schema exists).
  slice001's authority validation mechanism is **`package_verifier.py`** — it
  *re-derives every artifact from the recorded inputs and compares byte-for-byte*,
  re-checks all content hashes, and re-runs the offline replay. That is a strictly
  **stronger** check than JSON-Schema shape validation.
- The 27 ADR blueprint schemas runtime vendored (`verdict_envelope`,
  `replay_record`, `finding`, …) describe a **different, forward-looking contract**
  (ADR-0046 six-stage pipeline). Their shapes do **not** match slice001's artifacts
  (e.g. `verdict.json` has `value`/`signing_tag`; `verdict_envelope` has
  `confidence_basis_points`/`verdict_class`). Binding the 9 artifacts to those
  schemas would be incorrect, not conformant.

**Decision (criterion 4):** the binding "authority schema validation" for this
slice is the authority's own validator — `package_verifier` re-derivation, vendored
verbatim and exposed as `proof-package verify` (exit 0 == valid). Authoring
standalone JSON Schemas for the proof-package contract, and wiring the ADR-0046
`verdict_envelope`/`replay_record` contract, are **NEXT_SLICES** items, not this one.

## 3. Implementation strategy — vendor + reuse (the shorter path)

The `/goal` permits a genuinely shorter path that produces the same evidence
(determinism + schema + slice001 conformance + audit) if documented here. Chosen:

**Vendor slice001's deterministic, stdlib-only derivation modules into
`src/zovark_runtime/proof_package/`** (`ingest, tape, timeline, findings, verdict,
handoff, audit, replay, writer, package_verifier, canonical, hashing`), rewriting
imports `zovark.slice001 → zovark_runtime.proof_package`. Rationale:

1. **Strongest possible conformance evidence.** Faithful vendoring yields
   *byte-identical* output to the slice001 oracle — conformance becomes a trivial
   `diff`, not an argued "semantic equivalence."
2. **Lowest divergence risk.** A hand-rewrite of ~180 KB of intricate hashing/
   timestamp/rule logic would risk subtle hash drift. Vendoring eliminates that.
3. **Matches runtime's established pattern.** Runtime already vendors the 27
   architecture schemas with recorded provenance (`contract-manifest.json`,
   `ARCHITECTURE_REPO_SOURCE.md`). Provenance for the vendored pipeline is recorded
   in `src/zovark_runtime/proof_package/PROVENANCE.md` (architecture `main` =
   `d16935b…`). Vendoring is read-only on architecture (copy, never modify).
4. **Don't re-derive schemas.** Vendoring reuses the contract; it does not
   redefine it.

### Genuine reuse of runtime primitives

- **`investigation_memory.LocalInvestigationMemoryStore`** — load-bearing, not
  decorative. On ingest, each evidence item's canonical bytes are recorded to the
  store (content-addressed, lossless, no wall-clock in metadata). Before sealing,
  the pipeline **re-verifies every evidence item from the store** (`store.verify()`,
  which re-hashes the stored bytes); a mismatch aborts the run fail-closed. This is
  the runtime substrate "recording the investigation" and providing tamper-evidence,
  layered *alongside* slice001's in-tape re-hash so `replay-report.json` stays
  byte-conformant.
- **`proof_package.canonical`/`hashing`** are vendored from slice001 rather than
  reusing runtime's `verdict_derivation.canonical_json_bytes`. Reason: slice001 uses
  `ensure_ascii=False`; runtime's helper uses `ensure_ascii=True`. They diverge for
  any non-ASCII alert content, which would change every evidence hash and break both
  correctness and conformance. Using slice001's canonical guarantees identical
  content-addressed IDs across **all** inputs, not just this ASCII fixture.
- **`derive_verdict` / `validate_replay_record`** (runtime's existing ADR-0046
  primitives) are **deferred**: they operate on the `verdict_input`/`verdict_envelope`/
  `replay_record` contract, which is *not* the slice001 proof-package contract.
  Wiring them is a NEXT_SLICES item (the ADR-0046 pipeline slice).

## 4. Determinism model

- **No wall clock, no randomness, no network, no live LLM** anywhere in the pipeline
  or replay. Verified: vendored modules import only `json`, `hashlib`, `math`
  (no `socket`/`urllib`/`subprocess`/`datetime.now`/`time`/`random`/`eval`/`pickle`).
- All timestamps are derived from the input event timestamps; downstream timestamps
  (verdict `set_at`, audit close, replay) are computed by pure ISO-8601
  second-increment arithmetic, never `now()`.
- All IDs/hashes are SHA-256 over canonical JSON of recorded content.
- **Replay re-validates recorded artifacts and never re-runs a model**: it recomputes
  each evidence hash + the `ev-` id, re-derives the verdict/handoff/audit from the
  recorded tape, and asserts `no_live_llm_call`/`no_live_edr_call`. Replay mode is
  `recorded_output`.
- Output is written with fixed key-insertion order + `indent=2`; the same input
  yields byte-identical bytes on every run (Phase-3 proof: two runs, committed hashes).

## 5. Ingestion security model

- Input is parsed with `json.loads` only (no `eval`, no `pickle`, no YAML, no
  custom deserialization). Non-object top-level input is rejected.
- Evidence normalization requires a deterministic timestamp and an alert reference;
  malformed arrays/objects raise `ZovarkValidationError` (fail-closed, never a
  partial package).
- Output directory is path-checked: the writer only writes a **fixed allowlist** of
  9 filenames (no path traversal from input content), and refuses to write into a
  directory that already contains unexpected files. The `investigation_memory` store
  is written to a **separate** `--memory-dir` (default `<output>/../proof-package-memory`),
  never into the package directory.
- No secrets, no hardcoded Nango IDs. The only credential-shaped string is the
  inherited placeholder `vault://placeholder/bootstrap` (a literal placeholder, not a
  secret).

## 6. Verification plan (Phases 3–4)

- **Determinism:** run twice → byte-identical 9-file output; commit both digests
  (`CONFORMANCE.md`).
- **Schema/validation:** `proof-package verify` (vendored `package_verifier`,
  re-derivation) exits 0 on the generated package.
- **Conformance:** run architecture `slice001` on the copied fixture (read-only) and
  `diff` all 9 artifacts → byte-identical (commit the comparison in `CONFORMANCE.md`).
- **Tests:** new pytest module + existing suite + the three CI checks all green.
- **Audit:** fresh subagents review the diff + this DESIGN.md for dangerous-direction
  defects; findings recorded in `AUDIT.md`.

## 7. Known inherited quirks (documented, classified FAIL-SAFE)

- `edr-handoff.json.rollback_plan.recovery_notes` hard-codes "given the LSASS access
  event" for any `isolate_host` even when the input has no LSASS evidence. This is a
  narrative inaccuracy **inherited from the slice001 oracle**; it does not affect the
  machine-checkable verdict/evidence/replay and matches the conformance oracle
  byte-for-byte (so it cannot be "fixed" here without breaking conformance).
  Classified **FAIL-SAFE** (misleading prose, never a wrong/unverifiable machine
  result) → NEXT_SLICES backlog.
