# Zovark Runtime

Status: greenfield runtime Phase 2B lossless storage substrate.

This repository is the starting point for the future Zovark runtime. Phase 1
adds a deterministic local monolith skeleton for status reporting only. Phase
2A adds Context Compaction Memory semantic validators. Phase 2B adds lossless
local `investigation_memory` storage only.

No runtime product exists yet.

## What Exists

- Contract snapshot copied from
  `7inaydas-cmyk/zovark-architecture` at tag
  `arch-v4.1-runtime-phase0`.
- Phase 0 invariants for proof, Replay, and Context Compaction Memory.
- Feature lifecycle placeholders for planned runtime work.
- Static validation scripts for the contract manifest and invariant text.
- `zovark-runtime status` and `zovark-runtime doctor` skeleton commands.
- Standard-library Context Compaction Memory semantic validators.
- Lossless local `investigation_memory` storage substrate.

## What Does Not Exist

- No full investigation_memory runtime.
- No memory retrieval service.
- No model context integration.
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

The Context Compaction Memory validators are domain helper functions. They are
not storage, retrieval, model-context, proof-generation, or runtime enforcement.

The investigation_memory storage substrate stores exact local bytes and
deterministic metadata for verification. It is not a retrieval service, does not
produce model-visible output, and does not generate proof packages.

## Architecture Source

See [ARCHITECTURE_REPO_SOURCE.md](ARCHITECTURE_REPO_SOURCE.md).

## Architecture Map

See [docs/implementation-map.md](docs/implementation-map.md) for the current
runtime implementation map and [docs/current-system-diagram.md](docs/current-system-diagram.md)
for consolidated system diagrams.

Those documents are maps only. They do not change runtime implementation,
storage, retrieval, model context integration, proof generation, AlertForge,
benchmarks, customer-readiness, or outreach scope.
