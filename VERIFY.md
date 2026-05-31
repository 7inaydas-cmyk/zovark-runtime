# VERIFY.md — Slice 2 baseline (re-derived from git/disk)

All facts below were observed by running the commands shown; nothing is taken from
handover. Slice 2's 8 schemas, decision note (`contracts/proof_package/README.md`),
and schema tests already landed on `main` via PR #32; this run re-verifies the baseline
and adds the required `VERIFY.md` + `AUDIT_SLICE2.md` governance artifacts.

## Repo state

| Fact | Command | Observed |
|---|---|---|
| runtime HEAD SHA | `git rev-parse HEAD` | `c41bb0ab09ad72aefec2e45d1a215b981354c959` (exit 0) |
| branch / origin sync | `git branch --show-current; git rev-parse origin/main` | `main`; `origin/main == c41bb0a` |
| `proof-package` + verify modules | `ls src/zovark_runtime/proof_package/{pipeline,verify}.py` | both present (exit 0) |
| CLI subcommands | `python -m zovark_runtime.cli --help` | `proof-package`, `proof-package-verify` present |
| Runtime PR #31 (V1) | `gh pr view 31` | **MERGED**, merge `83927ad8b86c5360f708a78413e8d5640b6392f2` |
| Architecture PR #66 (verifier re-derivation) | `gh -R …/zovark-architecture pr view 66` | **MERGED**, merge `98de15fd941d834a9ef605675043106e200ec204` |

## Double-run determinism + byte-identity

Commands (run into two clean dirs):
```
PYTHONPATH=src python3 -m zovark_runtime.cli proof-package \
  --input tests/fixtures/edr-sample-001.json --output /tmp/zovark-slice2-rt1 --tenant-id tenant-001   # exit 0
PYTHONPATH=src python3 -m zovark_runtime.cli proof-package \
  --input tests/fixtures/edr-sample-001.json --output /tmp/zovark-slice2-rt2 --tenant-id tenant-001   # exit 0
```
- Emitted **9** artifacts in each run: `investigation-tape.json`, `evidence-ledger.json`,
  `timeline.json`, `findings.json`, `verdict.json`, `edr-handoff.json`,
  `audit-chain-entry.json`, `replay-report.json`, `customer-report.md`.
- Combined SHA-256 over the 9 artifacts (concatenated in the order above):
  - run1 = `8749bf8af7a403110b3a622a22107cc0645e7fe8c455291da9c945e9513445a0`
  - run2 = `8749bf8af7a403110b3a622a22107cc0645e7fe8c455291da9c945e9513445a0`
  - **byte_identical = true** — this is the baseline hash the final Phase-4 re-run must match.

## proof-package-verify (semantic boundary)

```
PYTHONPATH=src python3 -m zovark_runtime.cli proof-package-verify --package /tmp/zovark-slice2-rt1
```
- exit code: **0**
- `status`: **verified**
- `failure_count`: **0**
- `findings_rederived_from_evidence`: **true**; `verdict`: `confirmed_malicious`;
  `evidence_entries_checked`: 3; `checks_passed`: 7.

### Evidence that verification re-derives evidence → findings → verdict

- **Evidence hashes re-checked from raw_content** — `proof_package/replay.py:225-233`
  recomputes `sha256_of_obj(entry["raw_content"])` and the `ev-` id and rejects on
  mismatch (run during `derive_replay_report` inside the verifier).
- **Findings re-derived FROM evidence** — `proof_package/verify.py:62`
  `derive_findings({"raw_evidence": ledger})`, requiring an exact match else
  `findings_not_derived_from_evidence` (`verify.py:64-67`).
- **Verdict re-derived FROM findings** — the vendored verifier re-derives the chain via
  `derive_handoff`/`derive_replay_report` (`package_verifier.py:214,250`), which call
  `derive_verdict` and reject a verdict that does not follow from the findings.

## Existing conventions (reused by Slice 2)

- Schema draft: `"$schema": "https://json-schema.org/draft/2020-12/schema"` (all
  `contracts/*.schema.json`).
- Validator/tests: `pytest.importorskip("jsonschema")` + `Draft202012Validator`
  (+ `RefResolver` for cross-`$ref` cases) — matched by `tests/test_proof_package_schemas.py`.
- Root-level governance docs already present: `DESIGN.md`, `CONFORMANCE.md`, `AUDIT.md`,
  `NEXT_SLICES.md` — `VERIFY.md`/`AUDIT_SLICE2.md` follow the same convention.

## Conclusion

`proof-package` and `proof-package-verify` are present, the baseline package verifies
(exit 0, `verified`, 0 failures, findings re-derived from evidence), and generation is
deterministic + byte-identical. No BLOCKER. Proceeding with Slice 2 governance artifacts.
