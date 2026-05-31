# SLICE 7 — recorded live-AI investigation with offline replay

Target branch: `slices-5-8-staging` (**STAGE ONLY — do not merge to main**).
Commit message: `feat(slice7): recorded live-AI investigation replay`

## Goal
Introduce record-time model assistance while keeping replay and verdict deterministic.

## Acceptance
- A model may be called **at record time only**, and only when explicitly requested.
- Every model input/output is recorded losslessly (investigation_memory or repo-standard
  equivalent) **with hashes**.
- Replay re-validates recorded artifacts and **never** calls a live model or network.
- Model version metadata recorded (`model_versions_pin` if the field exists, else
  equivalent).
- `no_live_llm_call` true on replay if the field exists, else equivalent replay proof.
- `model_contribution` surfaced **honestly** per finding/verdict — no longer always
  false when the model contributed.
- The verdict remains deterministic from recorded I/O.
- Two record→replay runs produce byte-identical replay validation, with committed hashes.
- **Model output is recorded evidence, never verdict authority.** It cannot override the
  deterministic verifier's findings.
- A fake/deterministic provider is used in CI; no live model call in CI.

## Implementation guidance
- Scout existing `investigation_memory`, model metadata, `replay-report`,
  `no_live_llm_call` fields, fake-provider patterns. Implement a provider abstraction
  only if needed: a deterministic fake/fixture provider for tests; an optional local
  adapter only if repo conventions support it.
- The record-time command may call the model only on explicit request. Replay must
  reject any attempt to call the provider/network. Hash all model inputs/outputs.
  Preserve deterministic verdict derivation.

## Tests
- Record-time fake provider records exact input/output + hashes.
- Replay validates recorded model I/O without calling the provider.
- Replay fails if a model-output hash is tampered.
- Replay fails (or refuses) if code attempts a live model/network call.
- `model_contribution` true only where recorded model evidence contributes.
- Deterministic two-run replay hashes match.
- `proof-package-verify` still rejects a semantic forgery.

## Independent audit
- Monkeypatch the provider to explode during replay → replay must not call it.
  Monkeypatch network/socket during replay → no call allowed. Tamper a model-output hash
  → replay fails closed. Try to make model output override deterministic findings → must
  fail or be ignored. Confirm no production-readiness AI claims.
