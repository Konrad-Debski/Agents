# Claude Code

Claude Code gets a symlink at `~/.claude/CLAUDE.md` and one link per skill in `~/.claude/skills`. The adapter merges the global `mcpServers` in `~/.claude.json` and keeps the rest of the data. When `CLAUDE_CONFIG_DIR` is set, the adapter uses that configuration directory. With custom directories, select the harness explicitly in `local.json` and give the synchronization process the same variables.

When `claude` is in `PATH`, `scripts/plugins.sh` also adds Anthropic's [official marketplace](https://github.com/anthropics/claude-plugins-official) and installs `php-lsp` and `typescript-lsp` from it. With them Claude Code gets go-to-definition, references and diagnostics for `.php`, `.ts` and `.js` files. The plugins only start the language servers, so install the servers once on each computer:

```bash
npm install -g intelephense typescript-language-server typescript
```

Without the servers, `/plugin` reports an `Executable not found in $PATH` error and Claude Code works as before. Intelephense is free for these features; its premium license is optional. The marketplace follows Anthropic's `main` branch, not a gitlink, so `claude plugin marketplace update claude-plugins-official` updates these two plugins.
