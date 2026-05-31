# VERIFY_SLICE_7 — recorded live-AI investigation (STAGING)
- ai-investigate (fake provider) records model I/O + store anchor; ai-replay re-validates
  OFFLINE: exit 0, no_live_llm_call/no_live_edr_call true, model_contribution true,
  is_verdict_authority false.
- 9 ai tests: record→replay offline; replay refuses a provider; replay never calls model
  (ExplodingProvider rejected, not invoked); tampered output / tampered hash / consistent
  tamper (caught by store anchor) all fail closed; model NOT verdict authority
  (is_verdict_authority=True → rejected); AI layer does not change the deterministic verdict
  (verdict.json identical, model_contribution stays false); record deterministic across runs.
- Canonical 9-artifact package UNCHANGED (424d858c… on staging); AI artifact is separate.
- Full suite 324 passed; Phase-0 PASS. main untouched (staging only).
