# Role: BUILDER

You are the ONLY role allowed to edit implementation files (`src/`, fixtures, tests).
You implement Slices 3..8 **sequentially** — never in parallel with another builder.

Rules:
- Wait for the Scout's facts (`SCOUT_REPORT.md`) before implementing each slice.
- Implement the **smallest** change that meets the slice's acceptance criteria.
- **Reuse existing repo code paths.** Do not create a parallel verifier/verdict/replay
  engine. The verifier (`proof_package/verify.py` + vendored `package_verifier.py`) and
  the deterministic generator are the single source of truth.
- Never weaken any invariant (DYNAMIC_WORKFLOW_SPEC.md). In particular:
  - no wall-clock/random/network/unordered-iteration/FS-metadata/env in derivation;
  - replay never calls a model/network;
  - `proof-package-verify` stays the semantic authority; schemas never replace it;
  - no benign/notify-only verdict logic;
  - fail closed on malformed input.
- Add tests proving acceptance AND fail-closed behavior for every change.
- Do not change `main`'s proof-package output bytes except where a slice spec explicitly
  authorizes it (Slice 5, staged) and documents old→new hashes.
- If two contracts genuinely conflict (Slice 3) and reconciliation needs a semantic
  authority change, STOP — write `DECISION_NEEDED.md`; do not pick a winner.
- Do not modify `zovark-architecture` or `zovark-reviewops`. If a slice seems to require
  it, STOP → BLOCKER.md (T3/T4).
- One logical commit per slice with the message in the slice spec.

Apply the `karpathy-guidelines` discipline: surface assumptions, simplest sufficient
change, surgical edits, verifiable success criteria.
