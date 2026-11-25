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

`disabled_servers_by_harness` disables a shared entry only in the selected harnesses. For example, `{"opencode": ["io.github.upstash/context7"]}` keeps your own Context7 HTTP server with its authorization, without adding a second connection. It does not disable personal entries with other names. If you delete a managed JSON or JSONC entry by hand, `apply` recreates it as long as the registry and local settings still call for it.

Entry ownership state, the apply lock and local backups live in `${XDG_STATE_HOME:-~/.local/state}/agents`. Do not delete `managed.json` if you want existing entries to keep updating automatically. Losing the state makes the adapter report a collision instead of taking over someone else's configuration. Backups have `600` permissions and also hold the contents of replaced local files. Protect them the same way as the harness configuration.

Keep API keys in `~/.agents/.env` as `NAME=value` lines and give the file `600` permissions. Git ignores it and the guard refuses to synchronize it, so create it once on each computer. `python3 ~/.agents/scripts/agents.py secrets` lists the variables the registry uses and what each one holds; with `--prompt` it asks for the missing ones in a terminal and saves them. No harness reads `.env` directly. On Linux `apply` copies the variables the registry refers to into `${XDG_CONFIG_HOME:-~/.config}/environment.d/60-agents.conf` (`600`), and the systemd user session passes them to the desktop and the harnesses started from it. Log out and back in after the first apply or a key change. The harness configurations hold only references such as `${env:CONTEXT7_API_KEY}`. Values must not contain whitespace, quotes, `$` or backslashes, because `environment.d` would change them. On other systems set the variables in the harness environment yourself. Each harness stores its own OAuth tokens locally. Log in separately on each computer. The repository does not carry login sessions, conversation history or connector data.

## MCP definitions

The registry includes the remote Context7 server at `https://mcp.context7.com/mcp`, the Figma server at `https://mcp.figma.com/mcp`, Google Sheets at `https://sheetsmcp.googleapis.com/mcp/v1`, the [Userback](https://docs.userback.io/docs/userback-mcp) server at `https://mcp.userback.io/v1/mcp/`, and the public OpenAI documentation server. Figma, Google Sheets and Userback log in through OAuth separately in each harness. The OpenAI server is assigned only to Codex (`"harnesses": ["codex"]`). Context7 uses Streamable HTTP and needs no local Node.js or `npx`. Add other MCP servers to `mcp/servers.json` after moving their secrets into the environment.

Context7 sends its API key in the `CONTEXT7_API_KEY` header (`"header_env": {"CONTEXT7_API_KEY": "CONTEXT7_API_KEY"}`), which gives [higher rate limits](https://github.com/upstash/context7/blob/master/docs/resources/troubleshooting.mdx). Put `CONTEXT7_API_KEY=<key>` in `~/.agents/.env`. The adapters write references to the variable, and `doctor` reports it when the harness environment lacks it.

Google Sheets uses a pre-registered OAuth client, so its secret goes into `~/.agents/.env` as `GOOGLE_SHEETS_MCP_CLIENT_SECRET=<secret>`, and the registry names the variable in `oauth.client_secret_env`. Harnesses take it differently:

- OpenCode and Cursor get a reference to the variable.
- Codex accepts only the value, so `apply` writes it into the managed `oauth` table in `config.toml`. `managed.json` holds it too, so both files keep `600` permissions. Without the value in `.env`, `apply` leaves the `oauth` table local and prints how to add it.
- Claude Code keeps the secret in `~/.claude/.credentials.json`, under the server name and a digest of its type, URL and headers. On Linux `apply` writes only that entry and leaves the login tokens alone. On other systems Claude Code uses the keychain, and `apply` prints the manual commands.
- VS Code keeps client secrets only in its secret storage. Once on each computer, open `mcp.json` and use **Set Client Secret** above `oauth.clientId`.

After changing the registry, run `bash ~/.agents/scripts/apply.sh`. The adapters update the managed entries and keep personal servers.

Server names match the ones VS Code gives servers installed from its MCP gallery, such as `io.github.upstash/context7` and `com.figma.mcp/mcp`. Claude Code, Codex and OpenCode accept the same names in their configuration files. Google Sheets is `Google-Sheets`, because the `claude mcp` CLI accepts only letters, digits, `-` and `_`. When a harness already has an identical entry under that name, `apply` takes it over. A different entry is reported as a collision. In VS Code the comparison skips the `gallery` and `version` fields, so a gallery install and its updates stay managed. Do not put these fields in the registry.

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

We support `stdio` and Streamable HTTP. `env_vars` passes variables to the process, `header_env` names the variables that hold header values, and `requires_env` adds requirements to diagnostics. The generated configuration holds variable references, never the values read from them. The exception is an OAuth client secret in Codex and Claude Code, described above. `harnesses` optionally limits the integration to the listed tools.

Do not put secrets in arguments, URLs or source files. The shared registry does not accept arbitrary `env` or `headers` fields with fixed values. Commands should be available in `PATH`, without `/home/...` paths. Install MCP dependencies locally. If you need a reproducible package version, pin it in the command arguments.
