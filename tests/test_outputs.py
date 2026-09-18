"""Tests for CLI exit-code logic and the JSON/Markdown summary outputs."""

import json
from datetime import date

from src.main import _exit_code
from src.models import (
    Finding,
    ReviewResult,
    Severity,
    TerminatedEmployee,
)
from src.reporting import render_markdown_summary, write_summary_json


def _emp():
    return TerminatedEmployee(
        employee_id="E1",
        full_name="Test Person",
        email="test.person@ex.example",
        department="Finance",
        job_title="Clerk",
        termination_date=date(2026, 5, 1),
        termination_type="Voluntary",
    )


def _finding(sev):
    return Finding(
        employee=_emp(),
        system="Sys",
        account_id="A1",
        rule="TA-01",
        severity=sev,
        detail="still active",
    )


def _result(*severities):
    return ReviewResult(
        findings=[_finding(s) for s in severities],
        terminated_count=1,
        account_count=1,
        matched_identities=1,
    )


def test_exit_code_none_never_fails():
    assert _exit_code(_result(Severity.CRITICAL), "none") == 0


def test_exit_code_fails_on_threshold_or_worse():
    assert _exit_code(_result(Severity.HIGH), "high") == 2
    assert _exit_code(_result(Severity.CRITICAL), "high") == 2


def test_exit_code_ignores_below_threshold():
    # Only an INFO finding should not trip a "high" gate.
    assert _exit_code(_result(Severity.INFO), "high") == 0


def test_exit_code_clean_result_passes():
    assert _exit_code(_result(), "critical") == 0


def test_summary_json_shape(tmp_path):
    path = tmp_path / "summary.json"
    control = {"id": "ITGC-AD-001", "name": "Termination Access"}
    responses = {"TA-01": {"remediation": "Disable access."}}
    result = _result(Severity.CRITICAL, Severity.HIGH)
    result.run_id = "AD-20260917T010203Z"
    write_summary_json(
        result, 7, str(path),
        control=control, rule_responses=responses,
    )
    data = json.load(open(path))
    assert data["totals"]["findings"] == 2
    assert data["counts_by_severity"]["critical"] == 1
    assert data["counts_by_severity"]["high"] == 1
    assert data["sla_days"] == 7
    assert data["run_id"] == "AD-20260917T010203Z"
    assert data["control"]["id"] == "ITGC-AD-001"
    assert data["findings"][0]["finding_id"].startswith("AD-")
    assert data["findings"][0]["remediation"] == "Disable access."


def test_markdown_summary_clean_message():
    md = render_markdown_summary(_result(), 7)
    assert "No exceptions" in md


def test_markdown_summary_lists_findings():
    md = render_markdown_summary(
        _result(Severity.CRITICAL), 7,
        rule_responses={"TA-01": {"remediation": "Disable access."}},
    )
    assert "TA-01" in md
    assert "| Severity |" in md
    assert "required response" in md


def test_owner_routing_in_summary_and_markdown(tmp_path):
    owners = {"Sys": "@sys-admin"}
    result = _result(Severity.CRITICAL, Severity.HIGH)

    path = tmp_path / "s.json"
    write_summary_json(result, 7, str(path), owners)
    data = json.load(open(path))
    # One system in findings -> one owner to notify, de-duplicated.
    assert data["owners_to_notify"] == [{"system": "Sys", "owner": "@sys-admin"}]
    assert data["findings"][0]["owner"] == "@sys-admin"

    md = render_markdown_summary(result, 7, owners)
    assert "Action required by:" in md
    assert "@sys-admin" in md
