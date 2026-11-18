#!/usr/bin/env bash
set -euo pipefail
# Ponytail's hooks come only with its plugin, so use the author's own install commands.
# Rerun after a Ponytail gitlink update: Codex keeps a copy of the plugin.
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
ponytail="$repo_dir/.upstream/ponytail"
modern_web="$repo_dir/.upstream/modern-web-guidance"
if [[ -d "$ponytail/.claude-plugin" ]] && command -v claude >/dev/null; then
    { claude plugin marketplace add "$ponytail" && claude plugin install ponytail@ponytail; } ||
        printf 'The Ponytail plugin for Claude Code was not installed. See .upstream/ponytail/INSTALL.md.\n' >&2
    # Anthropic's LSP plugins give Claude Code PHP and TypeScript code intelligence once the servers are in PATH.
    { claude plugin marketplace add anthropics/claude-plugins-official &&
        claude plugin install php-lsp@claude-plugins-official &&
        claude plugin install typescript-lsp@claude-plugins-official; } ||
        printf 'The LSP plugins for Claude Code were not installed. See docs/integrations/claude-code.md.\n' >&2
fi
if [[ -d "$ponytail/.claude-plugin" ]] && command -v codex >/dev/null; then
    # Codex installs from our marketplace: the author's one fetches his main branch, not the pinned gitlink.
    { codex plugin marketplace add "$repo_dir/adapters/codex" && codex plugin add ponytail@agents; } ||
        printf 'The Ponytail plugin for Codex was not installed. See .upstream/ponytail/INSTALL.md.\n' >&2
fi
if [[ -f "$modern_web/.claude-plugin/marketplace.json" ]] && command -v claude >/dev/null; then
    { claude plugin marketplace add "$modern_web" &&
        claude plugin install modern-web-guidance@googlechrome; } ||
        printf 'The Modern Web Guidance plugin for Claude Code was not installed. See docs/skills/upstream.md.\n' >&2
fi
if [[ -f "$modern_web/.agents/plugins/marketplace.json" ]] && command -v codex >/dev/null; then
    { codex plugin marketplace add "$modern_web" &&
        codex plugin add modern-web-guidance@googlechrome; } ||
        printf 'The Modern Web Guidance plugin for Codex was not installed. See docs/skills/upstream.md.\n' >&2
fi
