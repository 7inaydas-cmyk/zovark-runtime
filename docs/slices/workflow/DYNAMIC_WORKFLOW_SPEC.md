# Zovark Slices 3–8 — Dynamic Workflow Operating Manual

This is the durable source of truth for the slices 3–8 build. The `/goal` that drives
it is short and only says: *"Execute the Zovark slices 3–8 workflow from
`docs/slices/workflow/`."* All operating detail lives here and in the sibling files.

## Repos & authority
- `zovark-architecture` = canonical authority/oracle. **READ-ONLY** unless explicitly
  authorized. Touching it → BLOCKER (tripwire T3).
- `zovark-runtime` = product/runtime. All implementation happens here.
- `zovark-reviewops` = closed infra. **Do not modify or expand** (tripwire T4).
- This is Zovark's deterministic rebuild, **not** HYDRA/Zovark_swami. Do not import
  Temporal/Go/Postgres/React-dashboard/Ollama/live-codegen/HYDRA assumptions.

## Honest framing (verbatim)
- Say: deterministic, replayable, byte-conformant to the oracle, tamper fails closed.
- Do NOT say: independently verified / independently corroborated.
- Honest claim: verdicts are deterministically re-derivable from recorded evidence
  under stated rules; tamper fails closed. We do not claim the rules are independently
  proven correct.

## Non-negotiable invariants (never weaken)
1. Deterministic verdict derivation — no wall-clock, randomness, network, unordered
   iteration, filesystem metadata, or env-dependent behavior in derivation.
2. Full-chain verifier re-derivation: evidence hashes → findings FROM evidence →
   verdict FROM findings. Fail closed on mismatch/tamper/malformed/uncertainty/forgery.
3. Replay never re-runs a model; validates recorded artifacts only.
4. No live LLM/model/network in deterministic/replay/verdict-decision path. (Slice 7
   record-time model use is the only exception, recorded losslessly + replayed offline.)
5. Schemas are necessary-not-sufficient; `proof-package-verify` is the semantic authority.
6. Confirm-malicious-only is the honest current boundary. No benign/notify-only verdicts.
7. Fail closed on malformed input — no partial packages, no uncaught traceback as product
   behavior.
8. No customer/product/production/compliance/SLA/readiness/benchmark/dashboard/AlertForge
   claims.
9. No real secrets or hardcoded integration IDs — placeholders/config/env only.
10. No architecture or ReviewOps modification.

## Model / agent topology (safe width)
- Use the cheapest/fastest model (e.g. Haiku) for **read-only** scout/test/audit workers
  where model routing is available; reserve the stronger model for synthesis,
  implementation decisions, and merge-gate judgment.
- Cap parallel read-only workers at **8**. Do not spawn hundreds.
- **Never parallelize code-writing builders.** The chain is linear: 3→4→5→6→7→8. Only one
  builder edits product code at a time.
- Parallelize only read-only work: scouting, test discovery, mutation-test design, audit
  checks, secret/network scans, docs review.

## Roles (see AGENT_*.md)
Controller, Builder, Repo Scout, Test/Repro, Independent Auditor, Reporter. The
Independent Auditor must not write `src/`/implementation; it may add audit docs + tests.

## Branch / merge policy
- Start on `main`.
- Slices **3 and 4** may be committed/merged to `main` after: green implementation +
  full suite + deterministic double-run + `proof-package-verify` pass + self-audit
  (zero unresolved DANGEROUS-DIRECTION) + independent audit (zero unresolved
  DANGEROUS-DIRECTION).
- After Slice 4 is green on `main`, create branch `slices-5-8-staging` from `main`.
- Implement Slices **5, 6, 7, 8** on `slices-5-8-staging`. **Do NOT merge 5–8 to main.**
- `main`'s combined 9-artifact hash must not change for slices 5–8.
- Write `docs/slices/REVIEW_REQUIRED.md` with exact morning operator decisions.
- Staging rationale: Slice 5 changes report bytes/baseline; Slice 6 adds a
  network-adjacent connector boundary; Slice 7 adds record-time model I/O; Slice 8 adds
  runtime schema/proof-status integration. All require operator review before main.

## Per-slice loop (slices 3..8)
1. Re-read `NEXT_SLICES.md` and re-derive repo state from git/disk (trust nothing).
2. Write `docs/slices/SLICE_<n>_PLAN.md`.
3. Builder implements the smallest change meeting acceptance; reuse existing code paths;
   no parallel verifier/verdict engine.
4. Add tests for acceptance + fail-closed behavior.
5. Run targeted tests + full suite/check (`uv run ... pytest tests/ -q` + the 3 Phase-0
   scripts).
6. Run `proof-package` twice + `proof-package-verify` (+ replay/connector/AI tests per
   slice).
7. Write `docs/slices/VERIFY_SLICE_<n>.md` (commands, exit codes, hashes, verifier status).
8. Write `docs/slices/AUDIT_SLICE_<n>.md` (self-audit).
9. Independent auditor writes `docs/slices/INDEP_AUDIT_SLICE_<n>.md` (mutation-tests guards;
   FAIL-SAFE vs DANGEROUS-DIRECTION; unsure = DANGEROUS-DIRECTION).
10. Fix every DANGEROUS-DIRECTION before advancing.
11. Commit one logical commit (see slice specs for messages).
12. Append `docs/slices/SLICES_PROGRESS.md` and update `STATE.json`.

## Baseline (pre-flight, recompute — do not trust)
- Two clean generations of `tests/fixtures/edr-sample-001.json` must be byte-identical;
  record the combined SHA-256.
- `proof-package-verify` must pass (status verified, failure_count 0,
  findings_rederived_from_evidence true) and reject a shape-valid forgery.
- Last recorded canonical combined hash:
  `8749bf8af7a403110b3a622a22107cc0645e7fe8c455291da9c945e9513445a0` (RECOMPUTE; if it
  differs unexpectedly → tripwire T10/BLOCKER).

## Context-limit protocol
If context gets tight: finish the current atomic step if safe; commit safe complete work
or revert unsafe partial work; write `docs/slices/CONTINUATION.md` (branch, HEAD,
clean/dirty, completed slices, current slice+phase, commands, passing/failing tests,
exact blocker, next smallest safe action, exact next `/goal`); append SLICES_PROGRESS.md;
stop. Never fake done.

## How this maps onto the Claude Code Workflow tool
The `Workflow` tool (Dynamic Workflows) IS available. It is used **only** for the
read-only parallel fan-out (scouts/auditors/scans), capped at 8 — see
`zovark_slices_3_8_workflow.js`. Code-writing (Builder), git operations, and merge-gate
decisions are **controller-owned in the main loop** and are deliberately NOT autonomous
inside the workflow script, because builders must be serialized and merge/staging gates
require judgment + operator approval.
