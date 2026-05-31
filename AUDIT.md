# Phase 4 — Independent Adversarial Audit

Fresh subagents were given **only** the diff + DESIGN.md (not the build reasoning)
and tasked to find dangerous-direction defects, security issues, and DESIGN
mismatches. Every finding below is classified **DANGEROUS-DIRECTION** (could yield a
wrong/unverifiable result presented as correct, or a security escape) or
**FAIL-SAFE** (worst case is an over-refusal/crash with no integrity loss). All
DANGEROUS-DIRECTION findings were fixed and re-audited. **Zero unresolved
dangerous-direction findings remain.**

Bound discipline: the audit ran 4 adversarial passes (1 initial round of 3
parallel auditors + 3 confirmation passes). The **core integrity property** — the
strict verifier's soundness, byte-exact conformance, and determinism — was sound
from the first fix and held under every subsequent pass. The residual findings were
all instances of a single, converging class (symlink-escape on the storage write
path), closed at the root by a full-path containment guard. No foundational design
flaw was found; no BLOCKER.

## Round 1 — three parallel auditors (correctness, security, design-fidelity)

| # | Finding | Class | Resolution |
|---|---|---|---|
| D1 | `proof-package-verify` re-derived the verdict/handoff/audit/replay chain but **never re-derived `findings` from the evidence** → a self-consistent package with fabricated/suppressed findings (e.g. a real malicious alert downgraded to `benign`) verified clean. Independently reproduced by two auditors (false-positive AND false-negative). Inherited from the oracle's verifier. | **DANGEROUS-DIRECTION** | Added runtime-original `proof_package/verify.py` (`verify_proof_package_strict`): after the vendored verifier hash-verifies the evidence, re-derive findings from the evidence ledger and require an exact match. CLI uses it. Root-invariant fix → the whole chain is now re-derived from evidence. Regression test: forgery accepted by vendored verifier, rejected by strict. |
| D2 | Output writer followed symlinks → arbitrary file overwrite outside the output dir via a pre-placed symlink named like an artifact. | **DANGEROUS-DIRECTION** (security) | Added a runtime-layer symlink guard (`pipeline._assert_output_dir_safe`) refusing a symlinked output dir or any symlinked target artifact. |
| F1 | `NaN`/`Infinity` input → uncaught `ValueError` (not the documented `ZovarkValidationError`). | FAIL-SAFE | Hardened input loader (`pipeline._safe_load_input`): reject non-finite via `parse_constant`. |
| F2 | Deeply-nested input → uncaught `RecursionError`. | FAIL-SAFE | Loader enforces ≤8 MiB, ≤64-depth, UTF-8, object top-level → `ZovarkValidationError`. |
| (design) | DESIGN named `proof-package verify` (actual: `proof-package-verify`); default memory dir mis-stated. | cosmetic | DESIGN corrected. |
| (overstatement) | DESIGN/CONFORMANCE said verify "re-derives every artifact" while findings were not re-derived. | (subsumed by D1) | True after D1; wording made precise. |

Design-fidelity auditor independently confirmed: vendoring is byte-verbatim (13
modules), determinism/conformance real, the inherited "LSASS" recovery-note quirk is
FAIL-SAFE (free-text only; not in any hash, verdict, evidence, or replay).

## Round 2 — confirmation pass

| # | Finding | Class | Resolution |
|---|---|---|---|
| 1 | The D2 symlink guard covered the package dir but not the `investigation_memory` store; a dangling symlink at a content-addressed leaf path made `store.put_bytes` write through it. | **DANGEROUS-DIRECTION** (file-escape) | Added a symlink check on the store's leaf content/metadata paths. |
| 2 | `1e999` → `float('inf')` bypassed `parse_constant`; huge integer literals raised an uncaught `ValueError` from `json.loads`. | FAIL-SAFE | Loader catches `ValueError`/`RecursionError` and rejects non-finite floats post-parse. |
| — | D1 strict verifier: **could not be broken** (reorder/drop/duplicate/extra-field/no_findings_flag forgeries all rejected). | — | held |

## Round 3 — confirmation pass

| # | Finding | Class | Resolution |
|---|---|---|---|
| 1 | The leaf-only store symlink guard missed a symlinked **intermediate** dir (`objects/<2hex>`); `mkdir` followed it. | **DANGEROUS-DIRECTION** (file-escape) | Replaced with `store._assert_no_symlink_escape`, walking **every** path component under `root_dir`. |
| 2 | Lone UTF-16 surrogate in a JSON string crashed at canonicalization (`UnicodeEncodeError`). | FAIL-SAFE | Loader rejects non-UTF-8-encodable strings and object keys. |
| — | D1 strict verifier: **held again**; conformance + determinism re-confirmed. | — | held |

## Round 4 — final confirmation pass

| # | Finding | Class | Resolution |
|---|---|---|---|
| 1 | The per-component store guard checked paths **under** `root_dir` but not whether `root_dir` **itself** was a symlink → a symlinked store root still wrote through (low/moderate: content-addressed, input-derived bytes, no overwrite, does **not** affect proof soundness — verify never reads the store). The last uncovered component of the symlink class. | **DANGEROUS-DIRECTION** (file-escape) | `run_proof_package` now refuses a symlinked memory dir, mirroring the output-dir guard. Symlink class fully closed (root + intermediate + leaf), verified across all vectors. |
| 2 | Verify-side `_load_json` didn't bound depth → `RecursionError` traceback on a maliciously deep package file (never emits "verified"). | FAIL-SAFE | `verify.py` maps `RecursionError`/`ValueError` from the vendored verifier and its own loader to `ZovarkValidationError` (vendored `package_verifier` kept byte-verbatim). |
| — | Core integrity (strict verifier soundness), byte-exact oracle conformance, determinism, no secrets/network/eval/pickle/subprocess, no swallowed-exception-to-success: **all confirmed sound.** | — | — |

## Deferred FAIL-SAFE items (→ NEXT_SLICES.md)

- Inherited "LSASS access event" recovery-note in `edr-handoff.json` for any
  `isolate_host` even without LSASS evidence (free-text only; matches the oracle
  byte-for-byte, so cannot change here without breaking conformance).
- `investigation_memory` records evidence before a later build step may abort,
  leaving content-addressed objects on disk (harmless, content-addressed).
- The slice001 proof-package contract has no standalone authority JSON Schemas;
  re-derivation is the validator (author JSON Schemas as a future slice).

## Status

**Zero unresolved DANGEROUS-DIRECTION findings.** All FAIL-SAFE items are either
fixed or documented and deferred. 260 tests pass; 9 artifacts byte-identical to the
oracle; 13 vendored modules byte-identical to the oracle source (modulo import path).
