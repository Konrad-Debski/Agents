#!/usr/bin/env bash
set -euo pipefail
# The only script to run by hand on a new computer. It checks the requirements,
# updates the submodules, deploys the configuration with scripts/apply.sh and
# starts a systemd timer that runs scripts/sync/run.sh every 15 minutes.

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# Apply without touching the timer first, e.g. during a migration rehearsal.
if [[ ${1:-} == --no-sync ]]; then
    shift
    exec bash "$script_dir/scripts/apply.sh" "$@"
fi
[[ $# == 0 ]] || { printf 'Usage: install.sh [--no-sync [apply.sh options]]\n' >&2; exit 1; }

fail() { printf 'Error: %s\n' "$*" >&2; exit 1; }

for dependency in git flock systemctl bash python3; do
    command -v "$dependency" >/dev/null || fail "Missing command $dependency. Install it before running the installer."
done

repo_dir=$(git -C "$script_dir" rev-parse --show-toplevel)
git_dir=$(git -C "$repo_dir" rev-parse --absolute-git-dir)
state_dir="$git_dir/agents-sync"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
upstream_script="$repo_dir/.upstream/git-sync/git-sync"

[[ $(uname -s) == Linux ]] || fail 'The installer requires Linux with systemd.'
systemctl --user show-environment >/dev/null || fail 'No access to the systemd user instance. Run the installer in the target user session, without sudo.'
[[ $(git -C "$repo_dir" branch --show-current) == main ]] || fail 'Run the installation on the main branch.'
[[ $(git -C "$repo_dir" config --get branch.main.remote) == origin ]] || fail 'The main branch must track origin/main.'
[[ $(git -C "$repo_dir" config --get branch.main.merge) == refs/heads/main ]] || fail 'The main branch must track origin/main.'
git -C "$repo_dir" var GIT_AUTHOR_IDENT >/dev/null || fail 'Set git config user.name and user.email.'

python3 "$repo_dir/scripts/agents.py" validate
python3 "$repo_dir/scripts/agents.py" guard
bash "$repo_dir/scripts/apply.sh" --dry-run

export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -oBatchMode=yes -oConnectTimeout=15}"
export GCM_INTERACTIVE=never
git -C "$repo_dir" ls-remote --exit-code origin refs/heads/main >/dev/null || fail 'Cannot fetch origin/main. Check access to the repository.'

mkdir -p -- "$state_dir" "$unit_dir"
exec 9>"$state_dir/lock"
flock -w 30 9 || fail 'Synchronization is in progress. Run the installation again after it finishes.'

git -C "$repo_dir" submodule foreach --quiet --recursive '
    test -z "$(git status --porcelain)" || {
        echo "Submodule $displaypath has uncommitted changes." >&2
        exit 1
    }
'
git -C "$repo_dir" submodule update --init --recursive
git -C "$repo_dir" submodule update --init --remote --checkout
bash -n "$upstream_script"
git -C "$repo_dir" config --local branch.main.sync true
git -C "$repo_dir" config --local branch.main.syncNewFiles true
git -C "$repo_dir" config --local branch.main.syncSkipHooks false
git -C "$repo_dir" config --local branch.main.pushRemote origin
printf -v autocommit_command 'bash %q' "$repo_dir/scripts/sync/autocommit.sh"
git -C "$repo_dir" config --local branch.main.autocommitscript "$autocommit_command"
bash "$repo_dir/scripts/apply.sh"

# systemd expands percent specifiers and, in ExecStart arguments, dollar signs.
unit_quote() {
    local value=$1
    [[ "$value" != *$'\n'* && "$value" != *$'\r'* && "$value" != *$'\t'* ]] || fail 'The path contains a forbidden control character.'
    value=${value//\\/\\\\}
    value=${value//\"/\\\"}
    value=${value//%/%%}
    if [[ ${2:-} == exec ]]; then
        value=${value//\$/\$\$}
        printf '"%s"' "$value"
    else
        printf '%s' "$value"
    fi
}

repo_unit=$(unit_quote "$repo_dir")
runner_unit=$(unit_quote "$repo_dir/scripts/sync/run.sh" exec)
bash_unit=$(unit_quote "$(command -v bash)" exec)

cat >"$unit_dir/agents-sync.service" <<EOF
[Unit]
Description=Synchronize agent configuration with Git

[Service]
Type=oneshot
WorkingDirectory=$repo_unit
ExecStart=$bash_unit $runner_unit
Environment=GIT_TERMINAL_PROMPT=0
Environment=GCM_INTERACTIVE=never
TimeoutStartSec=5min
EOF

cat >"$unit_dir/agents-sync.timer" <<'EOF'
[Unit]
Description=Synchronize agent configuration every 15 minutes

[Timer]
OnActiveSec=1min
OnUnitInactiveSec=15min
AccuracySec=30s
Unit=agents-sync.service

[Install]
WantedBy=timers.target
EOF

systemctl --user import-environment PATH
if [[ -n ${SSH_AUTH_SOCK:-} ]]; then
    systemctl --user import-environment SSH_AUTH_SOCK
fi
# Retire old units only after configuration has been deployed successfully.
systemctl --user disable --now agent-skills-sync.timer 2>/dev/null || true
systemctl --user stop agent-skills-sync.service 2>/dev/null || true
rm -f -- "$unit_dir/agent-skills-sync.timer" "$unit_dir/agent-skills-sync.service"
systemctl --user daemon-reload
systemctl --user enable --now agents-sync.timer

if command -v loginctl >/dev/null; then
    if ! loginctl --no-ask-password enable-linger "$(id -un)"; then
        printf 'The timer runs in the user session. To keep it running after logout, an administrator must run: sudo loginctl enable-linger %s\n' "$(id -un)" >&2
    fi
else
    printf 'loginctl is missing. Check that the systemd user instance keeps running after logout.\n' >&2
fi

printf 'Updated all submodules to the latest upstream versions and enabled agents-sync.timer.\nThe first synchronization runs in about a minute, then every 15 minutes after the previous one ends.\nLogs: journalctl --user -u agents-sync.service\n'
