import pytest

from laya_release import bump_version, changelog, decide, describe, highest_bump, latest_tag, parse_tag


@pytest.mark.parametrize("tag, expected", [("v1.2.3", ("v", (1, 2, 3))), ("1.2.3", ("", (1, 2, 3)))])
def test_parse_tag(tag, expected):
    assert parse_tag(tag) == expected


@pytest.mark.parametrize("tag", ["v1.2", "release-1.2.3", "1.2.3-rc1"])
def test_parse_tag_ignores_non_semver(tag):
    assert parse_tag(tag) is None


def test_latest_tag_picks_highest_version_regardless_of_prefix():
    assert latest_tag(["v1.9.0", "1.10.0", "nightly", "v1.2.3"]) == "1.10.0"


def test_latest_tag_is_none_without_version_tags():
    assert latest_tag(["nightly"]) is None


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


def test_changelog_groups_subjects_by_bump():
    decisions = [
        {"sha": "a" * 40, "subject": "Fix crash", "bump": "patch"},
        {"sha": "b" * 40, "subject": "Add option", "bump": "minor"},
    ]
    assert changelog(decisions) == "### Features\n- Add option (bbbbbbb)\n\n### Fixes and maintenance\n- Fix crash (aaaaaaa)"


def test_highest_bump_is_none_when_only_non_release_changes_are_confident():
    assert highest_bump([{"bump": "none", "confidence": 0.8}], 0.5, "patch") == "none"


def test_decide_skips_release_for_docs_tests_or_ci_only():
    answers = {
        "bump": {"choice": "C", "answer_confidence": 0.6},
        "scope": {"choice": "B", "answer_confidence": 0.7},
    }
    assert decide(answers) == ("none", 0.7)


def test_decide_uses_bump_label_for_source_changes():
    answers = {
        "bump": {"choice": "B", "answer_confidence": 0.6},
        "scope": {"choice": "A", "answer_confidence": 0.9},
    }
    assert decide(answers) == ("minor", 0.6)


def test_describe_lists_changed_files():
    commit = {"message": "Update README", "files": ["README.md"]}
    assert describe(commit) == "Update README\n\nChanged files:\nREADME.md"
