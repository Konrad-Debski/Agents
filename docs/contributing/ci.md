# CI and pull request checks

Runtime installation still needs only the Python standard library. Development checks also need Node.js 26, a current stable Go installation in `PATH`, the packages in `tests/requirements.txt`, and the command-line tools. On Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tests/requirements.txt
npm ci --ignore-scripts --no-audit --no-fund
bash scripts/quality/install-tools.sh "$VIRTUAL_ENV/bin"
bash scripts/check.sh all
```

The installer installs only actionlint and Gitleaks. It uses actionlint's official download script for its latest release and builds Gitleaks with `GOBIN` set to the requested tool directory using `go install github.com/zricethezav/gitleaks/v8@latest`. This selects the latest release in the v8 module; Go is needed for installation, not for running the resulting executable. These are development tools, not requirements of the user timer. No agent client is downloaded or installed. Actions follow major-version tags such as `@v7`, receiving updates within that major version. Moving to a new major version requires a workflow change. npm dependencies use `package-lock.json`.

## Local commands

`scripts/check.sh` accepts these commands:

- `static`: Bash syntax, ShellCheck, Ruff correctness rules and actionlint.
- `repository`: MCP registry, synchronization scope and registered skill directories.
- `tests`: the integration suite and generated Hypothesis scenarios.
- `secrets [BASE HEAD]`: Gitleaks over the new commit history, including secrets deleted in a later commit. The default range is `origin/main..HEAD`.
- `all`: all of the above and the PR-policy tests.

Secret scanning covers commits, not uncommitted edits. CI blocks a merge after a secret has already been pushed; it cannot undo that exposure. The local guard remains useful before publishing. Never paste real credentials into test fixtures.

The `quality` job needs full Git history for `guard` and secret scanning, and initialized submodules for the skill catalog. It checks out recorded gitlinks and never refreshes upstream branches. Its Python tests create disposable local repositories and submodules.

## Pull request policy

Use a branch such as `fix/preserve-comments` and a matching title such as `fix: Preserve Comments`. The existing optional ticket format, `[ALTER-65] fix: Preserve Comments`, is supported. New non-merge commits must follow Conventional Commits. Actual merge commits are excluded by their parent count, not by their message text. Legacy commits already in the base branch are not linted.

The repository template follows the existing PR skill: `Summary`, `Evidence` with nonempty `Before` and `After`, and `Merge Danger` with `Door` and `Blast Radius`. HTML instructions do not count as content. The checker validates structure, not whether a human explanation is true. Use the actual GitHub job output as evidence and review the diff.

For a saved GitHub pull request event:

```bash
npm run check:pr -- /absolute/path/to/event.json
```

`ci.yml` runs static checks, repository validation, secret scanning and Python integration tests as steps of one `quality` job. They share one checkout, Python environment and tool installation. Python uses the latest stable Python 3 release, selected with `python-version: '3.x'` and `check-latest: true`. Each run resolves the current Gitleaks version from the Go module proxy and caches only its executable, keyed by that version, runner OS, architecture and installer script. On a cache miss, CI installs Go and builds that resolved version using `go install`. On a hit, it skips both steps. actionlint still uses its official download script on every run. Local installation defaults to `@latest`; `GITLEAKS_VERSION` lets CI build the version used in its cache key.

Both jobs use the single-CPU `ubuntu-slim` container. Synchronization tests simulate the systemd manager and use the installed `systemd-analyze` to validate generated units. CI requires this executable before running the suite so its absence cannot silently remove that validation. No running systemd instance, Docker daemon or privileged container is needed. The slimmer runner has fewer CPUs, so the first uncached Go compilation can take longer than on a full Ubuntu runner.

`pr-policy.yml` runs the PR-policy tests and checks metadata and new commits, including after a title or body edit. Both steps share its Node installation and npm dependencies, keeping Node out of `quality`. Neither workflow uses path filters, write tokens, live MCP credentials or deployment secrets. Tests run in disposable HOME and XDG directories. Existing OpenCode CLI tests are optional and skip when a suitable client is not already installed; adapter tests still run without it.

## Enable merge enforcement

Workflow files produce results; the repository ruleset makes them mandatory. `.github/rulesets/main.json` is the proposed ruleset. It retains signature, deletion and force-push protections, requires `quality` and `pr-policy` from the GitHub Actions app, requires an up-to-date branch and resolved review threads, and allows the repository's documented merge-commit method. Zero mandatory approvals supports the current single-maintainer workflow.

First publish a PR containing the workflows and obtain successful results. Then inspect the current ruleset for concurrent changes and apply the prepared configuration in GitHub's repository settings. The rule names must match the job names exactly. Do not add a bypass for the retired publishing timer. Ruleset changes are separate from merging workflow files and are not applied by CI.

The initial CI PR may contain older nonconforming commits inherited from a working branch. Fix only that PR's new commits; never rewrite `main` to satisfy the linter. Contributors must also meet GitHub's existing verified-signature requirement.

Before relying on enforcement, verify that a failing test, failed or skipped required job, invalid commit and empty PR description block merge. The automated negative tests exercise command failures through public interfaces. Check that a new push invalidates earlier results and an edited PR description reruns its policy job.

No deployment runs before merge. The existing download-only timer distributes approved `main` revisions to user machines.
