# Codex

Codex gets a symlink of the global instructions at `~/.codex/AGENTS.md`. It reads skills from `~/.agents/skills`. The adapter updates a marked MCP block in `~/.codex/config.toml` and keeps the other settings and comments.

When `CODEX_HOME` is set, the adapter uses that directory instead of `~/.codex`. With a custom location, select the harness explicitly in `local.json` and give the synchronization process the same variable.

The installer registers `adapters/codex` as the `agents` plugin marketplace and installs `ponytail@agents` from it. [upstream.md](../skills/upstream.md) describes the plugin and its updates.
