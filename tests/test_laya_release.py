import pytest

from laya_release import bump_version, highest_bump, parse_version


def test_parse_version_strips_prefix():
    assert parse_version("v1.2.3", "v") == (1, 2, 3)


def test_parse_version_rejects_non_semver():
    with pytest.raises(ValueError):
        parse_version("v1.2", "v")


@pytest.mark.parametrize(
    "bump, expected",
    [("major", (2, 0, 0)), ("minor", (1, 3, 0)), ("patch", (1, 2, 4)), ("none", (1, 2, 3))],
)
def test_bump_version(bump, expected):
    assert bump_version((1, 2, 3), bump) == expected


def test_highest_bump_picks_largest_confident_decision():
    decisions = [
        {"bump": "patch", "confidence": 0.9},
        {"bump": "major", "confidence": 0.3},
        {"bump": "minor", "confidence": 0.8},
    ]
    assert highest_bump(decisions, 0.5, "patch") == "minor"


def test_highest_bump_uses_fallback_when_nothing_is_confident():
    assert highest_bump([{"bump": "major", "confidence": 0.1}], 0.5, "patch") == "patch"


def test_highest_bump_is_none_without_commits():
    assert highest_bump([], 0.5, "patch") == "none"
