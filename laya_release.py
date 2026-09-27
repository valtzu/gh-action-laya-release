import json
import os
import re
import subprocess
import sys
import uuid

BUMPS = ("none", "patch", "minor", "major")

LABEL_BUMPS = {"A": "major", "B": "minor", "C": "patch"}

QUESTIONS = {
    "bump": {
        "type": "choice",
        "instructions": "What kind of change does this commit make?",
        "criteria": {
            "A": "breaks existing users: removes or renames API, flags or behavior",
            "B": "adds a new feature, option or command",
            "C": "fixes a bug, or changes only docs, dependencies, tests or internals",
        },
    },
    "scope": {
        "type": "choice",
        "instructions": "Which files does this commit change?",
        "criteria": {
            "A": "source code or dependencies",
            "B": "only documentation, tests or CI configuration",
        },
    },
}

MAX_LISTED_FILES = 20

TAG_PATTERN = re.compile(r"^(v?)(\d+)\.(\d+)\.(\d+)$")


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def parse_tag(tag):
    match = TAG_PATTERN.match(tag)
    if not match:
        return None
    prefix, *version = match.groups()
    return prefix, tuple(int(part) for part in version)


def latest_tag(tags):
    versions = {tag: parsed for tag in tags if (parsed := parse_tag(tag))}
    return max(versions, key=lambda tag: versions[tag][1], default=None)


def commits_since(since_tag, head):
    revision_range = f"{since_tag}..{head}" if since_tag else head
    log = git("log", "--no-merges", "--name-only", "--format=%x1e%H%x1f%B%x1f", revision_range)
    commits = []
    for record in log.split("\x1e"):
        if record.strip():
            sha, message, files = record.split("\x1f")
            commits.append({"sha": sha.strip(), "message": message.strip(), "files": files.split()})
    return commits


def describe(commit):
    if not commit["files"]:
        return commit["message"]
    files = "\n".join(commit["files"][:MAX_LISTED_FILES])
    return f"{commit['message']}\n\nChanged files:\n{files}"


def decide(answers):
    if answers["scope"]["choice"] == "B":
        return "none", answers["scope"]["answer_confidence"]
    return LABEL_BUMPS[answers["bump"]["choice"]], answers["bump"]["answer_confidence"]


def bump_version(version, bump):
    major, minor, patch = version
    if bump == "major":
        return major + 1, 0, 0
    if bump == "minor":
        return major, minor + 1, 0
    if bump == "patch":
        return major, minor, patch + 1
    return version


def format_version(version):
    return ".".join(str(part) for part in version)


def highest_bump(decisions, min_confidence, fallback):
    confident = [d["bump"] for d in decisions if d["confidence"] >= min_confidence]
    if not decisions:
        return "none"
    if not confident:
        return fallback
    return max(confident, key=BUMPS.index)


def classify(commits, model):
    from laya import Router

    requests = [{"state": describe(c), "questions": QUESTIONS, "model": model} for c in commits]
    results = Router().predict_batch(requests) if requests else []
    decisions = []
    for commit, result in zip(commits, results):
        bump, confidence = decide(result["answers"])
        decisions.append(
            {
                "sha": commit["sha"],
                "subject": commit["message"].splitlines()[0],
                "bump": bump,
                "confidence": confidence,
            }
        )
    return decisions


CHANGELOG_SECTIONS = {
    "major": "Breaking changes",
    "minor": "Features",
    "patch": "Fixes and maintenance",
    "none": "Other changes",
}


def changelog(decisions):
    sections = []
    for bump, heading in CHANGELOG_SECTIONS.items():
        entries = [f"- {d['subject']} ({d['sha'][:7]})" for d in decisions if d["bump"] == bump]
        if entries:
            sections.append("\n".join([f"### {heading}", *entries]))
    return "\n\n".join(sections)


def write_outputs(outputs):
    with open(os.environ["GITHUB_OUTPUT"], "a") as file:
        for key, value in outputs.items():
            delimiter = f"EOF_{uuid.uuid4().hex}"
            file.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def escape_cell(text):
    return text.replace("|", "\\|")


def write_summary(decisions, outputs):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = [
        f"### {outputs['current-version']} → {outputs['next-version']} ({outputs['bump']})",
        "",
        "| Commit | Subject | Bump | Confidence |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| `{d['sha'][:7]}` | {escape_cell(d['subject'])} | {d['bump']} | {d['confidence']:.2f} |"
        for d in decisions
    ]
    with open(path, "a") as file:
        file.write("\n".join(lines) + "\n")


def main():
    head = os.environ["INPUT_HEAD"]
    model = os.environ["INPUT_MODEL"] or None
    min_confidence = float(os.environ["INPUT_MIN_CONFIDENCE"])
    fallback = os.environ["INPUT_FALLBACK_BUMP"]
    if fallback not in BUMPS:
        sys.exit(f"fallback-bump must be one of {', '.join(BUMPS)}")

    tag = latest_tag(git("tag", "--merged", head).split())
    prefix, current = parse_tag(tag) if tag else ("v", (0, 0, 0))
    decisions = classify(commits_since(tag, head), model)
    bump = highest_bump(decisions, min_confidence, fallback)
    next_version = format_version(bump_version(current, bump))

    outputs = {
        "previous-tag": tag or "",
        "current-version": format_version(current),
        "bump": bump,
        "next-version": next_version,
        "next-tag": f"{prefix}{next_version}",
        "decisions": json.dumps(decisions),
        "changelog": changelog(decisions),
    }
    write_outputs(outputs)
    write_summary(decisions, outputs)
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
