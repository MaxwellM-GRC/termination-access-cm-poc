"""Detection rules — the actual control logic.

Given correlated identities, raise a Finding for each way a terminated
employee's access falls outside policy. Rules are intentionally small and named
so an auditor can trace every exception back to a specific, testable assertion.

Rules:
  R1  OPEN_ACCESS          Account still ACTIVE after termination.
  R2  LATE_DEPROVISION     Account disabled, but after the SLA deadline.
  R3  POST_TERM_ACTIVITY   Login/activity dated after the termination date.
  R4  NAME_ONLY_MATCH      Account tied to the person by name alone — needs
                           manual confirmation before relying on the result.
"""

from __future__ import annotations

from datetime import date, timedelta

from .correlation import CorrelatedIdentity
from .models import AccountState, Finding, Severity, SystemAccount


def _evaluate_account(
    identity: CorrelatedIdentity,
    acct: SystemAccount,
    sla_days: int,
    name_only: bool,
) -> list[Finding]:
    emp = identity.employee
    findings: list[Finding] = []
    deadline = emp.termination_date + timedelta(days=sla_days)

    if name_only:
        findings.append(
            Finding(
                employee=emp,
                system=acct.system,
                account_id=acct.account_id,
                rule="R4_NAME_ONLY_MATCH",
                severity=Severity.INFO,
                detail=(
                    f"Account '{acct.username}' matched to {emp.full_name} by "
                    "name only (no email match). Confirm identity before relying "
                    "on any active/inactive conclusion below."
                ),
            )
        )

    # R1: still active after termination — the headline finding.
    if acct.state == AccountState.ACTIVE:
        findings.append(
            Finding(
                employee=emp,
                system=acct.system,
                account_id=acct.account_id,
                rule="R1_OPEN_ACCESS",
                severity=Severity.CRITICAL,
                detail=(
                    f"Account '{acct.username}' is still ACTIVE "
                    f"{(date.today() - emp.termination_date).days} days after "
                    f"termination ({emp.termination_date.isoformat()})."
                ),
            )
        )

    # R2: disabled, but late.
    if acct.state == AccountState.DISABLED and acct.deprovisioned_date:
        if acct.deprovisioned_date > deadline:
            days_late = (acct.deprovisioned_date - deadline).days
            findings.append(
                Finding(
                    employee=emp,
                    system=acct.system,
                    account_id=acct.account_id,
                    rule="R2_LATE_DEPROVISION",
                    severity=Severity.HIGH,
                    detail=(
                        f"Account disabled {acct.deprovisioned_date.isoformat()}, "
                        f"{days_late} day(s) past the {sla_days}-day SLA deadline "
                        f"of {deadline.isoformat()}."
                    ),
                    days_late=days_late,
                )
            )

    # R3: activity after the termination date, regardless of current state.
    if acct.last_activity and acct.last_activity > emp.termination_date:
        findings.append(
            Finding(
                employee=emp,
                system=acct.system,
                account_id=acct.account_id,
                rule="R3_POST_TERM_ACTIVITY",
                severity=Severity.CRITICAL,
                detail=(
                    f"Activity recorded {acct.last_activity.isoformat()}, after "
                    f"termination on {emp.termination_date.isoformat()}."
                ),
            )
        )

    return findings


def evaluate(
    identities: list[CorrelatedIdentity],
    sla_days: int,
) -> list[Finding]:
    findings: list[Finding] = []
    for identity in identities:
        for acct in identity.accounts:
            findings.extend(_evaluate_account(identity, acct, sla_days, False))
        for acct in identity.name_only_matches:
            findings.extend(_evaluate_account(identity, acct, sla_days, True))
    return findings
