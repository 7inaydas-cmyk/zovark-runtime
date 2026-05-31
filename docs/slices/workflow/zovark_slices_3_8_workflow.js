// Zovark slices 3–8 — READ-ONLY fan-out helper for ONE slice.
//
// This Claude Code Dynamic Workflow parallelizes ONLY read-only work: repo scouting,
// test/repro runs, and adversarial audit (mutation-testing guards). It deliberately does
// NOT write product code, do git operations, or make merge/staging decisions — those are
// CONTROLLER-owned in the main loop, because builders must be serialized (linear chain
// 3→4→5→6→7→8) and merge/operator-approval gates require judgment.
//
// Invoke per slice (do NOT run until the /goal is given), e.g.:
//   Workflow({ scriptPath: "docs/slices/workflow/zovark_slices_3_8_workflow.js",
//              args: { slice: 3, repo: "/home/excelsior/Desktop/Zovark-Kiro/zovark-runtime" } })
//
// Concurrency is capped by the runtime (min(16, cores-2)); we keep fan-out <= 8.

export const meta = {
  name: 'zovark-slice-readonly-fanout',
  description: 'Read-only scout/test/audit fan-out for one Zovark slice (no code writing, no git)',
  phases: [
    { title: 'Scout',  detail: 'parallel read-only subsystem scouts' },
    { title: 'Verify', detail: 'test/repro worker runs commands, records exit codes + hashes' },
    { title: 'Audit',  detail: 'parallel adversarial auditors mutation-test guards' },
  ],
}

const REPO = (typeof args === 'object' && args && args.repo) || '/home/excelsior/Desktop/Zovark-Kiro/zovark-runtime'
const SLICE = (typeof args === 'object' && args && args.slice) || 3
const WF = `${REPO}/docs/slices/workflow`
const SPEC = `${WF}/SLICE_${SLICE}_SPEC.md`

const FACTS = {
  type: 'object', additionalProperties: false,
  required: ['area', 'facts', 'unknowns'],
  properties: {
    area: { type: 'string' },
    facts: { type: 'array', items: { type: 'string' }, description: 'verified facts with file:line' },
    unknowns: { type: 'array', items: { type: 'string' }, description: 'ambiguities needing verification' },
  },
}
const VERIFY = {
  type: 'object', additionalProperties: false,
  required: ['commands', 'all_exit_zero', 'combined_hash', 'verifier_status', 'notes'],
  properties: {
    commands: { type: 'array', items: { type: 'string' } },
    all_exit_zero: { type: 'boolean' },
    combined_hash: { type: 'string' },
    verifier_status: { type: 'string' },
    notes: { type: 'string' },
  },
}
const AUDIT = {
  type: 'object', additionalProperties: false,
  required: ['lens', 'findings'],
  properties: {
    lens: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['title', 'classification', 'repro'],
        properties: {
          title: { type: 'string' },
          classification: { type: 'string', enum: ['DANGEROUS-DIRECTION', 'FAIL-SAFE', 'NONE'] },
          repro: { type: 'string' },
        },
      },
    },
  },
}

const RO = `STRICT READ-ONLY. Do NOT edit any src/ or product file. You may run shell commands to read/test. Repo: ${REPO}. Read ${SPEC} and the relevant AGENT_*.md in ${WF} for your role.`

// ---- Phase 1: Scout (parallel, <=6) -------------------------------------------------
phase('Scout')
const scoutAreas = [
  { key: 'cli',        name: 'CLI subcommands + exit codes (src/zovark_runtime/cli.py)' },
  { key: 'generator',  name: 'generator field-sets/enums (proof_package/{ingest,tape,timeline,findings,verdict,handoff,audit,replay,writer}.py)' },
  { key: 'verifier',   name: 'semantic boundary (proof_package/{package_verifier,verify}.py) — note any change that would weaken it' },
  { key: 'adr0046',    name: 'ADR-0046 assets (verdict_derivation.py, replay_validation.py, contracts/{verdict_input,verdict_envelope,replay_record}.schema.json)' },
  { key: 'fixtures',   name: 'fixtures + tests (tests/fixtures, tests/test_proof_package_*.py)' },
  { key: 'schemas',    name: 'contracts/proof_package/*.schema.json + Phase-0 check scripts + CI' },
]
const scout = (await parallel(scoutAreas.map((a) => () =>
  agent(`${RO}\nRole: REPO SCOUT. Report verified facts (with file:line, quote signatures — do not paraphrase contracts) about: ${a.name}. List any ambiguity as an unknown rather than guessing.`,
    { label: `scout:${a.key}`, phase: 'Scout', schema: FACTS })
))).filter(Boolean)

// ---- Phase 2: Verify (single test/repro worker) -------------------------------------
phase('Verify')
const verify = await agent(
  `${RO}\nRole: TEST/REPRO. Run (record exact command + exit code): full suite + 3 Phase-0 checks; proof-package twice into clean /tmp dirs; combined sha256 of the 9 artifacts (both runs, report byte-identity); proof-package-verify (status, failure_count, findings_rederived_from_evidence). You may run test-only repros but must NOT modify src/.`,
  { label: 'test-repro', phase: 'Verify', schema: VERIFY })

// ---- Phase 3: Audit (parallel adversarial lenses, <=5) ------------------------------
phase('Audit')
const auditLenses = [
  'verifier-not-weakened (mutation-test: can a shape-valid forged package verify clean?)',
  'determinism (run twice; any nondeterministic field?)',
  'no-network/no-live-model in deterministic/replay/verdict path (monkeypatch socket/provider)',
  'secrets/architecture/reviewops/benign-notify-only/readiness-claims scan',
  'slice-specific acceptance per ' + SPEC + ' (tamper replay_record / verdict_envelope / model-output where applicable)',
]
const audit = (await parallel(auditLenses.map((lens, i) => () =>
  agent(`${RO}\nRole: INDEPENDENT AUDITOR. You did not write the implementation and must not modify src/. Mutation-test the guard for this lens: ${lens}. Classify each finding DANGEROUS-DIRECTION vs FAIL-SAFE (unsure = DANGEROUS-DIRECTION) with a concrete repro.`,
    { label: `audit:${i}`, phase: 'Audit', schema: AUDIT })
))).filter(Boolean)

const dangerous = audit.flatMap((a) => a.findings).filter((f) => f.classification === 'DANGEROUS-DIRECTION')
log(`slice ${SLICE}: scouts=${scout.length} verifier=${verify.verifier_status} dangerous_findings=${dangerous.length}`)

return {
  slice: SLICE,
  scout,
  verify,
  audit,
  dangerous_direction_count: dangerous.length,
  // Controller decides build/commit/merge/stage from this read-only evidence.
  controller_note: 'Read-only evidence only. Builder edits + git + merge gates are controller-owned in the main loop.',
}
