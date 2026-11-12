# CI and pull request checks

Runtime installation needs only the Python standard library. Development checks need the pinned packages in `tests/requirements.txt`, which include the ShellCheck and actionlint executables. On Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tests/requirements.txt
bash scripts/check.sh all
```

## Local commands

`scripts/check.sh` accepts these commands:

- `static`: Bash syntax, ShellCheck, Ruff correctness rules and actionlint.
- `repository`: MCP registry, synchronization scope, secrets in tracked files and new commits, and registered skill directories.
- `tests`: the integration suite. It fails when no test runs.
- `commits [BASE HEAD]`: Conventional Commits subjects of new non-merge commits. The default range is `origin/main..HEAD`.
- `all`: all of the above.

## Secrets

GitHub secret scanning with push protection rejects a push that contains a known token format. `agents.py guard` also checks tracked files and new commits with its own patterns, including a secret deleted in a later commit. Never paste real credentials into test fixtures.

## CI

`ci.yml` runs every command in one `quality` job on `ubuntu-26.04`. The job needs full Git history for `guard` and the commit check, and initialized submodules for the skill catalog. It checks out the recorded gitlinks and never refreshes upstream branches. pip packages are cached by `tests/requirements.txt`.

Synchronization tests simulate the systemd manager and validate generated units with the installed `systemd-analyze`. CI requires this executable, so its absence cannot silently skip that validation. The OpenCode CLI tests skip when the client is not installed. Tests run in disposable HOME and XDG directories and use no credentials.

## Pull requests

Use a branch such as `fix/preserve-comments` and a matching title such as `fix: Preserve Comments`. Fill in the repository template: `Summary`, `Evidence` with `Before` and `After`, and `Merge Danger` with `Door` and `Blast Radius`. CI does not check the description.

`.github/rulesets/main.json` is the proposed ruleset. It keeps signature, deletion and force-push protections, requires `quality`, an up-to-date branch and resolved review threads, and allows merge commits. Apply it in the repository settings; CI does not apply it. The required check name must match the job name.

No deployment runs before merge. The download-only timer distributes approved `main` revisions to user machines.
