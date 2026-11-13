# Installation

Requirements: Linux with a systemd user instance, Git, Bash, Python 3.11 or newer, and `flock` from util-linux. Fetching from `origin/main` must work without an interactive login. Installation and synchronization never create commits or push changes.

The repository should occupy the `~/.agents` directory. Do not clone it inside an existing `~/.agents/skills`. With an existing installation, use `apply --dry-run` described below and resolve the reported collisions.

On a new computer, as the target user, without `sudo`:

```bash
git clone --recurse-submodules git@github.com:Konrad-Debski/Agents.git ~/.agents
bash "$HOME/.agents/install.sh"
bash "$HOME/.agents/scripts/doctor.sh"
```

The installer detects harnesses by their directories or by their programs in `PATH`. It creates the configuration and starts `agents-sync.timer`. When `claude` or `codex` is in `PATH`, it also installs the [Ponytail plugin](../skills/upstream.md) there. Running the command again updates the installation without duplicates. Moving the repository requires a reinstall. With existing collisions, first merge your own instructions or give the local MCP server a different name. The installer does not replace a different instructions file or a foreign symlink.

Installing only the configuration, without systemd:

```bash
bash "$HOME/.agents/install.sh" --no-sync --dry-run
bash "$HOME/.agents/install.sh" --no-sync
```

The scripts use the Python standard library and install no packages. The automatic schedule currently supports Linux. macOS and Windows have no schedule installer.

After upgrading from the publishing timer, run the installer again. It removes the old git-sync autocommit settings. Local edits and local commits on `main` stop synchronization until you move them to a working branch and publish a pull request.

Git may leave `.upstream/git-sync` behind after the gitlink is removed. The installer and new runner archive it under `.git/agents-sync/retired-git-sync.*/checkout` only when it is an untracked, clean submodule checkout with the historical official origin. The archive retains its files, Git metadata connection and local commits. A dirty checkout, a symlink or a different origin is preserved in place and stops migration with a specific message. Move that checkout outside the repository yourself before retrying; do not delete local work to satisfy the check.

The old timer may have made unpublished `Synchronize agent configuration` commits. Preserve their original tip with `git branch backup/pre-ci-main main`, then create a working branch such as `chore/recover-sync-changes`. Review those commits, reword and sign only the unpublished working-branch commits, and publish a PR. After merge, while on another branch with a clean work tree, fetch `origin/main` and move the local `main` branch to it before switching back. Keep the backup until you have verified that every intended change survived. No reset or cleanup of local work is part of installation.

## Apply and diagnostics

```bash
bash "$HOME/.agents/scripts/apply.sh" --dry-run
bash "$HOME/.agents/scripts/apply.sh"
bash "$HOME/.agents/scripts/doctor.sh"
```

`--dry-run` writes no configuration or state. Apply first checks all collisions, then writes files atomically and backs up the previous versions. A handled write error rolls back the earlier changes from that run. Managed entries changed by hand stop the apply. Edit the source definition instead of the generated entry.

Do not run apply while changing configuration in a harness UI. The lock guards against a second `apply` process, but external apps do not know about it. A sudden shutdown while writing several files may require restoring them from backups.

`doctor` checks the apply plan, missing programs and environment variables, broken symlinks and the timer state. It does not connect to MCP servers, verify OAuth logins or test model behavior.

[configuration.md](configuration.md) describes machine settings and secrets, and [synchronization.md](synchronization.md) the schedule and submodules.
