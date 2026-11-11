# Synchronization

The first run happens about a minute after installation, then every 15 minutes after the previous run ends. Synchronization works only on `main` and also commits new and deleted source files automatically. It can commit an edit in progress. Use a separate branch for work on changes.

`.gitignore` allows only the shared directories. An extra check also covers already tracked files and local unpushed commits. It blocks paths outside the scope, common credential files and recognized token formats. It does not replace reviewing changes and does not detect every possible secret.

Before synchronizing, we check the MCP registry. After a successful synchronization and submodule update, we check the sources again and run `apply`. A Git conflict stops the process and needs manual resolution. An apply error does not roll back the Git synchronization. After fixing the cause, run `apply` again.

```bash
systemctl --user status agents-sync.timer
journalctl --user -u agents-sync.service -n 50 --no-pager
systemctl --user start agents-sync.service
```

Disabling:

```bash
systemctl --user disable --now agents-sync.timer
systemctl --user stop agents-sync.service
```

The installer tries to keep systemd running after logout with `loginctl enable-linger`. If the system refuses, it prints the command for an administrator. It imports `PATH` and the current `SSH_AUTH_SOCK`. After changing the SSH agent, run the installer again. After a reboot, authentication must be available to the service without a password prompt.

## Submodules

The installer and every synchronization run update all submodules declared in `.gitmodules` to the latest upstream commits. The `branch` entry in `.gitmodules` sets the branch: `master` for `git-sync` and `main` for `cursor-plugins`. Without that entry, as for `ponytail` and `mattpocock-skills`, Git uses the remote repository's default branch. Synchronization commits the new submodule pointers and pushes them to `origin/main`.

Do not edit files inside submodules. Uncommitted changes stop synchronization. We link selected skills as whole directories, keeping their references and metadata. Codex ignores symlinks of the `SKILL.md` file itself during skill discovery. [upstream.md](../skills/upstream.md) describes choosing new sources.

Fetching the committed versions:

```bash
git -C ~/.agents pull --ff-only
git -C ~/.agents submodule update --init --recursive
bash ~/.agents/scripts/apply.sh
```

Manually fetching the latest versions of all sources:

```bash
git -C ~/.agents submodule update --init --remote --checkout
bash ~/.agents/scripts/apply.sh
```

After a manual update, commit the new pointers or leave that to the next synchronization run.

## Claude Code links

`apply` scans the `skills/` directory on every run. For each directory with a `SKILL.md`, including a symlink into a submodule, it creates a link `~/.claude/skills/<name>` to `~/.agents/skills/<name>`. When `CLAUDE_CONFIG_DIR` is set, it uses that directory instead of `~/.claude`.

A new skill needs one `apply` run. Edits to an existing skill show up immediately through the same link. Removing a skill removes only a link the adapter managed before. Personal directories and foreign symlinks stay protected, and a name collision stops the apply.

`scripts/sync/run.sh` runs `apply.sh` after a successful Git synchronization and submodule update, so the timer also covers new and removed skills. On a working branch, synchronization is skipped. Expose newly added skills right away with:

```bash
bash ~/.agents/scripts/apply.sh --dry-run
bash ~/.agents/scripts/apply.sh
```

Claude Code must be detected or listed in the explicit `harnesses` list. With the timer disabled, run `apply` by hand after adding or removing a skill. [Claude Code supports automatic skill reloading](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md). If a running session does not show a change from a symlink or a submodule update, use `/reload-skills` if your version has it, or start a new session. The adapter checks files, not the memory of a running Claude process.
