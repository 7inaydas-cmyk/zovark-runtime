# Architecture Query Checklist

Status: process checklist only. This document does not implement runtime
behavior.

Run this checklist before each future implementation PR. Each PR must cite the
architecture sources it checked and must use an exact `@codex review` trigger on
the final head before merge.

## Common Sources

Always check:

- `ARCHITECTURE_REPO_SOURCE.md`
- `INVARIANTS.md`
- `PHASE_PLAN.md`
- `docs/implementation-map.md`
- `docs/current-system-diagram.md`
- Architecture baseline:
  `7inaydas-cmyk/zovark-architecture@v3.2.5.0-baseline-consolidated`
- Architecture docs:
  - `docs/architecture-current-state.md`
  - `docs/context-compaction-memory.md`
  - `docs/contract-governance.md`
  - `contracts/README.md`
  - `docs/adr-status-table.md`

Every implementation PR must keep forbidden scope out unless that scope is
explicitly approved in the PR request.

## Before Phase 2B Storage

Architecture files to query:

- `docs/context-compaction-memory.md`
- `docs/contract-governance.md`
- `docs/implementation-map.md`
- `INVARIANTS.md`
- `PHASE_PLAN.md`

Contracts to check:

- `contracts/context-compaction-envelope-v1.schema.json`
- `contracts/memory-retrieval-request-v1.schema.json`
- `contracts/memory-retrieval-result-v1.schema.json`

Forbidden scope:

- storage-only unless explicitly approved;
- no retrieval service;
- no model context integration;
- no proof generation;
- no AlertForge contract or ingest;
- no benchmarks, customer-readiness, or outreach;
- no live EDR, SIEM, LLM, DB, Vault, control-plane, or network integrations;
- no signing, anchoring, legal, or compliance claims.

Required tests:

- lossless content storage;
- deterministic `memory_ref_id`;
- SHA-256 content hash correctness;
- content-size correctness;
- tamper/change detection;
- no model-visible content emitted by storage APIs;
- no live/network/database dependency imports unless explicitly scoped;
- existing semantic validator tests still pass.

Required review trigger:

```text
@codex review
```

The review must be on the latest pushed head.

## Before Phase 2C Retrieval

Architecture files to query:

- `docs/context-compaction-memory.md`
- `docs/contract-governance.md`
- `docs/architecture-query-checklist.md`

Contracts to check:

- `contracts/memory-retrieval-request-v1.schema.json`
- `contracts/memory-retrieval-result-v1.schema.json`

Forbidden scope:

- no model context integration unless separately approved;
- no proof generation;
- no AlertForge;
- no benchmarks or customer artifacts;
- no live integrations.

Required tests:

- bounded range request validation;
- capability-scope enforcement;
- audit record emission;
- denied and unavailable retrieval behavior;
- failure results carry no model-visible content;
- all returned ranges validated by semantic validators.

Required review trigger: exact `@codex review`.

## Before Phase 2D Envelope And Model-Visible Context

Architecture files to query:

- `docs/context-compaction-memory.md`
- `INVARIANTS.md`
- `docs/implementation-map.md`

Contracts to check:

- `contracts/context-compaction-envelope-v1.schema.json`
- `contracts/memory-retrieval-result-v1.schema.json`

Forbidden scope:

- no unbounded raw tool output in model context;
- no LLM summarization as canonical compaction;
- no proof package generation unless separately approved;
- no AlertForge, benchmarks, or customer artifacts.

Required tests:

- deterministic envelope generation;
- model-visible ranges and byte counts are explicit;
- envelope hash correctness;
- raw prompts, tool args, payloads, messages, notes, and hidden reasoning are
  not copied wholesale;
- what the model saw is recorded exactly.

Required review trigger: exact `@codex review`.

## Before Phase 3 Proof Generation

Architecture files to query:

- `docs/context-compaction-memory.md`
- architecture repo proof package docs at the baseline tag;
- `INVARIANTS.md`
- `PHASE_PLAN.md`

Contracts to check:

- Context Compaction Memory contracts;
- any proof package contracts imported for runtime use.

Forbidden scope:

- no V1 shape mutation;
- no implicit V2 generation;
- no Replay live calls;
- no customer, legal, compliance, signing, or benchmark claims.

Required tests:

- V1 shape preservation;
- explicit V2 behavior;
- offline Replay compatibility;
- proof records include memory refs, hashes, ranges, and retrieval refs when
  applicable.

Required review trigger: exact `@codex review`.

## Before Phase 4 AlertForge Contract And Ingest

Architecture files to query:

- `docs/implementation-map.md`
- `docs/external-standards-position.md`
- architecture repo AlertForge readiness docs at the baseline tag.

Contracts to check:

- proposed AlertForge input contract;
- unsafe-field rejection rules.

Forbidden scope:

- no AlertForge integration before a committed input contract/schema;
- no raw prompt, tool argument, output, payload, message, note, or hidden
  reasoning ingestion;
- no benchmark or customer claims.

Required tests:

- valid and invalid AlertForge fixtures;
- unsafe-field rejection;
- deterministic ingest behavior;
- no live external calls.

Required review trigger: exact `@codex review`.

## Before Benchmarks

Architecture files to query:

- `docs/implementation-map.md`
- architecture ADR status and benchmark governance docs at the baseline tag.

Contracts to check:

- benchmark fixture and result format if introduced.

Forbidden scope:

- no benchmark claims without benchmark evidence;
- no customer-readiness or outreach material.

Required tests:

- deterministic benchmark harness behavior;
- benchmark provenance;
- result reproducibility;
- no live production dependencies.

Required review trigger: exact `@codex review`.

## Before Customer-Readiness Or Outreach

Architecture files to query:

- `INVARIANTS.md`
- `PHASE_PLAN.md`
- `docs/implementation-map.md`
- benchmark evidence from Phase 6.

Contracts to check:

- customer-facing artifact policy if introduced.

Forbidden scope:

- no outreach before evidence-backed readiness;
- no legal admissibility, compliance certification, tamper-proof, production
  SOC readiness, or autonomous response claims unless implemented, tested, and
  approved in scope.

Required tests:

- evidence-backed readiness checks;
- fixture sensitivity checks;
- generated artifact lifecycle checks.

Required review trigger: exact `@codex review`.
