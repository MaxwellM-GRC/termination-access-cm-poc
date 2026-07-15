"""Reporting — turn findings into auditor-friendly outputs.

Outputs:
  * A console summary for a quick read of the run.
  * A timestamped CSV exception log — the artifact you would hand to an auditor.
  * A JSON summary for downstream automation (issue creation, chat alerts).
  * A Markdown summary suitable for a GitHub issue or notification body.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime

from .models import Finding, ReviewResult, Severity

_SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.INFO: 3,
}

_COLUMNS = [
    "employee_id",
    "full_name",
    "department",
    "termination_date",
    "termination_type",
    "system",
    "account_id",
    "rule",
    "severity",
    "days_late",
    "detail",
]


def _sorted(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (_SEVERITY_ORDER[f.severity], f.system))


def write_exception_log(findings: list[Finding], path: str) -> str:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_COLUMNS)
        writer.writeheader()
        for finding in _sorted(findings):
            writer.writerow(finding.as_row())
    return path


def print_summary(result: ReviewResult) -> None:
    findings = _sorted(result.findings)
    counts = {sev: 0 for sev in Severity}
    for f in findings:
        counts[f.severity] += 1

    print("=" * 72)
    print("TERMINATION ACCESS REVIEW — RUN SUMMARY")
    print("=" * 72)
    print(f"Terminated employees reviewed : {result.terminated_count}")
    print(f"Accounts ingested             : {result.account_count}")
    print(f"Identities correlated         : {result.matched_identities}")
    print(f"Terminated w/ no account found: {len(result.unmatched_employees)}")
    print("-" * 72)
    print(
        f"Findings: {len(findings)}  "
        f"(critical {counts[Severity.CRITICAL]}, "
        f"high {counts[Severity.HIGH]}, "
        f"info {counts[Severity.INFO]})"
    )
    print("-" * 72)

    if not findings:
        print("No exceptions. All terminated access de-provisioned within SLA.")
    for f in findings:
        late = f" [+{f.days_late}d]" if f.days_late is not None else ""
        print(
            f"[{f.severity.value.upper():8}] {f.rule:22} "
            f"{f.employee.full_name:18} {f.system:14}{late}"
        )
        print(f"           -> {f.detail}")

    if result.unmatched_employees:
        print("-" * 72)
        print("Terminated employees with NO downstream account matched:")
        for emp in result.unmatched_employees:
            print(f"  - {emp.full_name} ({emp.employee_id}), {emp.department}")
    print("=" * 72)


def default_log_name() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"exception_log_{stamp}.csv"


def _severity_counts(findings: list[Finding]) -> dict:
    counts = {sev.value: 0 for sev in Severity}
    for f in findings:
        counts[f.severity.value] += 1
    return counts


def print_integrity(sources) -> None:
    """Print the input completeness/accuracy check that precedes the review."""
    print("INPUT INTEGRITY (completeness & accuracy of source data)")
    print("-" * 72)
    for s in sources:
        if not s.ok:
            print(f"  [FAIL] {s.name}: missing mapped column(s) {s.missing_columns}")
            continue
        flags = []
        if s.blank_key_rows:
            flags.append(f"{s.blank_key_rows} blank-key row(s)")
        if s.unparsable_dates:
            flags.append(f"{s.unparsable_dates} unparsable date(s)")
        note = f" ({', '.join(flags)})" if flags else ""
        print(f"  [ OK ] {s.name}: {s.row_count} row(s){note}")
    print("=" * 72)


def _owners_to_notify(findings: list[Finding], system_owners: dict | None) -> list[dict]:
    """Distinct {system, owner} pairs for the systems that have findings."""
    if not system_owners:
        return []
    seen: dict[str, str] = {}
    for f in findings:
        owner = system_owners.get(f.system)
        if owner and f.system not in seen:
            seen[f.system] = owner
    return [{"system": s, "owner": o} for s, o in seen.items()]


def write_summary_json(
    result: ReviewResult,
    sla_days: int,
    path: str,
    system_owners: dict | None = None,
    integrity: list | None = None,
) -> str:
    """Machine-readable run summary for downstream automation (issues, alerts)."""
    findings = _sorted(result.findings)
    owners = system_owners or {}
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sla_days": sla_days,
        "input_valid": result.input_valid,
        "input_integrity": [s.as_dict() for s in (integrity or [])],
        "totals": {
            "terminated_reviewed": result.terminated_count,
            "accounts_ingested": result.account_count,
            "identities_correlated": result.matched_identities,
            "unmatched_employees": len(result.unmatched_employees),
            "findings": len(findings),
            "population_reconciled": result.population_reconciled,
        },
        "counts_by_severity": _severity_counts(findings),
        "owners_to_notify": _owners_to_notify(findings, owners),
        "findings": [
            {**f.as_row(), "owner": owners.get(f.system, "")} for f in findings
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path


def render_markdown_summary(
    result: ReviewResult,
    sla_days: int,
    system_owners: dict | None = None,
) -> str:
    """Markdown body for a GitHub issue or chat notification."""
    findings = _sorted(result.findings)
    counts = _severity_counts(findings)
    owners = system_owners or {}
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"**Termination access review — {stamp}**",
        "",
        f"- Terminated reviewed: {result.terminated_count}",
        f"- Accounts ingested: {result.account_count}",
        f"- SLA: {sla_days} days",
        f"- **Findings: {len(findings)}** "
        f"(critical {counts['critical']}, high {counts['high']}, "
        f"medium {counts['medium']}, info {counts['info']})",
        "",
    ]

    if not findings:
        lines.append("No exceptions. All terminated access de-provisioned within SLA.")
        return "\n".join(lines)

    routing = _owners_to_notify(findings, owners)
    if routing:
        tags = ", ".join(f"{r['owner']} ({r['system']})" for r in routing)
        lines += [f"**Action required by:** {tags}", ""]

    lines += ["| Severity | Rule | Employee | System | Owner | Detail |",
              "|----------|------|----------|--------|-------|--------|"]
    for f in findings:
        detail = f.detail.replace("|", "\\|")
        owner = owners.get(f.system, "")
        lines.append(
            f"| {f.severity.value} | {f.rule} | {f.employee.full_name} "
            f"| {f.system} | {owner} | {detail} |"
        )
    return "\n".join(lines)
