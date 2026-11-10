# Installation

Requirements: Linux with a systemd user instance, Git, Bash, Python 3.11 or newer, and `flock` from util-linux. Git must have `user.name` and `user.email` set. Fetching from and pushing to `origin/main`, and signing commits, must work without an interactive login.

The repository should occupy the `~/.agents` directory. Do not clone it inside an existing `~/.agents/skills`. With an existing installation, use `apply --dry-run` described below and resolve the reported collisions.

On a new computer, as the target user, without `sudo`:

```bash
git clone --recurse-submodules git@github.com:Konrad-Debski/Agents.git ~/.agents
bash "$HOME/.agents/install.sh"
bash "$HOME/.agents/scripts/doctor.sh"
```

The installer detects harnesses by their directories or by their programs in `PATH`. It creates the configuration and starts `agents-sync.timer`. Running the command again updates the installation without duplicates. Moving the repository requires a reinstall. With existing collisions, first merge your own instructions or give the local MCP server a different name. The installer does not replace a different instructions file or a foreign symlink.

Installing only the configuration, without systemd:

```bash
bash "$HOME/.agents/install.sh" --no-sync --dry-run
bash "$HOME/.agents/install.sh" --no-sync
```

The scripts use the Python standard library and install no packages. The automatic schedule currently supports Linux. macOS and Windows have no schedule installer.

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
