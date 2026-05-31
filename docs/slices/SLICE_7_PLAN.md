# SLICE 7 PLAN — recorded live-AI investigation (STAGING)

## Design (safety-first, additive)
- The deterministic 9-artifact proof package stays **rule-based and byte-stable**
  (verdict.model_contribution = false, canonical hash unchanged). The model is NEVER
  verdict authority and CANNOT override deterministic findings.
- New additive layer `proof_package/ai_investigation.py`:
  - `ModelProvider` protocol + `FakeModelProvider` (deterministic, offline; output is a
    pure function of the prompt — used in CI; no network).
  - `record_ai_investigation(tape, provider, store)` — **record-time only**: builds a
    deterministic prompt from recorded evidence, calls `provider.complete` (the ONLY model
    call), records model_id/version/prompt/prompt_hash/output/output_hash/model_contribution
    losslessly, and **anchors the model output bytes in the investigation_memory store**
    (content-addressed). model_contribution = True (a model produced this note).
  - `replay_ai_investigation(recorded, store)` — **offline**: re-reads the anchored output
    from the store, recomputes prompt/output hashes, and requires them to match the
    recorded hashes; asserts `is_verdict_authority == False`. **Never** accepts or calls a
    provider (passing a provider raises). Fails closed on any hash/tamper mismatch.
- CLI: `ai-investigate --package <dir> --output <ai.json> [--memory-dir]` (record-time,
  fake provider) and `ai-replay --recorded <ai.json> --memory-dir <dir>` (offline).

## Invariants
- Replay never calls a model or network (enforced: replay takes no provider; reads only
  the store + recorded artifact). Monkeypatch-proven.
- Model output recorded losslessly with hashes + store anchor; tamper → fail closed.
- Deterministic verdict unchanged with or without the AI layer (model not authority).
- `model_versions_pin` recorded; `no_live_llm_call`/`no_live_edr_call` true on replay.
- Stage only; canonical 9-artifact hash unchanged.

## Tests
record produces hashes + store anchor; replay re-validates offline; replay refuses a
provider; tamper output / tamper hash → fail closed; provider monkeypatched to explode is
never called during replay; proof-package verdict identical with/without AI; two record
runs byte-identical (fake provider).

## Independent-audit disposition
PASS, zero DANGEROUS-DIRECTION. Closed: F2 unused import removed; replay now also calls
store.verify() (store-layer re-hash) for defense in depth. Documented FAIL-SAFE (F1):
`replay_ai_investigation` attests recorded-artifact integrity + store anchor, NOT provenance
against the live tape — a store-write attacker could forge a self-consistent AI note, but
the model output is provably NEVER verdict authority, so it cannot alter any verdict,
finding, or the canonical package. Threat model assumes store-write integrity.
