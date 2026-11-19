#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(git -C "$script_dir/.." rev-parse --show-toplevel)
cd -- "$repo_dir"
git_dir=$(git rev-parse --absolute-git-dir)
state_dir="$git_dir/agents-sync"
[[ -d "$state_dir" ]] || {
    printf 'Run bash install.sh first.\n' >&2
    exit 1
}

exec 9>"$state_dir/lock"
flock -n 9 || exit 0

branch=$(git branch --show-current)
if [[ -z "$branch" ]]; then
    printf 'No active branch. Check the repository and finish any rebase before synchronizing.\n' >&2
    exit 1
fi
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -oBatchMode=yes -oConnectTimeout=15}"
export GCM_INTERACTIVE=never

# Avoid taking a snapshot of an unfinished Git operation.
for operation in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply sequencer; do
    if [[ -e $(git rev-parse --git-path "$operation") ]]; then
        printf 'Finish the current Git operation before synchronizing.\n' >&2
        exit 1
    fi
done
pending="$state_dir/submodules-pending"
# shellcheck source=scripts/sync/retire-legacy.sh
source "$repo_dir/scripts/sync/retire-legacy.sh"
retire_legacy_sync "$repo_dir" "$state_dir"
# shellcheck source=scripts/sync/gitsync.sh
source "$repo_dir/scripts/sync/gitsync.sh"
head=$(git rev-parse HEAD)
changes=$(git status --porcelain --untracked-files=all --ignore-submodules=dirty)
if [[ -n $changes && ! -e "$pending" ]]; then
    publish_snapshot "$head" "$branch"
    exit 0
fi
parent_changes=$(git status --porcelain --untracked-files=all --ignore-submodules=all)
if [[ -n $parent_changes ]]; then
    publish_snapshot "$head" "$branch"
    exit 0
fi
if [[ $branch != main ]]; then
    if ! git merge-base --is-ancestor "$head" origin/main; then
        publish_snapshot "$head" "$branch"
    fi
    exit 0
fi
# shellcheck disable=SC2016 # Git expands the variables in each submodule.
git submodule foreach --quiet --recursive '
    if test -n "$(git status --porcelain)"; then
        echo "Submodule $displaypath has uncommitted changes. Commit them in its repository." >&2
        exit 1
    fi
'

git fetch origin main
if ! git merge-base --is-ancestor HEAD origin/main; then
    publish_snapshot "$head" "$branch"
    exit 0
fi
touch "$pending"
git merge --ff-only origin/main
retire_legacy_sync "$repo_dir" "$state_dir"
git submodule update --init --recursive --checkout
rm -f -- "$pending"
python3 scripts/agents.py guard
python3 scripts/agents.py validate
bash scripts/apply.sh
# Plugins are reinstalled once per synchronized commit, not on every timer run.
if [[ $(cat "$state_dir/plugins-head" 2>/dev/null) != $(git rev-parse HEAD) ]]; then
    bash scripts/plugins.sh
    git rev-parse HEAD >"$state_dir/plugins-head"
fi
