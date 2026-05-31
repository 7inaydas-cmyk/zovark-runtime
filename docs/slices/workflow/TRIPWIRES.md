# TRIPWIRES — stop immediately and write BLOCKER.md

Write `BLOCKER.md` (repo root) and STOP if any of these occur. BLOCKER.md must include:
exact failed command, exit code, relevant output, files inspected, current branch+HEAD,
safest next action, and whether work was committed / reverted / left staged.

| ID | Condition |
|---|---|
| T1 | Baseline `proof-package` or `proof-package-verify` missing or failing before implementation. |
| T2 | Slice 3 requires choosing between conflicting verdict-contract semantics (proof-package vs ADR-0046). Write `docs/slices/DECISION_NEEDED.md`, do not pick a winner. |
| T3 | Any write to or required change in `zovark-architecture`. |
| T4 | Any write to or expansion of `zovark-reviewops`. |
| T5 | `proof-package-verify` weakened, bypassed, or made schema-only. |
| T6 | A shape-valid forged package verifies clean. |
| T7 | Replay calls a live model or network. |
| T8 | Deterministic `proof-package` path calls network. |
| T9 | Real secrets or hardcoded provider/integration IDs introduced. |
| T10 | `main`'s generated proof-package bytes / combined hash change unexpectedly. |
| T11 | Slices 5–8 would need to merge to `main` to proceed. |
| T12 | Any unresolved DANGEROUS-DIRECTION finding. |
| T13 | Tests cannot be made green after one focused repair pass. |
| T14 | Repo state becomes ambiguous or dirty in a way that cannot be explained. |
| T15 | Context/token limit approaching and current state is not safely resumable (use the context-limit protocol → CONTINUATION.md). |

Classification rule for findings: FAIL-SAFE (worst case = over-refusal/block, no
integrity loss) may be documented and deferred; DANGEROUS-DIRECTION (could yield a
wrong/unverifiable result presented as correct, or a security escape) must be fixed
before advancing. **Unsure = DANGEROUS-DIRECTION.**
