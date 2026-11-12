# Repository maintenance

The repository is installed as `~/.agents`. The global `AGENTS.md` is the knowledge map for all projects. Load this document when changing the `~/.agents` base itself.

- On `main`, the `agents-sync` service downloads approved changes every 15 minutes. It stops on local edits or unpublished commits and skips other branches. Publish changes through a pull request.
- Do not run the installer from a worktree against the real HOME as part of testing. The tests have an isolated environment.
- The installer and synchronization check out the submodule versions recorded in the repository. Update gitlinks through a pull request. Do not edit upstream files. Expose only the selected skills listed in [upstream.md](../skills/upstream.md).
- A new top-level directory needs a change to `.gitignore` and to the scope list in `scripts/agents.py`.
- Adding a harness needs a manifest in `adapters/`, support for its format in `scripts/agents.py`, tests and a description of its limits. A manifest alone does not add support for an arbitrary new format.
- Skill changes must account for path portability and dependencies on a specific harness's tools. Do not silently change the publishing procedures inside skills.

Before handing off changes, run `bash scripts/check.sh all`. [CI and pull request checks](ci.md) describes dependency setup and the required GitHub results.

On a development machine, enable the commit message check once:

```bash
npm ci
git config core.hooksPath .githooks
```

The `commit-msg` hook runs commitlint. Without `node_modules` it only prints a warning, so machines that only synchronize need no Node.js. `git commit --no-verify` skips the hook; CI checks the same commits again.

Install on the target computer with `bash ~/.agents/install.sh`, without `sudo`. [installation.md](../operations/installation.md) lists the current requirements.

## Commits and branches

- Write commit messages following [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), for example `chore: add development skills`. Put an optional scope in parentheses after the type, and mark breaking changes with `!` or a `BREAKING CHANGE:` footer.
- Name working branches `<type>/<kebab-case-description>`, for example `chore/add-mattpocock-development-skills`. The prefix matches the change type, following the repository convention used in the [PR publishing protocol](../../skills/create-pr/references/workflow.md).

## Knowledge organization

Agents load the main `AGENTS.md` in every project. Put only guidance shared across projects there. Keep the maintenance rules for the `~/.agents` repository, its Git conventions and links to its documentation in `docs/`. Do not add them to the global `AGENTS.md`, not even as links with a read condition that applies only when working in this repository.

[context-management.md](context-management.md) describes how to split instructions, documentation and skills, and the language rule for Markdown in this repository. Read it before changing `AGENTS.md`, adding a skill, editing documentation or reorganizing knowledge.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Install the development dependencies described in [ci.md](ci.md) first. The tests use temporary home directories, local remote Git repositories and a systemd stub. They do not change the user's live configuration.

If OpenCode 2 is already installed, optional local tests run `opencode debug config --standalone` with isolated HOME and XDG directories. They check JSON and JSONC configuration and OpenCode 1 format compatibility. MCP servers in these configuration copies are disabled, and the tests do not run a model. Without a compatible client the CLI tests skip; the adapter tests still run. Development tooling and CI never install OpenCode.
