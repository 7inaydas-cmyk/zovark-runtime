# VERIFY_SLICE_6 — EDR connector (STAGING)
- `edr-connect --recorded edr-provider-001.json` exit 0 → deterministic input; pipeline
  from it generates + `proof-package-verify` exit 0.
- Connector tests `tests/test_edr_connector.py` → 7 passed: normalize shape; proof-package
  + verify pass under a socket-blocking monkeypatch (network-free); recorded connector
  offline; LiveEdrConnector fails closed without creds; malformed provider fails closed;
  no `import socket/urllib/http`/`requests` in pipeline.py/verify.py.
- Full suite → 314 passed. Phase-0 PASS. Secret scan: no hardcoded secrets/provider IDs
  (creds via ZOVARK_EDR_ENDPOINT/ZOVARK_EDR_TOKEN env only).
- Deterministic core + replay/verify unchanged; main untouched (staging only).
