import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_workflow_actions_are_pinned_and_revision_is_retained():
    workflow_texts = [
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    ]
    action_refs = re.findall(
        r"uses:\s+[^\s@]+@([^\s#]+)", "\n".join(workflow_texts)
    )

    assert action_refs
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in action_refs)
    access_review = (ROOT / ".github" / "workflows" / "access-review.yml").read_text(
        encoding="utf-8"
    )
    assert "CONTROL_CODE_REVISION: ${{ github.sha }}" in access_review
    assert "input_valid" in access_review


def test_documented_poc_frequency_matches_configuration():
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert config["control"]["frequency"] == "Weekdays (POC demonstration)"
    assert "weekday schedule" in readme
    assert "production cadence" in readme
