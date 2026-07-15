"""Load and normalize the HR roster and each system's account extract.

Each source system has its own column names and its own words for "active" vs
"disabled". These loaders push all of that variation into the common model so
nothing downstream has to know or care which system a record came from.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from typing import Optional

from .models import AccountState, SystemAccount, TerminatedEmployee


def _parse_date(value: Optional[str]) -> Optional[date]:
    """Parse an ISO date, tolerating blanks. Extend here for other formats."""
    if not value or not value.strip():
        return None
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


def load_terminations(path: str, fields: dict) -> list[TerminatedEmployee]:
    employees: list[TerminatedEmployee] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            employees.append(
                TerminatedEmployee(
                    employee_id=row[fields["employee_id"]].strip(),
                    full_name=row[fields["full_name"]].strip(),
                    email=row[fields["email"]].strip().lower(),
                    department=row[fields["department"]].strip(),
                    job_title=row[fields["job_title"]].strip(),
                    termination_date=_parse_date(row[fields["termination_date"]]),
                    termination_type=row[fields["termination_type"]].strip(),
                )
            )
    return employees


def _normalize_state(raw: str, active_values, disabled_values) -> AccountState:
    raw = (raw or "").strip()
    if raw in active_values:
        return AccountState.ACTIVE
    if raw in disabled_values:
        return AccountState.DISABLED
    return AccountState.UNKNOWN


def load_accounts(system_cfg: dict) -> list[SystemAccount]:
    fields = system_cfg["fields"]
    accounts: list[SystemAccount] = []
    with open(system_cfg["file"], newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            accounts.append(
                SystemAccount(
                    system=system_cfg["name"],
                    account_id=row[fields["account_id"]].strip(),
                    username=row[fields["username"]].strip(),
                    email=row[fields["email"]].strip().lower(),
                    display_name=row[fields["display_name"]].strip(),
                    state=_normalize_state(
                        row[fields["state"]],
                        system_cfg.get("active_values", []),
                        system_cfg.get("disabled_values", []),
                    ),
                    last_activity=_parse_date(row.get(fields["last_activity"])),
                    deprovisioned_date=_parse_date(
                        row.get(fields["deprovisioned_date"])
                    ),
                )
            )
    return accounts
