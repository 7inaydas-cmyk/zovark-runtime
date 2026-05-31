# SLICE 6 PLAN — EDR connector ingest boundary (STAGING)
Additive: `connectors/edr_connector.py` (`normalize_provider_alert` pure/offline;
`RecordedEdrConnector` disk-only; `LiveEdrConnector` the only network site, behind explicit
fetch, creds via env, fail-closed if missing). CLI `edr-connect` normalizes a recorded
provider alert to the deterministic input shape (offline). Deterministic pipeline + replay/
verify stay network-free (the proof_package package imports no network module; live transport
is lazily imported only inside LiveEdrConnector.fetch). Recorded fixture edr-provider-001.json
runs fully offline. No secrets (placeholders/env only). Stage only.
