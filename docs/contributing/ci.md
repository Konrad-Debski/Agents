# CI and pull request checks

Runtime installation needs only the Python standard library. Development checks need the pinned packages in `tests/requirements.txt`, which include the ShellCheck and actionlint executables, and Node.js 26 for commitlint. On Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tests/requirements.txt
npm ci --ignore-scripts --no-audit --no-fund
bash scripts/check.sh all
```

## Local commands

`scripts/check.sh` accepts these commands:

- `static`: Bash syntax, ShellCheck, Ruff correctness rules and actionlint.
- `repository`: MCP registry, synchronization scope, secrets in tracked files and new commits, and registered skill directories.
- `tests`: the integration suite. It fails when no test runs. The commitlint test skips without `node_modules`.
- `commits [BASE HEAD]`: commitlint with `commitlint.config.mjs` on each new non-merge commit. The default range is `origin/main..HEAD`. Older commits on `main` do not follow the convention and are not checked.
- `all`: all of the above.

## Secrets

GitHub secret scanning with push protection rejects a push that contains a known token format. `agents.py guard` also checks tracked files and new commits with its own patterns, including a secret deleted in a later commit. Never paste real credentials into test fixtures.

## CI

`ci.yml` runs every command except `commits` in one `quality` job on `ubuntu-26.04`. The job needs full Git history for `guard`, Node.js for the commitlint tests, and initialized submodules for the skill catalog. It checks out the recorded gitlinks and never refreshes upstream branches. pip packages are cached by `tests/requirements.txt` and npm packages by `package-lock.json`.

Synchronization tests simulate the systemd manager and validate generated units with the installed `systemd-analyze`. CI requires this executable, so its absence cannot silently skip that validation. The OpenCode CLI tests skip when the client is not installed. Tests run in disposable HOME and XDG directories and use no credentials.

## Pull requests

Use a branch such as `fix/preserve-comments` and a matching title such as `fix: Preserve Comments`. The `commit-msg` hook in `.githooks` checks each commit message locally; [maintenance.md](maintenance.md) shows how to enable it. Fill in the repository template: `Summary`, `Evidence` with `Before` and `After`, and `Merge Danger` with `Door` and `Blast Radius`.

`pr-policy.yml` runs `scripts/quality/pr_policy.py` in the `pr-policy` job when a pull request opens, gets new commits or has its title or description edited. The script checks the title with commitlint and `commitlint.config.mjs`, the same rules that `check.sh commits` applies to commit messages. The job then runs `check.sh commits` on the new commits of the pull request. The script also requires a `type/kebab-case` branch whose type matches the title, `main` as the base, and the filled template sections.

Dependabot pull requests skip the `pr-policy` job. Dependabot picks its own branch names and writes commit bodies with lines longer than commitlint allows. GitHub counts a skipped required job as passed, and `quality` still runs.

`.github/rulesets/main.json` is the proposed ruleset. It keeps signature, deletion and force-push protections, requires `quality` and `pr-policy`, an up-to-date branch and resolved review threads, and allows merge commits. Apply it in the repository settings; CI does not apply it. Each required check name must match its job name.

No deployment runs before merge. The download-only timer distributes approved `main` revisions to user machines.

## Dependency updates

`.github/dependabot.yml` makes Dependabot open update pull requests once a month. It covers the `.upstream/` submodules, GitHub Actions, the npm packages in `package-lock.json` and the pip packages in `tests/requirements.txt`. Each submodule gets its own pull request. Actions, npm and pip updates are grouped into one pull request per ecosystem, and Dependabot waits 7 days after a release before proposing it. Review a submodule update as described in [upstream.md](../skills/upstream.md#updating). Synchronization ignores the pull requests until they are merged into `main`.
