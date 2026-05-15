# Local Inference Position

Status: documentation only. This file does not implement RamaLama, local
inference, model routing, model context integration, live LLM calls, or runtime
model execution.

## RamaLama

RamaLama is not implemented in `zovark-runtime`.

RamaLama is not implemented in the current architecture baseline
`arch-v4.1-runtime-phase0`.

No live LLM integration exists in `zovark-runtime`. No model context integration
exists yet.

RamaLama may be considered later only as a local inference/provider candidate.
Any future RamaLama or local inference work must be a separate
architecture-gated PR.

## Required Future Constraints

Future local inference must respect Context Compaction Memory:

- no model receives unbounded raw tool output;
- oversized output is stored losslessly before model exposure;
- model-visible context is deterministic envelope plus `memory_ref_id`;
- bounded retrieval is audited and capability-scoped; and
- what the model actually saw is recorded.

Future local inference must not create customer, benchmark, legal,
compliance-certification, production SOC readiness, signing, anchoring, SLSA, or
in-toto claims by itself.
