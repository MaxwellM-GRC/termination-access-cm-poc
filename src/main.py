"""CLI entry point for the termination access review.

Usage:
    python -m src.main                          # run, print summary
    python -m src.main --out log.csv            # also write exception log
    python -m src.main --summary-json out.json  # machine-readable summary
    python -m src.main --sla 5                  # override SLA window (days)
    python -m src.main --fail-on high           # exit non-zero on high+ findings

The --fail-on flag turns the review into something a scheduler can act on: a
non-zero exit lets CI mark the run failed (and alert), while --summary-json
gives downstream steps (issue creation, Slack) structured data to work from.
"""

from __future__ import annotations

import argparse
import sys

import yaml

from . import correlation, detection, integrity, loaders, reporting
from .models import ReviewResult, Severity

# Ordered most-severe first; index doubles as the threshold rank.
_SEVERITY_RANK = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.INFO: 3,
}
_THRESHOLDS = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "info": 3,
    "none": 99,  # never fail
}


def run(
    config_path: str,
    sla_override: int | None,
    out_path: str | None,
    summary_json_path: str | None = None,
    issue_md_path: str | None = None,
) -> ReviewResult:
    with open(config_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    sla_days = sla_override if sla_override is not None else cfg["deprovisioning_sla_days"]

    system_owners = {
        s["name"]: s["owner"] for s in cfg["systems"] if s.get("owner")
    }

    # Completeness & accuracy of inputs (IPE) before anything is relied upon.
    input_checks = integrity.validate_inputs(cfg)
    reporting.print_integrity(input_checks)

    if not integrity.inputs_ok(input_checks):
        # A mapped column is missing, so the extract is mis-shaped and the output
        # cannot be trusted. Record the failure and stop: a control must never
        # report "clean" on inputs it was unable to validate.
        result = ReviewResult(input_valid=False)
        if summary_json_path:
            reporting.write_summary_json(
                result, sla_days, summary_json_path, system_owners, input_checks
            )
        print("\nInput validation FAILED (see INPUT INTEGRITY above). Review aborted.")
        return result

    employees = loaders.load_terminations(
        cfg["hr_source"]["file"], cfg["hr_source"]["fields"]
    )

    accounts = []
    for system_cfg in cfg["systems"]:
        accounts.extend(loaders.load_accounts(system_cfg))

    identities, unmatched = correlation.correlate(employees, accounts)
    findings = detection.evaluate(identities, sla_days)

    result = ReviewResult(
        findings=findings,
        terminated_count=len(employees),
        account_count=len(accounts),
        matched_identities=len(identities),
        unmatched_employees=unmatched,
    )

    reporting.print_summary(result)

    if out_path:
        path = reporting.write_exception_log(findings, out_path)
        print(f"\nException log written to: {path}")

    if summary_json_path:
        path = reporting.write_summary_json(
            result, sla_days, summary_json_path, system_owners, input_checks
        )
        print(f"Summary JSON written to: {path}")

    if issue_md_path:
        with open(issue_md_path, "w", encoding="utf-8") as fh:
            fh.write(reporting.render_markdown_summary(result, sla_days, system_owners))
        print(f"Issue markdown written to: {issue_md_path}")

    return result


def _exit_code(result: ReviewResult, fail_on: str) -> int:
    """Exit code: 3 if inputs failed validation, 2 if a finding meets the
    fail-on severity, else 0."""
    if not result.input_valid:
        return 3
    threshold = _THRESHOLDS[fail_on]
    if threshold == 99:
        return 0
    for finding in result.findings:
        if _SEVERITY_RANK[finding.severity] <= threshold:
            return 2
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Termination access review POC")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--sla", type=int, default=None, help="Override SLA in days")
    parser.add_argument("--out", default=None, help="Path for CSV exception log")
    parser.add_argument(
        "--summary-json", default=None, help="Path for machine-readable JSON summary"
    )
    parser.add_argument(
        "--issue-md", default=None, help="Path for a Markdown summary (issue/alert body)"
    )
    parser.add_argument(
        "--fail-on",
        choices=list(_THRESHOLDS.keys()),
        default="none",
        help="Exit non-zero when a finding of this severity or worse exists",
    )
    args = parser.parse_args()
    result = run(args.config, args.sla, args.out, args.summary_json, args.issue_md)
    sys.exit(_exit_code(result, args.fail_on))


if __name__ == "__main__":
    main()
