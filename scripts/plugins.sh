#!/usr/bin/env bash
set -euo pipefail
# Ponytail's hooks come only with its plugin, so use the author's own install commands.
# Rerun after a Ponytail gitlink update: Codex keeps a copy of the plugin.
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
ponytail="$repo_dir/.upstream/ponytail"
[[ -d "$ponytail/.claude-plugin" ]] || exit 0
if command -v claude >/dev/null; then
    { claude plugin marketplace add "$ponytail" && claude plugin install ponytail@ponytail; } ||
        printf 'The Ponytail plugin for Claude Code was not installed. See .upstream/ponytail/INSTALL.md.\n' >&2
    # Anthropic's LSP plugins give Claude Code PHP and TypeScript code intelligence once the servers are in PATH.
    { claude plugin marketplace add anthropics/claude-plugins-official &&
        claude plugin install php-lsp@claude-plugins-official &&
        claude plugin install typescript-lsp@claude-plugins-official; } ||
        printf 'The LSP plugins for Claude Code were not installed. See docs/integrations/claude-code.md.\n' >&2
fi
if command -v codex >/dev/null; then
    # Codex installs from our marketplace: the author's one fetches his main branch, not the pinned gitlink.
    { codex plugin marketplace add "$repo_dir/adapters/codex" && codex plugin add ponytail@agents; } ||
        printf 'The Ponytail plugin for Codex was not installed. See .upstream/ponytail/INSTALL.md.\n' >&2
fi
