from grc_control_core import __version__, load_schema, stable_finding_id


def test_shared_control_core_release_is_explicitly_approved():
    assert __version__ == "0.1.0"
    assert stable_finding_id("ITGC-AD-001", "TA-01", "compatibility-check") == stable_finding_id(
        "ITGC-AD-001", "TA-01", "compatibility-check"
    )
    assert load_schema("finding-v1.schema.json")["title"] == "GRC Finding v1"
