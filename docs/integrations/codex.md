# Codex

Codex gets a symlink of the global instructions at `~/.codex/AGENTS.md`. It reads skills from `~/.agents/skills`. The adapter updates a marked block for MCP servers and skill exclusions in `~/.codex/config.toml` and keeps the other settings and comments.

When `CODEX_HOME` is set, the adapter uses that directory instead of `~/.codex`. With a custom location, select the harness explicitly in `local.json` and give the synchronization process the same variable.

The installer registers `adapters/codex` as the `agents` marketplace and installs `ponytail@agents` and `modern-web-guidance@agents` from it. Both plugin directories are symlinks to the pinned submodules. If an older install left a separate `googlechrome` marketplace, the installer removes it along with `modern-web-guidance@googlechrome`. [upstream.md](../skills/upstream.md) describes plugin updates.

The adapter's `plugin_skills` list covers all six Ponytail skills. `apply` writes a `[[skills.config]]` entry with `enabled = false` for each shared `SKILL.md`, using the checkout's absolute path. Codex resolves symlinks when matching these paths. The plugin's separate copies stay enabled, and the shared files remain available to other harnesses. Restart Codex after the first apply. If the plugin is disabled or missing, the shared copies stay disabled. Removing Codex from `local.json` removes only the managed exclusions.
