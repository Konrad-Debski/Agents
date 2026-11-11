# Claude Code

Claude Code gets a symlink at `~/.claude/CLAUDE.md` and one link per skill in `~/.claude/skills`. The adapter merges the global `mcpServers` in `~/.claude.json` and keeps the rest of the data. When `CLAUDE_CONFIG_DIR` is set, the adapter uses that configuration directory. With custom directories, select the harness explicitly in `local.json` and give the synchronization process the same variables.
