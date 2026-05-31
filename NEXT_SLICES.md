# Next Slices — Backlog Toward the Full Product

The V1 slice (this PR) delivers a deterministic, replay-validatable, approval-ready
9-file proof package from one static EDR alert JSON, semantically and byte-identically
conformant to the architecture `slice001` oracle, with a strict offline verifier that
re-derives every artifact (including findings) from the recorded evidence.

Each slice below has **concrete, artifact-backed acceptance criteria** suitable for
chaining the next `/goal`. They are **not** built here. Ordering is roughly by
dependency. None may weaken determinism, the no-network/no-live-LLM replay path, or
proof-status semantics.

---

## Slice 2 — Authority JSON Schemas for the proof-package contract
**Why:** The 9 artifacts currently have no standalone JSON Schemas; validation is by
re-derivation. Explicit schemas make the contract checkable independently and in CI.
**Acceptance:**
- A JSON Schema per artifact (`investigation-tape`, `evidence-ledger`, `timeline`,
  `findings`, `verdict`, `edr-handoff`, `audit-chain-entry`, `replay-report`) committed
  under `contracts/proof_package/`, with provenance.
- Every artifact the V1 command emits validates against its schema (CI test, exit 0).
- Schemas are consistent with — not a replacement for — `proof-package-verify`
  re-derivation; a test asserts both agree.
- Decision recorded: author in `architecture` (authority) vs vendor into runtime.

## Slice 3 — ADR-0046 verdict contract bridge (`derive_verdict` / `validate_replay_record`)
**Why:** Runtime's existing `verdict_derivation.derive_verdict` and
`replay_validation.validate_replay_record` serve the ADR-0046 `verdict_input` →
`verdict_envelope` / `replay_record` contract, which is distinct from slice001's
proof-package contract. V1 deferred them.
**Acceptance:**
- A documented mapping from the proof-package tape to a `verdict_input`, and an
  emitted `verdict_envelope` that validates against `contracts/verdict_envelope.schema.json`.
- `validate_replay_record` runs (fail-closed, offline, hash-based) against an emitted
  `replay_record` and passes; a tampered record fails.
- Determinism preserved (twice-run byte-identical); committed hashes.
- Clear statement of how the two contracts relate (proof-package vs ADR-0046) — no
  silent divergence.

## Slice 4 — Multi-alert / multi-evidence inputs
**Why:** V1 ingests one alert with simple event arrays. SOC inputs bundle many events
and multiple alerts.
**Acceptance:**
- The command accepts an input with N alerts / many events of all five source types
  (process, network, credential_access, lateral_movement, network_flow) and emits a
  conformant package (the richer `slice001` rule paths, e.g. LSASS/SMB, exercised).
- Deterministic + strict-verify clean on at least 3 distinct multi-event fixtures.
- Evidence ordering and dedup are deterministic; documented.

## Slice 5 — Richer, fully evidence-backed SOC report
**Why:** Fix the inherited FAIL-SAFE quirk: the `isolate_host` recovery note hard-codes
"given the LSASS access event" even without LSASS evidence. The report should make no
claim not backed by recorded evidence.
**Acceptance:**
- Every sentence in `customer-report.md` and `edr-handoff.json` narrative fields is
  traceable to a recorded evidence item (a test asserts no un-evidenced claim strings).
- Because this changes bytes, it forks from strict slice001 byte-conformance: record a
  new conformance baseline (semantic equivalence on verdict/evidence/replay retained;
  document the intentional divergence and why).
- No readiness/SLA/compliance claims introduced.

## Slice 6 — Real EDR connector (ingest boundary only)
**Why:** Move from a static JSON file to a real EDR source, while keeping the
deterministic core offline.
**Acceptance:**
- A connector fetches/normalizes one alert into the exact V1 input shape behind a
  boundary; **the deterministic pipeline and replay remain network-free** (a test
  asserts no network in the pipeline/replay path).
- Secrets via deployment config only; placeholders in the repo; secret scan clean.
- Recorded fixtures let the deterministic path run and replay fully offline.

## Slice 7 — Live-AI-assisted investigation with recorded replay
**Why:** The product thesis: AI may assist, but the result must be replayable without
re-running a model.
**Acceptance:**
- An investigation step may call a model **at record time only**; every model
  input/output is recorded losslessly (investigation_memory) with hashes.
- Replay re-validates recorded artifacts and **never** calls a live model or network
  (enforced + tested); `model_versions_pin` populated; `no_live_llm_call: true` on replay.
- `model_contribution` is surfaced honestly per finding/verdict (no longer always
  `false`), and the verdict remains deterministically replayable from recorded I/O.
- Two record→replay runs produce byte-identical replay validation; committed hashes.

## Slice 8 — Runtime-enforced schemas + proof-loop status integration
**Why:** Move schemas from "copied, not enforced" to enforced; optionally import the
ADR-0053 proof-loop completion authority.
**Acceptance:**
- Pipeline enforces the relevant contract schemas at runtime (not just in tests).
- If/when criteria are met, `proof-status` reflects the architecture-owned
  `runtime_proof_loop` authority **only** per ADR-0053 (no weakening of its semantics).
- All Phase-0 checks + suite remain green.

---

**Out of scope for all of the above (carried from the goal):** AlertForge, dashboards,
benchmarks, outreach; any customer/product/production/compliance/SLA/readiness claim;
live LLM or network in the deterministic/replay path; modifying the architecture
authority repo; expanding the closed ReviewOps lane.
