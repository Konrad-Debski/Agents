# External sources and skill selection

Load when adding or updating external skills. The sources are submodules, and `skills/` holds symlinks to selected whole directories. This keeps the originals' references, scripts, metadata and licenses.

## Active set

| Source | Symlinks in `skills/` | Use |
| --- | --- | --- |
| [cursor/plugins](https://github.com/cursor/plugins) | `unslop` | Editing text |
| [DietrichGebert/ponytail](https://github.com/dietrichgebert/ponytail) | `ponytail`, `ponytail-audit`, `ponytail-review` | Small implementation scope, reviewing changes and auditing a whole repository |
| [mattpocock/skills](https://github.com/mattpocock/skills) | `grill-me`, `grilling`, `writing-for-agents`, `diagnosing-bugs`, `pr`, `retro`, `handoff`, `tdd`, `codebase-design` | Section requirements, agent instructions, bug diagnosis, PR descriptions, retrospectives, work handoff, TDD and module design |

`grilling` is a dependency of the current `grill-me`. Keeping only the alias would make its procedure impossible to run. `diagnosing-bugs` has its own script template, and `writing-for-agents` has a `SKILL-MECHANICS.md` file. The whole-directory symlink exposes these resources too.

The skills are general and apply to PHP, Twig, ACF, CSS and TypeScript in themes. They bring no ready conventions for a specific theme, so the agent still follows the project instructions.

The other skills are available in the sources but have no global symlinks. `ponytail` has a broad invocation description and, once started, stays active for the session. We keep the author's behavior. We do not add it to the main `AGENTS.md`.

In Claude Code and Codex the installer also installs Ponytail as a plugin with the author's commands from [INSTALL.md](../../.upstream/ponytail/INSTALL.md), using `.upstream/ponytail` as the marketplace for Claude Code. Codex uses the marketplace in `adapters/codex`, which points at the same submodule, because the author's Codex marketplace fetches his `main` branch. The plugin adds the author's hooks, so every session there starts with the Ponytail rules at the `full` level, and Claude Code passes them to subagents. `/ponytail default <level>` changes the starting level and `/ponytail off` turns the rules off for a session. The plugin exposes all six Ponytail skills next to the three symlinked ones. The hooks need `node` in the `PATH` of the harness. In Codex, open `/hooks` once and trust the Ponytail hooks. Cursor, OpenCode and VS Code get only the symlinked skills.

`pr` from `engineering/pr` sets the PR description content. The repository's own `create-pr` runs publishing and merging through the shared protocol, which `pr` reads when preparing a description.

From Matt's repository we do not expose tracker procedures, environment generators, training materials or experimental skills globally. We expose `tdd` for test-first work, and `codebase-design` for module design and as a reference for TDD. The user starts `retro` and `handoff`. Adding another skill requires checking its dependencies and justifying a separate use.

## Updating

The gitlink in the parent repository sets the exact approved version of each source. Installation and synchronization check out that version. To select a newer version, update the gitlink on a working branch and publish a pull request. The update branch comes from `.gitmodules`; without a `branch` entry Git uses the remote repository's default branch.

When the task is to update one source:

```bash
git -C ~/.agents submodule update --init --remote --checkout -- .upstream/ponytail
git -C ~/.agents submodule update --init --remote --checkout -- .upstream/mattpocock-skills
```

Run only the command for the source you are updating, on a working branch. Check the diff, metadata and paths of the selected skills. If upstream changed them, fix the symlinks and the `skills` list in `package.json`. Do not edit files inside the submodule. Commit the new gitlink and publish a pull request. After the changes, run `apply` to refresh the Claude Code links. [synchronization.md](../operations/synchronization.md) describes this process in detail.

Claude Code loads the Ponytail plugin from `.upstream/ponytail`, so the gitlink also sets the plugin version. Codex copies the plugin from the submodule when `codex plugin add ponytail@agents` runs. Synchronization runs `scripts/plugins.sh` after each downloaded commit, which refreshes the copy after a gitlink update.

Do not run Matt's `scripts/link-skills.sh` script, because it exposes a wider set than the one selected here. Fetching the repository into `.upstream/` alone does not install the whole package into the skill directory.

## Documentation split

From Matt's repository we adopt splitting documentation by type of work and stating when to use each piece of material. In this base the categories are `operations/`, `integrations/`, `contributing/` and `skills/`. We chose them for maintaining a shared configuration instead of copying his package's categories.

A file about a skill explains how it is chosen. The procedure stays in `SKILL.md`, so the documentation does not become a second copy of the instructions.
