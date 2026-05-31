# INDEP_AUDIT_SLICE_6 — EDR connector ingest boundary (independent, read-only)

Branch `slices-5-8-staging` (NOT merged to main). Auditor ran read/execute only; no `src/` modified.

## Verdict: PASS — no DANGEROUS-DIRECTION findings.

The connector is a clean ingest boundary. The deterministic proof-package pipeline and
replay/verify paths remain fully network-free; network capability exists only behind an
explicitly-invoked `LiveEdrConnector.fetch()` with a lazy `urllib.request` import. Fail-closed
on missing creds and malformed payloads. No hardcoded secrets. The verifier is unchanged and
still rejects forgery. Determinism holds.

## Checks (all PASS)

| # | Check | Result | Repro |
|---|---|---|---|
| 1 | Deterministic pipeline network-free | PASS | Monkeypatched `socket.socket`+`create_connection`+`getaddrinfo` to raise, ran `run_proof_package` on connector output → `confirmed_malicious`, no network attempt. |
| 1 | Replay/verify network-free | PASS | Same socket-block; `verify_proof_package_strict` (re-derives + offline replay) → `verified`. |
| 1 | No network import anywhere in proof_package | PASS | `grep -rE "import (socket|urllib|http)|requests|urlopen"` across whole `proof_package/` → NONE. Only ref to connectors outside `connectors/` is `cli.py:95` importing `RecordedEdrConnector` (offline). No path reaches `LiveEdrConnector`/urllib. |
| 2 | Lazy network import | PASS | After `import zovark_runtime.connectors.edr_connector`: `urllib.request`, `socket`, `ssl` NOT in `sys.modules`. (`urllib.parse` IS loaded, but by stdlib `pathlib`, not the connector — it is pure string parsing, zero network capability.) |
| 3 | Fail-closed (no creds / endpoint-only / token-only / empty-string env) | PASS | All four raise `ConnectorError` before any import of `urllib.request`. |
| 3 | Normalize fail-closed on malformed | PASS | not-a-dict, missing alert_id/host/timestamp, detections-not-list, detection-not-dict, unknown kind, missing kind → all raise `ConnectorError`. Never partial/garbage output. |
| 4 | No hardcoded secrets/provider IDs/keys | PASS | Connector references only env names `ZOVARK_EDR_ENDPOINT`/`ZOVARK_EDR_TOKEN` and `Bearer {token}` template. Fixture uses RFC-5737 doc IP `203.0.113.60` + `.example` host; no real IDs/keys. |
| 5 | Verifier not weakened; forgery rejected | PASS | Connector only emits input JSON; touches no verifier code. Tampered `verdict.json` → verify raises `extracted_view_mismatch`. |
| 5 | Determinism | PASS | `normalize_provider_alert` twice → byte-identical. |
| 6 | Crafted detection / injection | PASS | Detection of `kind:process` carrying its own `process_events`/`network_events` fields nests them inside the event object at `process_events[0].raw_content`; they do NOT leak to top-level event arrays (ingest's `_EVENT_ARRAY_KEYS` split is top-level only) → no double-count/pollution. `host`/`alert_id` never reach filesystem paths (output filenames are a fixed constant list in `writer.py`) → no path traversal. |
| 7 | Architecture / ReviewOps / main untouched | PASS | Slice-6 working-tree delta is exactly: `cli.py` (+edr-connect), new `connectors/`, fixture, test. No proof_package source, no architecture, no ReviewOps. Not merged to main. |

E2E run succeeded: `edr-connect` → `proof-package` (verdict `confirmed_malicious`, replay `succeeded`) → `proof-package-verify` (status `verified`, 7 checks, 0 failures).

## FAIL-SAFE observations (not blocking)

- **Live network path uncovered by CI**: `LiveEdrConnector.fetch()` network branch is `# pragma: no cover - live only`; never exercised (no creds in CI). By design — covered by fail-closed-without-creds test + lazy-import isolation. FAIL-SAFE.
- **No SSRF/scheme allowlist on live endpoint** (`edr_connector.py:110-113`): `urllib.request.urlopen` is handed the raw `ZOVARK_EDR_ENDPOINT` with no scheme restriction (`file://`, `ftp://`, `gopher://` not blocked). Classified FAIL-SAFE because (a) the endpoint is operator-supplied config, not attacker-controlled provider data, and (b) this path is entirely off the deterministic/replay pipeline. Worth a scheme allowlist (`https://` only) when the live path is hardened, but not a slice-6 dangerous direction.
- **No input-size bound in connector** (`edr_connector.py:61-69`): 5000 detections map to 5000 events; the connector imposes no cap. FAIL-SAFE — bounding is a downstream ingest/pipeline concern and does not affect determinism or fail-closed behavior; no oversized *deterministic-shape corruption* observed.

## Tools/repros used
- Socket-block monkeypatch over full pipeline + verify (strongest network-on-deterministic-path check).
- `sys.modules` import-time diff + `python3 -X importtime` to attribute `urllib.parse` to `pathlib`.
- `grep -rE` for network imports across all of `proof_package/` and for connector refs across `src/`.
- Malformed/fail-closed matrix; determinism double-run; tampered-verdict forgery; crafted nested event-array-key detection; filesystem-path grep on `writer.py`/`pipeline.py`.
- Note: `pytest` not installed in env; equivalent assertions reproduced directly via interpreter (all passed).
