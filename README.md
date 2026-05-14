# Zovark Runtime

Status: greenfield runtime Phase 1 skeleton.

This repository is the starting point for the future Zovark runtime. Phase 1
adds a deterministic local monolith skeleton for status reporting only.

No runtime product exists yet.

## What Exists

- Contract snapshot copied from
  `7inaydas-cmyk/zovark-architecture` at tag
  `arch-v4.1-runtime-phase0`.
- Phase 0 invariants for proof, Replay, and Context Compaction Memory.
- Feature lifecycle placeholders for planned runtime work.
- Static validation scripts for the contract manifest and invariant text.
- `zovark-runtime status` and `zovark-runtime doctor` skeleton commands.

## What Does Not Exist

- No investigation_memory implementation.
- No memory storage service.
- No memory retrieval service.
- No investigation execution.
- No planner, executor, or assessor runtime.
- No sandbox EXECUTE implementation.
- No AlertForge integration.
- No benchmark harness.
- No customer-readiness or outreach material.
- No live EDR, SIEM, LLM, DB, Vault, control-plane, or network integration.
- No signing, anchoring, SLSA, in-toto, legal, or compliance scope.

## Validation

Run:

```bash
python scripts/check_contract_manifest.py
python scripts/check_invariants.py
python scripts/check_no_unbounded_model_context.py
```

These checks are Phase 0 static checks. They are not runtime enforcement.

## Architecture Source

See [ARCHITECTURE_REPO_SOURCE.md](ARCHITECTURE_REPO_SOURCE.md).
