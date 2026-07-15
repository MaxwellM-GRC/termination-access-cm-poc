"""Core data structures for the termination access review.

Everything downstream (correlation, detection, reporting) speaks in these
normalized objects, so each source system only needs a thin adapter that maps
its own quirky schema into a common shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class AccountState(str, Enum):
    """Normalized account state, mapped from each system's own vocabulary."""

    ACTIVE = "active"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    INFO = "info"


@dataclass(frozen=True)
class TerminatedEmployee:
    """A record from the HR system's termination roster (source of truth)."""

    employee_id: str
    full_name: str
    email: str
    department: str
    job_title: str
    termination_date: date
    termination_type: str


@dataclass(frozen=True)
class SystemAccount:
    """A normalized account from any downstream application."""

    system: str
    account_id: str
    username: str
    email: str
    display_name: str
    state: AccountState
    last_activity: Optional[date]
    deprovisioned_date: Optional[date]


@dataclass
class Finding:
    """A single exception raised against a terminated employee's access."""

    employee: TerminatedEmployee
    system: str
    account_id: str
    rule: str
    severity: Severity
    detail: str
    days_late: Optional[int] = None

    def as_row(self) -> dict:
        return {
            "employee_id": self.employee.employee_id,
            "full_name": self.employee.full_name,
            "department": self.employee.department,
            "termination_date": self.employee.termination_date.isoformat(),
            "termination_type": self.employee.termination_type,
            "system": self.system,
            "account_id": self.account_id,
            "rule": self.rule,
            "severity": self.severity.value,
            "days_late": "" if self.days_late is None else self.days_late,
            "detail": self.detail,
        }


@dataclass
class ReviewResult:
    """Full output of a review run: findings plus population reconciliation."""

    findings: list[Finding] = field(default_factory=list)
    terminated_count: int = 0
    account_count: int = 0
    matched_identities: int = 0
    unmatched_employees: list[TerminatedEmployee] = field(default_factory=list)
    # False when input integrity checks failed and the review was not run.
    input_valid: bool = True

    @property
    def population_reconciled(self) -> bool:
        """Every terminated employee is accounted for: matched or explicitly not."""
        return (
            self.matched_identities + len(self.unmatched_employees)
            == self.terminated_count
        )
