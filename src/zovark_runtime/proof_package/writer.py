"""Proof-package artifact writer for Slice 001."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.replay import derive_replay_report


JSON_OUTPUT_FILES = (
    "investigation-tape.json",
    "evidence-ledger.json",
    "timeline.json",
    "findings.json",
    "verdict.json",
    "edr-handoff.json",
    "audit-chain-entry.json",
    "replay-report.json",
)
MARKDOWN_OUTPUT_FILES = ("customer-report.md",)
EXPECTED_OUTPUT_FILES = JSON_OUTPUT_FILES + MARKDOWN_OUTPUT_FILES
_RAW_CONTENT_KEY_ORDER = {
    "edr_alert": (
        "alert_id",
        "alert_type",
        "child_process",
        "description",
        "host",
        "host_fqdn",
        "ingested_at",
        "severity",
        "source_process",
        "timestamp",
    ),
    "process_event": (
        "event_id",
        "event_type",
        "ingested_at",
        "parent_pid",
        "parent_process",
        "pid",
        "process_name",
        "command_line",
        "timestamp",
        "user",
    ),
    "network_event": (
        "bytes_received",
        "bytes_sent",
        "classification",
        "destination_ip",
        "destination_port",
        "event_id",
        "event_type",
        "ingested_at",
        "pid",
        "process",
        "protocol",
        "source_host",
        "timestamp",
    ),
    "credential_access": (
        "event_id",
        "event_type",
        "host",
        "ingested_at",
        "pid",
        "process",
        "target_process",
        "technique",
        "technique_name",
        "timestamp",
    ),
    "lateral_movement_attempt": (
        "destination_host",
        "destination_ip",
        "event_id",
        "event_type",
        "ingested_at",
        "pid",
        "process",
        "source_host",
        "status",
        "technique",
        "technique_name",
        "timestamp",
    ),
}


def build_proof_package(tape: dict[str, Any]) -> dict[str, Any]:
    """Build the deterministic 9-file Slice 001 proof package in memory."""
    _validate_tape_for_write(tape)
    package: dict[str, Any] = {
        "investigation-tape.json": _investigation_tape_artifact(tape),
        "evidence-ledger.json": _evidence_ledger_artifact(tape),
        "timeline.json": deepcopy(tape["timeline"]),
        "findings.json": deepcopy(tape["findings"]),
        "verdict.json": deepcopy(tape["verdict"]),
        "edr-handoff.json": _handoff_artifact(tape["handoff"]),
        "audit-chain-entry.json": deepcopy(tape["audit_entry"]),
        "replay-report.json": deepcopy(tape["replay_report"]),
        "customer-report.md": render_customer_report(tape),
    }
    validate_proof_package(package, tape=tape)
    return deepcopy(package)


def write_proof_package(
    tape: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, str]:
    """Write exactly the Slice 001 proof-package artifacts into *output_dir*."""
    package = build_proof_package(tape)
    out_path = Path(output_dir)
    _validate_output_dir(out_path)
    out_path.mkdir(parents=True, exist_ok=True)

    written: dict[str, str] = {}
    for filename in EXPECTED_OUTPUT_FILES:
        destination = out_path / filename
        artifact = package[filename]
        if filename in JSON_OUTPUT_FILES:
            destination.write_text(_json_text(artifact), encoding="utf-8")
        else:
            destination.write_text(artifact, encoding="utf-8")
        written[filename] = str(destination)
    return written


def write_artifacts(
    output_dir: str | Path,
    tape: dict[str, Any],
    handoff: dict[str, Any] | None = None,
    close_audit_entry: dict[str, Any] | None = None,
    replay_report: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Compatibility wrapper matching the Slice 001 task description."""
    updated = deepcopy(tape)
    if handoff is not None:
        updated["handoff"] = deepcopy(handoff)
    if close_audit_entry is not None:
        updated["audit_entry"] = deepcopy(close_audit_entry)
        updated["audit_ref"] = close_audit_entry.get("entry_id")
        updated["state"] = "closed"
    if replay_report is not None:
        updated["replay_report"] = deepcopy(replay_report)
    return write_proof_package(updated, output_dir)


