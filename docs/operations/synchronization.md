# Synchronization

The first run happens about a minute after installation, then every 15 minutes after the previous run ends. On a clean `main` with no unpublished commits, the timer fetches `origin/main`, advances by fast-forward and applies the approved configuration.

When a checkout has local edits or commits outside `origin/main`, the timer saves a snapshot on `origin/agents-wip/<id>`. The first push creates that branch. Each checkout has its own ID and updates its branch without force-pushing. The snapshot preserves tracked edits, deletions and non-ignored new files. If staged contents differ from both HEAD and the working files, the snapshot's first parent contains the staged version. The timer leaves your current branch, index and working files in place and skips unfinished Git operations. A rejected push leaves the snapshot in a local ref and the timer retries on the next run while work is still pending.

The repository guard checks the snapshot and unpublished commit history for paths outside the shared scope, common credential files and recognized token formats. It cannot detect every secret. The backup branch is visible to anyone with read access to `origin`. Use working branches and pull requests to publish reviewed changes to `main`.

After downloading the approved revision and its recorded submodule versions, we check the synchronization scope and MCP registry, then run `apply`. After a new commit, synchronization also runs `scripts/plugins.sh`, which reinstalls the Ponytail plugin in Claude Code and Codex and the LSP plugins in Claude Code. A failed validation leaves the previous harness configuration in place. An apply error does not roll back the Git download. After fixing the cause, run `apply` again. Failed submodule checkouts leave a marker so the next run can retry the approved versions. Local edits inside submodules still stop the retry.

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

## Recover a snapshot on another computer

List backup branches and check the commit message for the source branch. Replace `<id>` with the ID from the listing or the source computer's timer log. Recover the snapshot on a new local branch from a clean checkout.

```bash
git ls-remote --heads origin 'agents-wip/*'
git fetch origin refs/heads/agents-wip/<id>
git log -1 --oneline FETCH_HEAD
git switch -c recover-agent-work FETCH_HEAD
```

## Submodules

The installer and synchronization check out the gitlinks recorded in the parent repository. A newer upstream commit is not installed until its gitlink has passed CI and been merged through a pull request. The timer uses the repository’s own snapshot script.

During migration, the runner archives a recognized clean orphan of the retired git-sync checkout. Dirty or unrecognized leftovers remain untouched and stop synchronization. [Installation](installation.md) describes the archive and recovery of unpublished commits from the old timer.

Commit work inside submodules in their own repositories. The parent snapshot can record a changed gitlink. The download on `main` stops if a submodule has uncommitted changes. We link selected skills as whole directories, keeping their references and metadata. Codex ignores symlinks of the `SKILL.md` file itself during skill discovery. [upstream.md](../skills/upstream.md) describes choosing new sources.

Fetching the committed versions:

```bash
git -C ~/.agents pull --ff-only
git -C ~/.agents submodule update --init --recursive
bash ~/.agents/scripts/apply.sh
```

Proposing newer versions of all sources on a working branch:

```bash
git -C ~/.agents switch -c chore/update-upstream-skills
git -C ~/.agents submodule update --init --remote --checkout
bash ~/.agents/scripts/apply.sh
```

Review the upstream changes, run the quality checks, commit the new gitlinks and publish a pull request. The timer can back up the changed gitlinks on the checkout’s snapshot branch. After merge, return to `main` and fetch the approved revision.

## Claude Code links

`apply` scans the `skills/` directory on every run. For each directory with a `SKILL.md`, including a symlink into a submodule, it creates a link `~/.claude/skills/<name>` to `~/.agents/skills/<name>`. When `CLAUDE_CONFIG_DIR` is set, it uses that directory instead of `~/.claude`.

A new skill needs one `apply` run. Edits to an existing skill show up immediately through the same link. Removing a skill removes only a link the adapter managed before. Personal directories and foreign symlinks stay protected, and a name collision stops the apply.

`scripts/sync/run.sh` runs `apply.sh` after a successful Git synchronization and submodule update, so the timer also covers new and removed skills. The timer applies approved configuration when it synchronizes a clean `main`. Expose newly added skills right away with:

```bash
bash ~/.agents/scripts/apply.sh --dry-run
bash ~/.agents/scripts/apply.sh
```

Claude Code must be detected or listed in the explicit `harnesses` list. With the timer disabled, run `apply` by hand after adding or removing a skill. [Claude Code supports automatic skill reloading](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md). If a running session does not show a change from a symlink or a submodule update, use `/reload-skills` if your version has it, or start a new session. The adapter checks files, not the memory of a running Claude process.
