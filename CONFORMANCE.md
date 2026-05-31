# Conformance & Determinism Evidence — V1 Proof-Package Slice

Reproducible, artifact-backed evidence for goal criteria 3 (determinism), 4
(schema/validation), and 5 (conformance to the architecture slice001 oracle).
Regenerate with the commands below; the SHA-256 digests must match.

- Fixture: `tests/fixtures/edr-sample-001.json`
  (sha256 `b5c78e66fee8f11f5e224b9b3cb37d24510f58735d31d546a339eb7855b2060a`,
  byte-identical to architecture `samples/edr-sample-001.json`).
- Oracle: `architecture/zovark.slice001` at architecture `main`
  `d16935bd354b0e55984b7548e2ce4cca3385feea` (run read-only as the correctness oracle).

## Commands

```bash
# Runtime (run twice, to separate dirs):
PYTHONPATH=src python3 -m zovark_runtime.cli proof-package \
  --input tests/fixtures/edr-sample-001.json --output /tmp/rt1 --tenant-id tenant-001
PYTHONPATH=src python3 -m zovark_runtime.cli proof-package \
  --input tests/fixtures/edr-sample-001.json --output /tmp/rt2 --tenant-id tenant-001

# Oracle (read-only, in the architecture repo):
uv run python3 -m zovark.slice001 \
  --input samples/edr-sample-001.json --output /tmp/oracle --tenant-id tenant-001

# Offline re-derivation validation (exit 0 == valid):
PYTHONPATH=src python3 -m zovark_runtime.cli proof-package-verify --package /tmp/rt1
```

## 3. Determinism — byte-identical across two independent runs

| Run | Combined SHA-256 of the 9 artifacts |
|---|---|
| runtime run 1 | `8749bf8af7a403110b3a622a22107cc0645e7fe8c455291da9c945e9513445a0` |
| runtime run 2 | `8749bf8af7a403110b3a622a22107cc0645e7fe8c455291da9c945e9513445a0` |

**Result: byte-identical (deterministic).** Also enforced by
`tests/test_proof_package_pipeline.py::test_pipeline_is_deterministic_byte_identical`.

## 4. Validation — offline re-derivation, exit 0

`proof-package-verify` runs the vendored `package_verifier` (re-derives every
artifact from recorded inputs, re-checks all content hashes, re-runs the offline
replay): `status: verified`, `failure_count: 0`, `checks_passed: 7`,
`evidence_entries_checked: 3`, exit 0. (The slice001 proof-package contract has no
authority JSON Schemas; re-derivation is the authority's own, stronger validator —
see DESIGN.md §2.)

## 5. Conformance — byte-identical to the slice001 oracle

| Artifact | SHA-256 (runtime == oracle) |
|---|---|
| `investigation-tape.json` | `5715f118ae0d8d58f479310c9a565cdd62b3cdd80dad5d5cbbd831a386a6b92d` |
| `evidence-ledger.json` | `48a05974c2e3755522d0dfa8845a5186957adc57f1bb1bfe67852d72055fc405` |
| `timeline.json` | `932dc709cf8b45068988f52ec9ef1bec6bdfbf7faa0689f91655965e2a7749df` |
| `findings.json` | `14121544d3c02b9d6138dd9870852bbdabb9e7834a2429ec1c215fdeab2e70c7` |
| `verdict.json` | `701c7ca79ba4a094c5f881e3b42cf81a830c014678f5463e6339983b12589e93` |
| `edr-handoff.json` | `1bcfe1bcd271c9febeeb7494dd5da634a6c1a9158e3a9d080cef338672dd75c5` |
| `audit-chain-entry.json` | `1f4b9c8eb918851573d4271d7fe15f2c4bdbd394d68181b1152b113b66545427` |
| `replay-report.json` | `e7265f116f76079bc43c2c2348d09db5299bb30e691274533d28f1e892216ef2` |
| `customer-report.md` | `dd0d57ba41ea267123a40dc9357689bccd4ed2d6991ec1c0b7cef93801d68b9f` |

Combined: runtime `8749bf8a…3445a0` == oracle `8749bf8a…3445a0`.

**Result: all 9 artifacts byte-identical to the oracle** → trivially semantically
equivalent (same verdict `confirmed_malicious`, same 3 evidence items + hashes, same
replay record, all 9 present, schema-equivalent).

## Replay / safety invariants (in `replay-report.json`)

`no_live_llm_call: true`, `no_live_edr_call: true`, `mode: recorded_output`,
`model_versions_pin: []`, `verdict_recomputed: true`, evidence hashes re-verified
(3/3 passed). The deterministic path makes no network or model calls.
