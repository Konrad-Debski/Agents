#!/usr/bin/env bash
set -euo pipefail

fail() { printf 'Błąd: %s\n' "$*" >&2; exit 1; }

for dependency in git flock systemctl bash; do
    command -v "$dependency" >/dev/null || fail "Brak polecenia $dependency. Zainstaluj je przed uruchomieniem instalatora."
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(git -C "$script_dir/.." rev-parse --show-toplevel)
git_dir=$(git -C "$repo_dir" rev-parse --absolute-git-dir)
state_dir="$git_dir/agent-skills-sync"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
upstream_script="$repo_dir/.upstream/git-sync/git-sync"

[[ $(uname -s) == Linux ]] || fail 'Instalator wymaga Linuksa z systemd.'
systemctl --user show-environment >/dev/null || fail 'Brak dostępu do systemd użytkownika. Uruchom instalator w sesji docelowego użytkownika, bez sudo.'
[[ $(git -C "$repo_dir" branch --show-current) == main ]] || fail 'Instalację uruchom na gałęzi main.'
[[ $(git -C "$repo_dir" config --get branch.main.remote) == origin ]] || fail 'Gałąź main musi śledzić origin/main.'
[[ $(git -C "$repo_dir" config --get branch.main.merge) == refs/heads/main ]] || fail 'Gałąź main musi śledzić origin/main.'
git -C "$repo_dir" var GIT_AUTHOR_IDENT >/dev/null || fail 'Ustaw git config user.name oraz user.email.'

export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -oBatchMode=yes -oConnectTimeout=15}"
export GCM_INTERACTIVE=never
git -C "$repo_dir" ls-remote --exit-code origin refs/heads/main >/dev/null || fail 'Nie można pobrać origin/main. Sprawdź dostęp do repozytorium.'

mkdir -p -- "$state_dir" "$unit_dir"
exec 9>"$state_dir/lock"
flock -w 30 9 || fail 'Synchronizacja jest w toku. Ponów instalację po jej zakończeniu.'

git -C "$repo_dir" submodule foreach --quiet --recursive '
    test -z "$(git status --porcelain)" || {
        echo "Submoduł $displaypath zawiera niezapisane zmiany." >&2
        exit 1
    }
'
git -C "$repo_dir" submodule update --init --recursive
git -C "$repo_dir" submodule update --init --remote --checkout -- .upstream/git-sync
bash -n "$upstream_script"
git -C "$repo_dir" config --local branch.main.sync true
git -C "$repo_dir" config --local branch.main.syncNewFiles true
git -C "$repo_dir" config --local branch.main.syncSkipHooks false
git -C "$repo_dir" config --local branch.main.pushRemote origin

# systemd expands percent specifiers and, in ExecStart arguments, dollar signs.
unit_quote() {
    local value=$1
    [[ "$value" != *$'\n'* && "$value" != *$'\r'* && "$value" != *$'\t'* ]] || fail 'Ścieżka zawiera niedozwolony znak sterujący.'
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
runner_unit=$(unit_quote "$repo_dir/scripts/sync.sh" exec)
bash_unit=$(unit_quote "$(command -v bash)" exec)

cat >"$unit_dir/agent-skills-sync.service" <<EOF
[Unit]
Description=Synchronize agent skills with Git

[Service]
Type=oneshot
WorkingDirectory=$repo_unit
ExecStart=$bash_unit $runner_unit
Environment=GIT_TERMINAL_PROMPT=0
Environment=GCM_INTERACTIVE=never
TimeoutStartSec=5min
EOF

cat >"$unit_dir/agent-skills-sync.timer" <<'EOF'
[Unit]
Description=Synchronize agent skills every 15 minutes

[Timer]
OnActiveSec=1min
OnUnitInactiveSec=15min
AccuracySec=30s
Unit=agent-skills-sync.service

[Install]
WantedBy=timers.target
EOF

systemctl --user import-environment PATH
if [[ -n ${SSH_AUTH_SOCK:-} ]]; then
    systemctl --user import-environment SSH_AUTH_SOCK
fi
systemctl --user daemon-reload
systemctl --user enable --now agent-skills-sync.timer

if command -v loginctl >/dev/null; then
    if ! loginctl --no-ask-password enable-linger "$(id -un)"; then
        printf 'Timer działa w sesji użytkownika. Aby działał także po wylogowaniu, administrator musi wykonać: sudo loginctl enable-linger %s\n' "$(id -un)" >&2
    fi
else
    printf 'Brak loginctl. Sprawdź, czy systemd użytkownika działa także po wylogowaniu.\n' >&2
fi

printf 'Zaktualizowano submoduł git-sync do master i włączono agent-skills-sync.timer.\nPierwsza synchronizacja za około minutę, kolejne co 15 minut po zakończeniu poprzedniej.\nLogi: journalctl --user -u agent-skills-sync.service\n'
