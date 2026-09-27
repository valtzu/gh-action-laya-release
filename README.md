# Laya release bump

GitHub Action that decides whether the next release is **major**, **minor** or **patch** by classifying each commit message since the latest version tag (`1.2.3` or `v1.2.3`) with [laya](https://github.com/NandhaKishorM/laya).

Each commit message, together with its changed file names, gets one of four labels; the highest confident one wins:

| Bump | Meaning |
|---|---|
| major | breaks existing users: removes or renames API, flags or behavior |
| minor | adds a new feature, option or command |
| patch | fixes a bug, or changes dependencies or internals |
| none | changes only documentation, tests or CI configuration |

Decisions below `min-confidence` are ignored. If commits exist but none is confident, `fallback-bump` is used. Without commits since the tag, or when every confident decision is `none`, the bump is `none` and no release should be made.

## Usage

```yaml
on:
  workflow_dispatch:

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0

      - id: bump
        uses: valtzu/gh-action-laya-release@main

      - if: steps.bump.outputs.bump != 'none'
        run: gh release create "${{ steps.bump.outputs.next-tag }}" --notes "$CHANGELOG" --generate-notes
        env:
          GH_TOKEN: ${{ github.token }}
          CHANGELOG: ${{ steps.bump.outputs.changelog }}
```

`fetch-depth: 0` is required so tags and history are available.

## Inputs

| Name | Default | Description |
|---|---|---|
| `head` | `HEAD` | Revision to compare against the latest version tag |
| `model` | `english` | Laya checkpoint (`english`, `multilingual`, `typed-decisions`); empty lets the router pick |
| `min-confidence` | `0.4` | Ignore decisions below this confidence |
| `fallback-bump` | `patch` | Bump when no decision is confident |
| `laya-version` | `0.3.21` | laya package version |
| `python-version` | `3.12` | Python version |

## Outputs

| Name | Description |
|---|---|
| `previous-tag` | Highest version tag reachable from `head`, empty if none |
| `current-version` | Version of that tag, `0.0.0` if none |
| `bump` | `none`, `patch`, `minor` or `major` |
| `next-version` | Next version without prefix |
| `next-tag` | Next version with the previous tag's prefix (`v` if no previous tag) |
| `decisions` | JSON array of per-commit decisions |
| `changelog` | Markdown list of commit subjects grouped into breaking changes, features, and fixes |

A per-commit table is also written to the job summary.

## Caveats

Laya is a small zero-shot classifier, not an LLM. The label wording was picked because it classified a handful of sample commits correctly on the `english` checkpoint; other checkpoints and wordings did noticeably worse. Review the job summary before trusting a major bump.
