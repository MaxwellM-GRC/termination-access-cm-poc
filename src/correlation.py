"""Identity correlation layer.

The reason a single terminated employee can slip through is that each system
holds their account under a slightly different key: an email in one, a login
handle in another, a display name in a third. A per-system review sees only its
own slice. This layer stitches those slices back to one HR identity so the
review can ask a cross-application question: "does this terminated person still
have live access ANYWHERE?"

Matching is deliberately conservative and layered:
  1. Exact work-email match (highest confidence).
  2. Normalized full-name match (fallback for accounts missing/wrong email).
Anything that matches on name only is flagged so a human can confirm it; we
never want a false correlation to either raise or suppress a finding silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import SystemAccount, TerminatedEmployee


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().replace(".", " ").split())


@dataclass
class CorrelatedIdentity:
    employee: TerminatedEmployee
    accounts: list[SystemAccount] = field(default_factory=list)
    name_only_matches: list[SystemAccount] = field(default_factory=list)


def correlate(
    employees: list[TerminatedEmployee],
    accounts: list[SystemAccount],
) -> tuple[list[CorrelatedIdentity], list[TerminatedEmployee]]:
    """Return (correlated identities, employees with no account matched)."""

    by_email: dict[str, list[SystemAccount]] = {}
    by_name: dict[str, list[SystemAccount]] = {}
    for acct in accounts:
        if acct.email:
            by_email.setdefault(acct.email, []).append(acct)
        by_name.setdefault(_normalize_name(acct.display_name), []).append(acct)

    correlated: list[CorrelatedIdentity] = []
    unmatched: list[TerminatedEmployee] = []

    for emp in employees:
        identity = CorrelatedIdentity(employee=emp)
        seen: set[tuple[str, str]] = set()

        for acct in by_email.get(emp.email, []):
            identity.accounts.append(acct)
            seen.add((acct.system, acct.account_id))

        for acct in by_name.get(_normalize_name(emp.full_name), []):
            key = (acct.system, acct.account_id)
            if key not in seen:
                identity.name_only_matches.append(acct)
                seen.add(key)

        if identity.accounts or identity.name_only_matches:
            correlated.append(identity)
        else:
            unmatched.append(emp)

    return correlated, unmatched
