import copy
import json

import pytest

import config
from manifest import ManifestError, validate_plan
from plan import plan_mock

DEMO = json.loads((config.ROOT / "projects" / "demo" / "plan.json").read_text())


def test_demo_plan_is_valid() -> None:
    plan = validate_plan(copy.deepcopy(DEMO))
    assert [s["id"] for s in plan["scenes"]] == ["s01", "s02", "s03", "s04"]


def test_defaults_are_filled() -> None:
    plan = validate_plan({"title": "T", "scenes": [{"narration": "Hello."}]})
    scene = plan["scenes"][0]
    assert plan["format"] == config.DEFAULT_FORMAT
    assert scene["id"] == "s01"
    assert scene["visual"] == {"kind": "card"}
    assert scene["transition"] == "cut"


@pytest.mark.parametrize("bad", [
    {"scenes": [{"narration": "x"}]},
    {"title": "T", "scenes": []},
    {"title": "T", "format": "cinema", "scenes": [{"narration": "x"}]},
    {"title": "T", "scenes": [{"narration": "x", "visual": {"kind": "video"}}]},
    {"title": "T", "scenes": [{"visual": {"kind": "card"}}]},
    {"title": "T", "scenes": [{"id": "a", "narration": "x"},
                              {"id": "a", "narration": "y"}]},
])
def test_invalid_plans_are_rejected(bad: dict) -> None:
    with pytest.raises(ManifestError):
        validate_plan(bad)


def test_mock_planner_makes_a_valid_plan() -> None:
    plan = validate_plan(plan_mock({"slug": "x", "prompt": "One. Two! Three?"}))
    assert len(plan["scenes"]) == 4
    assert plan["scenes"][0]["visual"]["kind"] == "title"