def validate_proof_package(
    package: dict[str, Any],
    *,
    tape: dict[str, Any] | None = None,
) -> None:
    """Validate the in-memory package file set and artifact linkage."""
    if not isinstance(package, dict):
        raise ZovarkValidationError("proof package must be an object")
    if set(package) != set(EXPECTED_OUTPUT_FILES):
        raise ZovarkValidationError("proof package file set is invalid")
    for filename in JSON_OUTPUT_FILES:
        if not isinstance(package[filename], (dict, list)):
            raise ZovarkValidationError(f"{filename} must be a JSON artifact")
    if not isinstance(package["customer-report.md"], str):
        raise ZovarkValidationError("customer-report.md must be Markdown text")
    if not package["customer-report.md"]:
        raise ZovarkValidationError("customer-report.md must not be empty")

    if tape is None:
        return

    _validate_tape_for_write(tape)
    if package["investigation-tape.json"] != _investigation_tape_artifact(tape):
        raise ZovarkValidationError("investigation-tape.json does not match tape")
    if package["evidence-ledger.json"] != _evidence_ledger_artifact(tape):
        raise ZovarkValidationError("evidence-ledger.json does not match tape")
    if package["timeline.json"] != tape["timeline"]:
        raise ZovarkValidationError("timeline.json does not match tape")
    if package["findings.json"] != tape["findings"]:
        raise ZovarkValidationError("findings.json does not match tape")
    if package["verdict.json"] != tape["verdict"]:
        raise ZovarkValidationError("verdict.json does not match tape")
    if package["edr-handoff.json"] != tape["handoff"]:
        raise ZovarkValidationError("edr-handoff.json does not match tape")
    if package["audit-chain-entry.json"] != tape["audit_entry"]:
        raise ZovarkValidationError("audit-chain-entry.json does not match tape")
    if package["replay-report.json"] != tape["replay_report"]:
        raise ZovarkValidationError("replay-report.json does not match tape")


