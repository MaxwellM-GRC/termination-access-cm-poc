"""Input integrity checks — completeness and accuracy of the source data (IPE).

Before the review logic runs, this module inspects each raw extract so the run
can make an explicit statement about the completeness and accuracy of its inputs,
the way an auditor establishes reliance on Information Produced by the Entity.

Each source is checked for:
  * missing_columns    — a column the config maps is absent from the file
                         (schema drift). This is a hard stop: the output cannot
                         be relied on, so the run refuses to proceed.
  * row_count          — records read (completeness of the population).
  * blank_key_rows     — rows missing a required key field (accuracy/usability).
  * unparsable_dates   — non-empty date fields that do not parse (accuracy).

These are lightweight application-level input edit checks (an ITAC concept). They
surface the condition of the data rather than cleaning it, so the control's
reliability is transparent instead of assumed. Only missing mapped columns fail
the run; blank keys and bad dates are reported as data-quality flags because the
correlation and detection layers already handle them safely per record.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SourceIntegrity:
    """Integrity findings for a single source extract."""

    name: str
    row_count: int
    missing_columns: list[str]
    blank_key_rows: int
    unparsable_dates: int

    @property
    def ok(self) -> bool:
        """True when the file is structurally usable (no mapped column missing)."""
        return not self.missing_columns

    def as_dict(self) -> dict:
        return {
            "source": self.name,
            "row_count": self.row_count,
            "missing_columns": self.missing_columns,
            "blank_key_rows": self.blank_key_rows,
            "unparsable_dates": self.unparsable_dates,
            "ok": self.ok,
        }


def _is_valid_date(value: str) -> bool:
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def check_source(
    name: str,
    path: str,
    fields: dict,
    required_keys: list[str],
    date_keys: list[str],
) -> SourceIntegrity:
    """Inspect one extract. `required_keys` and `date_keys` are logical field
    names (keys of `fields`); the file is read using the mapped column names."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []

        # Every column the config maps must physically exist in the file.
        missing = sorted(
            {fields[k] for k in fields if fields[k] not in header}
        )
        if missing:
            # Cannot trust counts from a mis-shaped file; stop at the schema check.
            return SourceIntegrity(name, 0, missing, 0, 0)

        row_count = 0
        blank_key_rows = 0
        unparsable_dates = 0
        for row in reader:
            row_count += 1
            if any(not (row.get(fields[k]) or "").strip() for k in required_keys):
                blank_key_rows += 1
            for dk in date_keys:
                value = (row.get(fields[dk]) or "").strip()
                if value and not _is_valid_date(value):
                    unparsable_dates += 1

    return SourceIntegrity(name, row_count, [], blank_key_rows, unparsable_dates)


def validate_inputs(cfg: dict) -> list[SourceIntegrity]:
    """Return an integrity record for the HR roster and each system extract."""
    results: list[SourceIntegrity] = []

    hr = cfg["hr_source"]
    results.append(
        check_source(
            name="HR roster",
            path=hr["file"],
            fields=hr["fields"],
            required_keys=["employee_id", "full_name", "email", "termination_date"],
            date_keys=["termination_date"],
        )
    )

    for system_cfg in cfg["systems"]:
        results.append(
            check_source(
                name=system_cfg["name"],
                path=system_cfg["file"],
                fields=system_cfg["fields"],
                required_keys=["account_id", "email", "state"],
                date_keys=["last_activity", "deprovisioned_date"],
            )
        )

    return results


def inputs_ok(integrity: list[SourceIntegrity]) -> bool:
    """True only if every source passed its structural (schema) check."""
    return all(source.ok for source in integrity)
