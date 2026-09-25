import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "docs" / "poc_product_profile.md"


def test_profile_covers_configured_rules_and_human_boundary():
    profile = PROFILE.read_text(encoding="utf-8")
    normalized_profile = " ".join(profile.split())
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))

    assert config["control"]["id"] in profile
    assert set(config["rule_responses"]).issubset(set(re.findall(r"TA-\d{2}", profile)))
    assert "Automation does" in profile
    assert "People decide" in profile
    assert "not a compliance conclusion" in normalized_profile


def test_mapping_ids_are_unique_and_referenced_by_detailed_documents():
    profile = PROFILE.read_text(encoding="utf-8")
    mapping_ids = re.findall(r"`(MAP-TA-\d{2})`", profile)
    assert len(mapping_ids) == 5
    assert len(set(mapping_ids)) == len(mapping_ids)

    narrative = (ROOT / "docs" / "control_narrative.md").read_text(encoding="utf-8")
    governance = (ROOT / "docs" / "governance_and_controls.md").read_text(encoding="utf-8")
    for mapping_id in mapping_ids:
        assert mapping_id in narrative
        assert mapping_id in governance


def test_profile_names_reviewable_evidence_outputs_and_approved_core_release():
    profile = PROFILE.read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    for evidence_term in ("source validation", "run summary", "exception log"):
        assert evidence_term in profile.lower()
    assert "grc-control-core.git@v0.3.0" in requirements
