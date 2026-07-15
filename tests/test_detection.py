"""Tests for the correlation layer and detection rules.

Run: python -m pytest -q
"""

from datetime import date

from src.correlation import correlate
from src.detection import evaluate
from src.models import AccountState, SystemAccount, TerminatedEmployee


def _emp(**kw):
    base = dict(
        employee_id="E1",
        full_name="Test Person",
        email="test.person@ex.example",
        department="Finance",
        job_title="Clerk",
        termination_date=date(2026, 5, 1),
        termination_type="Voluntary",
    )
    base.update(kw)
    return TerminatedEmployee(**base)


def _acct(**kw):
    base = dict(
        system="Sys",
        account_id="A1",
        username="tperson",
        email="test.person@ex.example",
        display_name="Test Person",
        state=AccountState.DISABLED,
        last_activity=None,
        deprovisioned_date=date(2026, 5, 2),
    )
    base.update(kw)
    return SystemAccount(**base)


def _rules(findings):
    return {f.rule for f in findings}


def test_correlation_matches_by_email():
    ids, unmatched = correlate([_emp()], [_acct()])
    assert len(ids) == 1
    assert not unmatched
    assert len(ids[0].accounts) == 1


def test_unmatched_employee_is_reported():
    ids, unmatched = correlate([_emp(email="nobody@ex.example", full_name="No One")], [_acct()])
    assert not ids
    assert len(unmatched) == 1


def test_name_only_match_is_flagged():
    acct = _acct(email="different@ex.example")
    ids, _ = correlate([_emp()], [acct])
    findings = evaluate(ids, sla_days=7)
    assert "R4_NAME_ONLY_MATCH" in _rules(findings)


def test_active_account_is_critical_open_access():
    ids, _ = correlate([_emp()], [_acct(state=AccountState.ACTIVE, deprovisioned_date=None)])
    findings = evaluate(ids, sla_days=7)
    assert "R1_OPEN_ACCESS" in _rules(findings)


def test_late_deprovision_flagged_and_dated():
    # Term 2026-05-01, SLA 7d -> deadline 2026-05-08; disabled 2026-05-20 = 12 late
    acct = _acct(deprovisioned_date=date(2026, 5, 20))
    ids, _ = correlate([_emp()], [acct])
    findings = [f for f in evaluate(ids, sla_days=7) if f.rule == "R2_LATE_DEPROVISION"]
    assert findings and findings[0].days_late == 12


def test_on_time_deprovision_is_clean():
    acct = _acct(deprovisioned_date=date(2026, 5, 3))
    ids, _ = correlate([_emp()], [acct])
    findings = evaluate(ids, sla_days=7)
    assert findings == []


def test_post_termination_activity_flagged():
    acct = _acct(last_activity=date(2026, 6, 1))
    ids, _ = correlate([_emp()], [acct])
    findings = evaluate(ids, sla_days=7)
    assert "R3_POST_TERM_ACTIVITY" in _rules(findings)
