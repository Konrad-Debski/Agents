# Cursor

Cursor reads skills from `~/.agents/skills`, and the adapter merges MCP in `~/.cursor/mcp.json`. Global User Rules are set in the Cursor UI. Add this once in **Customize > Rules**:

```text
Read and follow ~/.agents/AGENTS.md before every task.
```

This is an instruction for the model, not a native file import. `doctor.sh` reminds you about it but does not check the UI settings. We do not write global Cursor rules to an undocumented file.
