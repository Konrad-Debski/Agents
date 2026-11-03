#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(git -C "$script_dir/.." rev-parse --show-toplevel)
cd -- "$repo_dir"
git_dir=$(git rev-parse --absolute-git-dir)
state_dir="$git_dir/agents-sync"
upstream_script="$repo_dir/.upstream/git-sync/git-sync"

[[ -d "$state_dir" && -f "$upstream_script" ]] || {
    printf 'Najpierw wykonaj bash scripts/install-sync.sh.\n' >&2
    exit 1
}

exec 9>"$state_dir/lock"
flock -n 9 || exit 0

branch=$(git branch --show-current)
if [[ -z "$branch" ]]; then
    printf 'Brak aktywnej gałęzi. Sprawdź repozytorium i dokończ ewentualny rebase przed synchronizacją.\n' >&2
    exit 1
fi
if [[ "$branch" != main ]]; then
    printf 'Pomijam synchronizację. Bieżąca gałąź nie jest main.\n'
    exit 0
fi

export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -oBatchMode=yes -oConnectTimeout=15}"
export GCM_INTERACTIVE=never

python3 scripts/agents.py guard
python3 scripts/agents.py validate

# Refuse unfinished Git operations before touching submodules.
bash "$upstream_script" check
git submodule foreach --quiet --recursive '
    if test -n "$(git status --porcelain)"; then
        echo "Submoduł $displaypath zawiera niezapisane zmiany. Zapisz je w jego repozytorium." >&2
        exit 1
    fi
'

# Retry a failed checkout before git-sync can mistake an old submodule HEAD for
# an intentional local change to the recorded submodule version.
pending="$state_dir/submodules-pending"
if [[ -e "$pending" ]]; then
    git submodule update --init --recursive
    rm -f -- "$pending"
fi

before=$(git rev-parse HEAD)
# Only git-sync follows the latest upstream branch automatically. Other
# submodules keep the versions recorded in this repository.
git submodule update --init --remote --checkout -- .upstream/git-sync
bash -n "$upstream_script"
touch "$pending"
if bash "$upstream_script"; then
    git submodule update --init --recursive
    rm -f -- "$pending"
    python3 scripts/agents.py guard
    python3 scripts/agents.py validate
    bash scripts/apply.sh
else
    result=$?
    if [[ $(git rev-parse HEAD) == "$before" ]]; then rm -f -- "$pending"; fi
    exit "$result"
fi
