# Local configuration and MCP

## Local settings and secrets

The optional file `${XDG_CONFIG_HOME:-~/.config}/agents/local.json` stays outside the repository:

```json
{
  "harnesses": ["codex", "claude-code", "cursor", "opencode", "vscode"],
  "disabled_servers": [],
  "disabled_servers_by_harness": {}
}
```

A missing `harnesses` key means automatic detection. An empty list disables the integrations. Removing a harness from the explicit list removes only its previously managed entries and links. `disabled_servers` disables a server on a specific machine without changing the shared definition.

`disabled_servers_by_harness` disables a shared entry only in the selected harnesses. For example, `{"vscode": ["context7"], "opencode": ["context7"]}` keeps your own Context7 HTTP servers with their authorization, without adding a second connection. It does not disable personal entries with other names. If you delete a managed JSON or JSONC entry by hand, `apply` recreates it as long as the registry and local settings still call for it.

Entry ownership state, the apply lock and local backups live in `${XDG_STATE_HOME:-~/.local/state}/agents`. Do not delete `managed.json` if you want existing entries to keep updating automatically. Losing the state makes the adapter report a collision instead of taking over someone else's configuration. Backups have `600` permissions and also hold the contents of replaced local files. Protect them the same way as the harness configuration.

Provide API keys in the environment of the launched harness. Variables set only in the terminal may be missing in a GUI app or a systemd service. Each harness stores its own OAuth tokens locally. Log in separately on each computer. The repository does not carry login sessions, conversation history or connector data.

## MCP definitions

The registry includes the remote Context7 server at `https://mcp.context7.com/mcp`, the Figma server at `https://mcp.figma.com/mcp`, and the public OpenAI documentation server. Figma logs in through OAuth separately in each harness and needs no secret. The OpenAI server is assigned only to Codex (`"harnesses": ["codex"]`). Context7 uses Streamable HTTP and needs no local Node.js or `npx`. Add other MCP servers to `mcp/servers.json` after moving their secrets into the environment.

The default Context7 configuration connects without an API key, so a missing authorization variable does not block MCP startup. A key gives [higher rate limits](https://github.com/upstash/context7/blob/master/docs/resources/troubleshooting.mdx). You can keep your own authorized connections and disable the shared entry with `disabled_servers_by_harness`.

To require authorization in the shared Context7 definition, add `"header_env": {"Authorization": "CONTEXT7_AUTHORIZATION"}` and set the `CONTEXT7_AUTHORIZATION` variable to the full value `Bearer <Context7 API key>`. The adapters write references to the environment, and `doctor` checks that the variable exists. The key value stays outside the repository.

After changing the registry, run `bash ~/.agents/scripts/apply.sh`. The adapters update the managed entries and keep personal servers. The `gallery` and `version` fields do not belong in the shared registry.

Format example:

```json
{
  "version": 1,
  "servers": {
    "local-tool": {
      "transport": "stdio",
      "command": "my-mcp-server",
      "args": ["serve"],
      "env_vars": ["MY_TOOL_API_KEY"],
      "requires_env": ["MY_TOOL_API_KEY"]
    },
    "remote-tool": {
      "transport": "http",
      "url": "https://example.com/mcp",
      "header_env": {"X-API-Key": "MY_TOOL_API_KEY"},
      "harnesses": ["codex", "claude-code"]
    }
  }
}
```

We support `stdio` and Streamable HTTP. `env_vars` passes variables to the process, `header_env` names the variables that hold header values, and `requires_env` adds requirements to diagnostics. The generated configuration holds variable references, never the values read from them. `harnesses` optionally limits the integration to the listed tools.

Do not put secrets in arguments, URLs or source files. The shared registry does not accept arbitrary `env` or `headers` fields with fixed values. Commands should be available in `PATH`, without `/home/...` paths. Install MCP dependencies locally. If you need a reproducible package version, pin it in the command arguments.
