# INDEPENDENT AUDIT — SLICE 5 (evidence-backed SOC report, staging)

Three fresh adversarial passes. Branch slices-5-8-staging (not merged to main).

## Cycle 0 (initial) — found 4 issues
- F1 (DANGEROUS): full report path printed unconditional "LSASS" for any credential_access.
- F2 (DANGEROUS): fabricated `C:\Temp\svchost.exe` payload path in every full report.
- F3 (DANGEROUS/acceptance): REVIEW_REQUIRED.md missing.
- F4 (FAIL-SAFE): self-audit wording overstated commit state.

## Cycle 1 — F1/F2/F3 CONFIRMED CLOSED; found 2 more (same class)
Fixes verified: LSASS/SMB report+handoff claims gated on evidence (`_content_mentions`,
`_has_lsass_evidence`); svchost removed; REVIEW_REQUIRED.md written; non-LSASS fixture
`edr-multi-004` locks the gate. New findings:
- Finding A (DANGEROUS): `findings.py` SMB finding title hardcoded "HOST-13" + T1021.002;
  RULE-SMB fired on bare `blocked_by_firewall` (mislabels non-SMB lateral).
- Finding B (DANGEROUS): handoff blast_radius asserted "SMB attempt" for any blocked lateral.

## Cycle 2 — Finding A & B CONFIRMED CLOSED
- SMB finding title → "Lateral movement attempt over SMB (blocked by firewall)" (no host);
  RULE-SMB fires only for genuine SMB (`t1021.002`/`smb`), not bare `blocked_by_firewall`.
- handoff blast_radius SMB wording gated on `_content_mentions_smb`; else
  "lateral-movement attempt".
- Repro `edr-multi-005` (RDP T1021.001 blocked): no SMB finding, no "HOST-13", handoff says
  "lateral-movement attempt"; crafted WinRM (T1021.006) likewise. `edr-multi-001` (genuine
  SMB, actual dest HOST-13) keeps accurate SMB wording.
- multi-005 still `confirmed_malicious` + verifies; determinism byte-identical; forged
  verdict rejected; edr-sample-001 combined hash unchanged (`424d858c…`); no
  network/model/secret; architecture/ReviewOps untouched.

## VERDICT: zero unresolved DANGEROUS-DIRECTION. FAIL-SAFE: new runtime report baseline is
provisional (diverges from the slice001 oracle narrative) — operator decision in
REVIEW_REQUIRED.md.
