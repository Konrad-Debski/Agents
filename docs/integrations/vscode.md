# VS Code

VS Code in the Local harness reads personal skills from `~/.agents/skills`, so the adapter does not copy them. The adapter merges MCP in `${XDG_CONFIG_HOME:-~/.config}/Code/User/mcp.json`, which is the user profile. Shared servers go into the `servers` section and use `${env:NAME}` references. We keep comments, trailing commas, `inputs`, personal servers and other settings. The adapter does not write to a project's `.vscode/mcp.json` or to a portable `.mcp.json`. Plugins in `~/.vscode/agent-plugins` are out of scope, because they work only in VS Code. We do not read or change them.

Local harness instructions have no documented global file, so add them by hand in **Chat: Open Customizations > Instructions** for the Local harness as a user instruction:

```text
Read and follow ~/.agents/AGENTS.md before every task.
```

The adapter supports the default user profile on Linux. It does not change VS Code Insiders or other profiles. The VS Code process reads `${env:NAME}` variables. An app started from the menu may not see them if they are set only in the terminal.
