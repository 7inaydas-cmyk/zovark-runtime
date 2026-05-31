# SLICE 6 — EDR connector ingest boundary (only)

Target branch: `slices-5-8-staging` (**STAGE ONLY — do not merge to main**).
Commit message: `feat(slice6): EDR connector ingest boundary`

## Goal
Add a connector ingest boundary **without** contaminating the deterministic core with
network.

## Acceptance
- A connector fetches or normalizes one alert into the **exact** deterministic input
  shape (the shape `ingest.normalize_evidence` consumes).
- The deterministic proof-package pipeline remains **network-free**.
- Replay and the verifier remain **network-free**.
- Network exists only behind an explicit connector command/boundary.
- Missing credentials fail closed **at the connector boundary only**.
- Secrets via config/env only; **placeholders only** committed. Secret scan clean.
- Recorded fixtures let the deterministic path run and replay fully offline.

## Implementation guidance
- Scout existing connector/config patterns first. If none, implement: a connector
  interface; one EDR-style adapter using configurable endpoint/token **placeholders**; a
  recorded/mock transport for tests; a normalizer from provider alert JSON → deterministic
  input shape.
- Live fetch may exist only behind the explicit connector command. `proof-package`
  generation, `proof-package-verify`, and replay must NEVER perform network I/O.
- Do not touch ReviewOps. No dashboards/outreach.

## Tests
- Recorded connector fixture normalizes to the expected deterministic input shape.
- proof-package from the normalized fixture verifies offline.
- socket/network monkeypatch proves the deterministic pipeline does no network.
- socket/network monkeypatch proves replay/verifier do no network.
- Missing credentials fail closed at the connector boundary only.
- No hardcoded secrets/provider IDs; grep/secret-scan check passes.

## Independent audit
- Hunt lazy imports, fallback branches, HTTP clients, SDK calls, sockets. Prove network
  cannot happen in the proof-package or replay path. Confirm connector-only boundary.
  Confirm no real tokens/IDs.
