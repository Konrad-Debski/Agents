# Agents

A shared base of knowledge, skills and MCP configuration for AI agents. The repository is installed in `~/.agents` and synchronized between computers through Git.

`AGENTS.md` is a short knowledge map. Detailed rules live in `docs/` and `skills/`, and the agent loads them for a specific task.

## Documentation

- [Installation and diagnostics](docs/operations/installation.md): a new computer, applying the configuration, resolving collisions.
- [Integrations](docs/integrations/README.md): Codex, Claude Code, OpenCode, Cursor, VS Code and T3.
- [Configuration and MCP](docs/operations/configuration.md): local settings, secrets, the server registry.
- [Synchronization](docs/operations/synchronization.md): the timer, Git and submodules.
- [Maintenance and tests](docs/contributing/maintenance.md): changes to this repository.
- [Context management](docs/contributing/context-management.md): where to store knowledge and when to load it.
- [Skill index](docs/skills/README.md): choosing a procedure when the harness does not show the catalog.
- [Sources and decisions](docs/contributing/context-design.md): a summary of Kyle's video and the reasons for the knowledge split.

## Structure

- `AGENTS.md` points to the knowledge sources for all projects.
- `docs/` holds topic documentation.
- `skills/` holds procedures and their optional references.
- `mcp/servers.json` holds shared server definitions without secrets.
- `adapters/` describes the harness integrations.
- `install.sh` is the installer. Run it once on a new computer.
- `scripts/` holds `apply.sh` and `doctor.sh`, which you run by hand, and `agents.py`, which implements them.
- `scripts/sync/` holds the scripts that the timer and `git-sync` run. Do not run them by hand.
- `tests/` checks the adapters and synchronization in isolated directories.
- `.upstream/` holds external sources that update automatically.
