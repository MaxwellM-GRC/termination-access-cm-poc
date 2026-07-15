"""Tests for input integrity checks (IPE completeness/accuracy) and the
fail-closed exit behavior when inputs cannot be validated."""

from src.integrity import check_source, inputs_ok, validate_inputs
from src.main import _exit_code
from src.models import ReviewResult

FIELDS = {
    "account_id": "account_id",
    "email": "email",
    "state": "status",
    "last_activity": "last_login",
    "deprovisioned_date": "disabled_date",
}
HEADER = "account_id,email,status,last_login,disabled_date\n"


def _write(tmp_path, text):
    p = tmp_path / "extract.csv"
    p.write_text(text, encoding="utf-8")
    return str(p)


def _check(path):
    return check_source(
        name="Sys",
        path=path,
        fields=FIELDS,
        required_keys=["account_id", "email", "state"],
        date_keys=["last_activity", "deprovisioned_date"],
    )


def test_clean_source_passes(tmp_path):
    path = _write(tmp_path, HEADER + "A1,a@ex.example,Active,2026-05-01,\n")
    result = _check(path)
    assert result.ok
    assert result.row_count == 1
    assert result.blank_key_rows == 0
    assert result.unparsable_dates == 0


def test_missing_mapped_column_fails(tmp_path):
    # Drop the 'status' column that config maps to `state`.
    path = _write(tmp_path, "account_id,email,last_login,disabled_date\nA1,a@ex.example,,\n")
    result = _check(path)
    assert not result.ok
    assert "status" in result.missing_columns
    # Row counting is skipped once the file is mis-shaped.
    assert result.row_count == 0


def test_blank_required_key_is_counted(tmp_path):
    path = _write(tmp_path, HEADER + "A1,,Active,,\n")  # blank email
    result = _check(path)
    assert result.ok
    assert result.blank_key_rows == 1


def test_unparsable_date_is_counted(tmp_path):
    path = _write(tmp_path, HEADER + "A1,a@ex.example,Active,not-a-date,\n")
    result = _check(path)
    assert result.unparsable_dates == 1


def test_inputs_ok_aggregates(tmp_path):
    good = _check(_write(tmp_path, HEADER + "A1,a@ex.example,Active,,\n"))
    bad_path = tmp_path / "bad.csv"
    bad_path.write_text("account_id,email\nA1,a@ex.example\n", encoding="utf-8")
    bad = check_source(
        name="Bad",
        path=str(bad_path),
        fields=FIELDS,
        required_keys=["account_id", "email", "state"],
        date_keys=[],
    )
    assert inputs_ok([good]) is True
    assert inputs_ok([good, bad]) is False


def test_validate_inputs_over_real_config():
    import yaml
    cfg = yaml.safe_load(open("config.yaml"))
    results = validate_inputs(cfg)
    # HR roster + three systems, all structurally valid in the shipped data.
    assert len(results) == 4
    assert inputs_ok(results)


def test_exit_code_flags_input_failure():
    failed = ReviewResult(input_valid=False)
    assert _exit_code(failed, "none") == 3  # non-zero even when fail-on is none