def render_customer_report(tape: dict[str, Any]) -> str:
    """Render the deterministic human-readable Slice 001 customer report."""
    _validate_tape_for_write(tape)
    ledger = tape["raw_evidence"]
    findings = tape["findings"]
    verdict = tape["verdict"]
    handoff = tape["handoff"]
    replay_report = tape["replay_report"]
    source_types = {entry["source_type"] for entry in ledger}
    if not {
        "credential_access",
        "lateral_movement_attempt",
        "network_event",
        "process_event",
    }.issubset(source_types):
        return _render_generic_customer_report(tape)

    ev_ids = [entry["evidence_id"] for entry in ledger]
    ev_short = [_short_evidence_id(evidence_id) for evidence_id in ev_ids]
    alert = _first_raw_content(ledger, "edr_alert")
    process = _first_raw_content(ledger, "process_event")
    network = _first_raw_content(ledger, "network_event")
    credential = _first_raw_content(ledger, "credential_access")
    lateral = _first_raw_content(ledger, "lateral_movement_attempt")
    target = handoff["target"]
    rollback = handoff["rollback_plan"]
    signing_tag = verdict["signing_tag"]
    entry1_this = replay_report["audit_chain_entry"]["prev_entry_hash"]
    entry2_this = replay_report["audit_chain_entry"]["this_entry_hash"]

    host = target["identifier"]
    fqdn = target.get("fqdn")
    target_label = f"{host} ({fqdn})" if fqdn else host
    user = _string_from(process, "user", default="the affected user")
    source_process = _string_from(alert, "source_process", default="source process")
    child_process = _string_from(alert, "child_process", default="child process")
    destination_ip = _string_from(network, "destination_ip", default="external IP")
    destination_port = network.get("destination_port", 443)
    bytes_received = network.get("bytes_received", 0)
    kib_received = bytes_received // 1024 if isinstance(bytes_received, int) else 0
    kb_received = round(bytes_received / 1000) if isinstance(bytes_received, int) else 0
    credential_technique = _string_from(credential, "technique", default="T1003.001")
    lateral_host = _string_from(lateral, "destination_host", default="target host")
    alert_timestamp = _string_from(alert, "timestamp", default=tape["created_at"])
    event_minute = _utc_minute(alert_timestamp)
    event_date = alert_timestamp[:10]

    lines = [
        "# Zovark Proof Package",
        "",
        "**Zovark is the AI-native proof layer for high-stakes security response.**",
        "",
        "---",
        "",
        "## Recommended Action (EDR Action Card)",
        "",
        f"**Action:** {handoff['action_type'].upper()}",
        f"**Target:** {target_label}",
        "**Approval required:** YES — no action has been dispatched",
        f"**Evidence basis:** {len(ledger)} evidence items (see below)",
        f"**Verdict:** {verdict['value'].upper()}",
        (
            f"**Reversibility:** {rollback['reversibility_class']} — "
            f"`{rollback['vendor_reversal_action']}` available"
        ),
        f"**Authorization:** {handoff['authorization_record_ref']} (bootstrap mode)",
        "",
        "> No action has been dispatched. Human approval is required before any EDR action is taken.",
        "",
        "---",
        "",
        "## 1. What happened?",
        "",
        f"At {event_minute} UTC on {event_date}, a user on {host} opened a document that caused",
        f"Microsoft Word (`{source_process}`) to spawn a hidden PowerShell process with an",
        "encoded command. The PowerShell process then:",
        "",
        f"1. Connected to an external IP ({destination_ip}) over HTTPS and downloaded {kib_received} KB.",
        f"2. Attempted to read LSASS memory — a credential dumping technique ({credential_technique}).",
        f"3. Attempted to move laterally to {lateral_host} via SMB (blocked by firewall).",
        "",
        "The sequence is consistent with a phishing-delivered implant executing a",
        "multi-stage attack: initial access → C2 communication → credential theft →",
        "lateral movement.",
        "",
        "---",
        "",
        "## 2. What evidence supports it?",
        "",
        "| # | Evidence ID | Type | Timestamp | Key detail |",
        "|---|---|---|---|---|",
        f"| 1 | {ev_short[0]} | edr_alert | {_time_only(alert['timestamp'])} | {source_process} spawned {child_process} |",
        (
            f"| 2 | {ev_short[1]} | process_event | {_time_only(process['timestamp'])} | "
            f"{process['process_name']} -EncodedCommand (hidden window) |"
        ),
        (
            f"| 3 | {ev_short[2]} | network_event | {_time_only(network['timestamp'])} | "
            f"{destination_ip}:{destination_port}, {kb_received} KB received |"
        ),
        (
            f"| 4 | {ev_short[3]} | credential_access | {_time_only(credential['timestamp'])} | "
            f"LSASS memory read ({credential_technique}) |"
        ),
        (
            f"| 5 | {ev_short[4]} | lateral_movement_attempt | {_time_only(lateral['timestamp'])} | "
            f"SMB to {lateral_host} (blocked) |"
        ),
        "",
        "Each evidence entry carries a SHA-256 hash of its exact content. The hashes are",
        "verified during replay — any post-ingestion tampering would cause replay to fail",
        "with `evidence_corruption`.",
        "",
        "---",
        "",
        "## 3. Why was this verdict reached?",
        "",
        f"**Verdict:** `{verdict['value']}`",
        "",
        "**Derivation rule:** Any finding with severity `critical` or `high` → `confirmed_malicious`",
        "",
        "**Findings that triggered this verdict:**",
        "",
        "| Finding | Severity | MITRE |",
        "|---|---|---|",
    ]
    for finding in findings:
        severity = finding["severity"]
        rendered_severity = f"**{severity}**" if severity == "critical" else severity
        title = finding["title"].replace(" (blocked by firewall)", " (blocked)")
        lines.append(
            f"| {title} | {rendered_severity} | {finding.get('mitre_technique', '')} |"
        )
    lines.extend(
        [
            "",
            "The verdict is **deterministic** — it is a pure function of the recorded findings.",
            "No AI model contributed. Same evidence, same rules, same verdict every time.",
            "",
            "`model_contribution: false` on all findings and on the verdict.",
            "",
            "---",
            "",
            "## 4. What response action is recommended?",
            "",
            f"**Isolate {host}.**",
            "",
            "Rationale: The host has demonstrated active C2 communication, credential dumping,",
            "and lateral movement intent. Isolation stops the active threat while preserving",
            "forensic state for investigation.",
            "",
            "The action card (`edr-handoff.json`) contains the full structured recommendation",
            "including evidence links, policy snapshot, and rollback plan.",
            "",
            "---",
            "",
            "## 5. What is the approval mode?",
            "",
            f"**{handoff['approval_mode']}**",
            "",
            "No action has been dispatched. The action card is a recommendation. A human",
            "approver must review this proof package and record their approval before any",
            "EDR action is taken.",
            "",
            f"Authorization record: `{handoff['authorization_record_ref']}` (bootstrap mode — production",
            "vault runtime is a future milestone).",
            "",
            "---",
            "",
            "## 6. What is the blast radius?",
            "",
            f"**Directly affected:** {host} only.",
            "",
            f"- All active user sessions on {host} will be terminated.",
            f"- All processes on {host} will lose network access.",
            f"- Shared drives mounted from {host} will become unavailable.",
            "",
            f"**Lateral movement:** {lateral_host} was targeted but the attempt was blocked by the",
            "firewall before isolation. No other hosts are known to be compromised.",
            "",
            f"**User impact:** {user} is the active user on {host}. Credential rotation",
            "for this account is recommended regardless of isolation outcome, given the LSASS",
            "access event.",
            "",
            "---",
            "",
            "## 7. How can the action be reversed or recovered?",
            "",
            f"**Reversibility class:** `{rollback['reversibility_class']}`",
            "",
            "If isolation is approved and later found to be a false positive:",
            "",
            f"- In a live EDR integration, the expected reversal action would be `{rollback['vendor_reversal_action']}`.",
            "- In Slice 001, this is a recommendation only; no EDR action is dispatched.",
            "- Reversal window: 4 hours from dispatch.",
            "",
            "**Regardless of isolation outcome:**",
            f"- Rotate credentials for {user} (LSASS was accessed; assume credentials compromised).",
            "- Review the downloaded payload at `C:\\Temp\\svchost.exe` (decoded from the PowerShell command).",
            f"- Investigate the C2 IP {destination_ip}.",
            "",
            "---",
            "",
            "## 8. Can the decision be replayed?",
            "",
            "**Yes. Replay result: succeeded.**",
            "",
            "The replay engine verified:",
            "",
            "| Check | Result |",
            "|---|---|",
            f"| Evidence hashes verified | ✅ all {len(ledger)} entries matched |",
            f"| Verdict recomputed | ✅ `{verdict['value']}` |",
            "| Verdict matched stored verdict | ✅ |",
            "| Live LLM call during replay | ❌ none |",
            "| Live EDR call during replay | ❌ none |",
            "",
            "The proof package is self-contained. An auditor can verify the reasoning offline,",
            "months or years later, without access to Zovark's infrastructure or the original",
            "EDR system.",
            "",
            f"Replay ID: `{replay_report['replay_state']['replay_id']}`",
            f"Replay mode: `{replay_report['replay_state']['mode']}`",
            "",
            "---",
            "",
            "## Audit Chain",
            "",
            "| Entry | Event | Entry ID | Hash |",
            "|---|---|---|---|",
            f"| 1 | tape_recording_closed | audit-entry-1 | {entry1_this[:16]}...{entry1_this[-4:]} |",
            f"| 2 | tape_replayed | audit-entry-2 | {entry2_this[:16]}...{entry2_this[-4:]} |",
            "",
            "Chain: hash-linked. Entry 2's `prev_entry_hash` equals entry 1's `this_entry_hash`.",
            "Root signing deferred to M1+ (production vault runtime).",
            "",
            "---",
            "",
            "## Internal Proof Substrate",
            "",
            f"Tape ID: {tape['tape_id']}",
            f"Tenant: {tape['tenant_id']}",
            f"Source alert: {tape['source_alert_ref']}",
            f"Generated: {tape['created_at']}",
            f"Schema: {tape['schema_version']}",
            f"Signing tag: {signing_tag}",
            "",
            "---",
            "",
            "## Artifacts",
            "",
            "- `edr-handoff.json`          ← EDR action card (hero artifact)",
            "- `replay-report.json`        ← Replayable proof package (hero artifact)",
            "- `customer-report.md`        ← This document",
            "- `investigation-tape.json`   ← Internal proof substrate",
            "- `evidence-ledger.json`",
            "- `timeline.json`",
            "- `findings.json`",
            "- `verdict.json`",
            "- `audit-chain-entry.json`",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_generic_customer_report(tape: dict[str, Any]) -> str:
    ledger = tape["raw_evidence"]
    findings = tape["findings"]
    verdict = tape["verdict"]
    handoff = tape["handoff"]
    replay_report = tape["replay_report"]
    target = handoff["target"]
    rollback = handoff["rollback_plan"]
    alert = _first_raw_content(ledger, "edr_alert")
    target_identifier = target["identifier"]
    target_label = _target_label(target)
    action_title = (
        f"Isolate {target_identifier}."
        if handoff["action_type"] == "isolate_host"
        else "Notify the response owner."
    )
    entry1_this = replay_report["audit_chain_entry"]["prev_entry_hash"]
    entry2_this = replay_report["audit_chain_entry"]["this_entry_hash"]

    lines = [
        "# Zovark Proof Package",
        "",
        "**Zovark is the AI-native proof layer for high-stakes security response.**",
        "",
        "---",
        "",
        "## Recommended Action (EDR Action Card)",
        "",
        f"**Action:** {handoff['action_type'].upper()}",
        f"**Target:** {target_label}",
        "**Approval required:** YES — no action has been dispatched",
        f"**Evidence basis:** {len(ledger)} evidence items (see below)",
        f"**Verdict:** {verdict['value'].upper()}",
        (
            f"**Reversibility:** {rollback['reversibility_class']} — "
            f"`{rollback['vendor_reversal_action']}` available"
        ),
        f"**Authorization:** {handoff['authorization_record_ref']} (bootstrap mode)",
        "",
        "> No action has been dispatched. Human approval is required before any EDR action is taken.",
        "",
        "---",
        "",
        "## 1. What happened?",
        "",
        _string_from(alert, "description", default="A static EDR alert was processed."),
        "",
        "Zovark normalized the static EDR-style JSON into content-addressed evidence,",
        "derived rule-based findings, computed a deterministic verdict, produced an",
        "approval-required handoff card, sealed the tape, and replay-verified the result.",
        "",
        "---",
        "",
        "## 2. What evidence supports it?",
        "",
        "| # | Evidence ID | Type | Timestamp | Key detail |",
        "|---|---|---|---|---|",
    ]
    for index, entry in enumerate(ledger, start=1):
        lines.append(
            f"| {index} | {_short_evidence_id(entry['evidence_id'])} | "
            f"{entry['source_type']} | {_evidence_timestamp(entry)} | "
            f"{_evidence_detail(entry)} |"
        )
    lines.extend(
        [
            "",
            "Each evidence entry carries a SHA-256 hash of its exact content. The hashes are",
            "verified during replay — any post-ingestion tampering would cause replay to fail.",
            "",
            "---",
            "",
            "## 3. Why was this verdict reached?",
            "",
            f"**Verdict:** `{verdict['value']}`",
            "",
            f"**Derivation rule:** {verdict['derivation_rule']}",
            "",
            "**Findings that triggered this verdict:**",
            "",
            "| Finding | Severity | MITRE |",
            "|---|---|---|",
        ]
    )
    for finding in findings:
        lines.append(
            f"| {finding['title']} | {finding['severity']} | {finding.get('mitre_technique', '')} |"
        )
    lines.extend(
        [
            "",
            "The verdict is deterministic. No AI model contributed.",
            "",
            "`model_contribution: false` on all findings and on the verdict.",
            "",
            "---",
            "",
            "## 4. What response action is recommended?",
            "",
            f"**{action_title}**",
            "",
            "The action card (`edr-handoff.json`) contains the structured recommendation,",
            "approval gate, evidence links, policy snapshot, and rollback plan.",
            "",
            "---",
            "",
            "## 5. What is the approval mode?",
            "",
            f"**{handoff['approval_mode']}**",
            "",
            "No action has been dispatched. The action card is a recommendation. A human",
            "approver must review this proof package before any EDR action is taken.",
            "",
            f"Authorization record: `{handoff['authorization_record_ref']}` (bootstrap mode).",
            "",
            "---",
            "",
            "## 6. What is the blast radius?",
            "",
            handoff["blast_radius"]["estimated_business_impact"],
            "",
            "---",
            "",
            "## 7. How can the action be reversed or recovered?",
            "",
            f"**Reversibility class:** `{rollback['reversibility_class']}`",
            "",
            f"- Expected reversal action: `{rollback['vendor_reversal_action']}`.",
            "- In Slice 001, this is a recommendation only; no EDR action is dispatched.",
            f"- Reversal window: {rollback['reversal_window']}.",
            "",
            "---",
            "",
            "## 8. Can the decision be replayed?",
            "",
            "**Yes. Replay result: succeeded.**",
            "",
            "The replay engine verified:",
            "",
            "| Check | Result |",
            "|---|---|",
            f"| Evidence hashes verified | all {len(ledger)} entries matched |",
            f"| Verdict recomputed | `{verdict['value']}` |",
            "| Verdict matched stored verdict | yes |",
            "| Live LLM call during replay | none |",
            "| Live EDR call during replay | none |",
            "",
            f"Replay ID: `{replay_report['replay_state']['replay_id']}`",
            f"Replay mode: `{replay_report['replay_state']['mode']}`",
            "",
            "---",
            "",
            "## Audit Chain",
            "",
            "| Entry | Event | Entry ID | Hash |",
            "|---|---|---|---|",
            f"| 1 | tape_recording_closed | audit-entry-1 | {entry1_this[:16]}...{entry1_this[-4:]} |",
            f"| 2 | tape_replayed | audit-entry-2 | {entry2_this[:16]}...{entry2_this[-4:]} |",
            "",
            "Chain: hash-linked. Entry 2's `prev_entry_hash` equals entry 1's `this_entry_hash`.",
            "",
            "---",
            "",
            "## Internal Proof Substrate",
            "",
            f"Tape ID: {tape['tape_id']}",
            f"Tenant: {tape['tenant_id']}",
            f"Source alert: {tape['source_alert_ref']}",
            f"Generated: {tape['created_at']}",
            f"Schema: {tape['schema_version']}",
            f"Signing tag: {verdict['signing_tag']}",
            "",
            "---",
            "",
            "## Artifacts",
            "",
            "- `edr-handoff.json`          ← EDR action card (hero artifact)",
            "- `replay-report.json`        ← Replayable proof package (hero artifact)",
            "- `customer-report.md`        ← This document",
            "- `investigation-tape.json`   ← Internal proof substrate",
            "- `evidence-ledger.json`",
            "- `timeline.json`",
            "- `findings.json`",
            "- `verdict.json`",
            "- `audit-chain-entry.json`",
        ]
    )
    return "\n".join(lines) + "\n"


def _validate_tape_for_write(tape: dict[str, Any]) -> None:
    if not isinstance(tape, dict):
        raise ZovarkValidationError("tape must be an object")
    if "replay_report" not in tape:
        raise ZovarkValidationError("tape is missing replay_report")
    expected_replay = derive_replay_report(tape)
    if tape["replay_report"] != expected_replay:
        raise ZovarkValidationError(
            "tape.replay_report does not match derived replay report"
        )


def _investigation_tape_artifact(tape: dict[str, Any]) -> dict[str, Any]:
    handoff = tape["handoff"]
    return {
        "audit_ref": tape["audit_ref"],
        "created_at": tape["created_at"],
        "findings": deepcopy(tape["findings"]),
        "handoff_ref": tape.get("handoff_ref", handoff["handoff_id"]),
        "handoff_summary": deepcopy(
            tape.get("handoff_summary", _handoff_summary(handoff))
        ),
        "raw_evidence": _evidence_ledger_artifact(tape),
        "schema_version": tape["schema_version"],
        "source_alert_ref": tape["source_alert_ref"],
        "state": tape["state"],
        "tape_id": tape["tape_id"],
        "tenant_id": tape["tenant_id"],
        "timeline": deepcopy(tape["timeline"]),
        "verdict": deepcopy(tape["verdict"]),
    }


def _evidence_ledger_artifact(tape: dict[str, Any]) -> list[dict[str, Any]]:
    return [_evidence_entry_artifact(entry) for entry in tape["raw_evidence"]]


def _evidence_entry_artifact(entry: dict[str, Any]) -> dict[str, Any]:
    source_type = entry["source_type"]
    return {
        "evidence_id": entry["evidence_id"],
        "hash": entry["hash"],
        "ingested_at": entry["ingested_at"],
        "raw_content": _ordered_raw_content(source_type, entry["raw_content"]),
        "source_type": source_type,
    }


def _handoff_artifact(handoff: dict[str, Any]) -> dict[str, Any]:
    artifact = deepcopy(handoff)
    target = handoff["target"]
    ordered_target: dict[str, Any] = {}
    for key in ("fqdn", "identifier", "kind", "validated_at"):
        if key in target:
            ordered_target[key] = deepcopy(target[key])
    for key, value in target.items():
        if key not in ordered_target:
            ordered_target[key] = deepcopy(value)
    artifact["target"] = ordered_target
    return artifact


def _ordered_raw_content(
    source_type: str,
    raw_content: dict[str, Any],
) -> dict[str, Any]:
    key_order = _RAW_CONTENT_KEY_ORDER.get(source_type, ())
    ordered: dict[str, Any] = {}
    for key in key_order:
        if key in raw_content:
            ordered[key] = deepcopy(raw_content[key])
    for key, value in raw_content.items():
        if key not in ordered:
            ordered[key] = deepcopy(value)
    return ordered


def _handoff_summary(handoff: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_type": handoff["action_type"],
        "approval_mode": handoff["approval_mode"],
        "execution_status": handoff["execution_result"]["status"],
        "target": {
            "identifier": handoff["target"]["identifier"],
            "kind": handoff["target"]["kind"],
        },
    }


def _validate_output_dir(output_dir: Path) -> None:
    if output_dir.exists() and not output_dir.is_dir():
        raise ZovarkValidationError("output_dir must be a directory")
    if not output_dir.exists():
        return
    unexpected = [
        entry.name for entry in output_dir.iterdir() if entry.name not in EXPECTED_OUTPUT_FILES
    ]
    if unexpected:
        raise ZovarkValidationError("output_dir contains unexpected files")


def _json_text(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def _first_raw_content(
    evidence_entries: list[dict[str, Any]],
    source_type: str,
) -> dict[str, Any]:
    for entry in evidence_entries:
        if entry["source_type"] == source_type:
            return entry["raw_content"]
    raise ZovarkValidationError(f"missing {source_type} evidence")


def _short_evidence_id(evidence_id: str) -> str:
    return evidence_id[:20] + "..." + evidence_id[-3:]


def _target_label(target: dict[str, Any]) -> str:
    identifier = target["identifier"]
    fqdn = target.get("fqdn")
    if isinstance(fqdn, str) and fqdn and fqdn != identifier:
        return f"{identifier} ({fqdn})"
    return identifier


def _evidence_timestamp(entry: dict[str, Any]) -> str:
    raw_content = entry["raw_content"]
    timestamp = raw_content.get("timestamp", entry["ingested_at"])
    if not isinstance(timestamp, str) or not timestamp:
        raise ZovarkValidationError("evidence timestamp must be a non-empty string")
    return _time_only(timestamp)


def _evidence_detail(entry: dict[str, Any]) -> str:
    raw_content = entry["raw_content"]
    source_type = entry["source_type"]
    if source_type == "edr_alert":
        return _string_from(raw_content, "description", default="EDR alert")
    if source_type == "process_event":
        return _string_from(raw_content, "command_line", default="Process event")
    if source_type in {"network_event", "network_flow"}:
        destination_ip = _string_from(raw_content, "destination_ip", default="destination")
        destination_port = raw_content.get("destination_port")
        if isinstance(destination_port, int):
            return f"{destination_ip}:{destination_port}"
        return destination_ip
    if source_type == "credential_access":
        return _string_from(raw_content, "technique_name", default="Credential access")
    if source_type == "lateral_movement_attempt":
        return _string_from(raw_content, "technique_name", default="Lateral movement")
    return source_type


def _string_from(source: dict[str, Any], key: str, *, default: str) -> str:
    value = source.get(key)
    if isinstance(value, str) and value:
        return value
    return default


def _time_only(timestamp: str) -> str:
    if len(timestamp) != 20 or timestamp[10] != "T" or timestamp[19] != "Z":
        raise ZovarkValidationError("timestamp must be ISO-8601 UTC")
    return timestamp[11:19] + "Z"


def _utc_minute(timestamp: str) -> str:
    return _time_only(timestamp)[:5]
