#!/usr/bin/env bash
# Sourced by run.sh while holding the sync lock.
publish_snapshot() (
    local head=$1 branch=$2 scratch id snapshot_ref tree previous snapshot
    local -a parents=(-p "$head")

    scratch=$(mktemp -d "$state_dir/snapshot.XXXXXXXX")
    trap 'rm -rf -- "$scratch"' EXIT
    if [[ ! -f "$state_dir/snapshot-id" ]]; then
        python3 -c 'import uuid; print(uuid.uuid4().hex)' >"$scratch/id"
        mv -- "$scratch/id" "$state_dir/snapshot-id"
    fi
    id=$(cat "$state_dir/snapshot-id")
    [[ $id =~ ^[a-f0-9]{32}$ ]] || {
        printf 'Invalid snapshot ID in %s/snapshot-id\n' "$state_dir" >&2
        return 1
    }
    snapshot_ref="refs/heads/agents-wip/$id"

    # Capture the worktree without changing what the agent has staged.
    export GIT_INDEX_FILE="$scratch/index"
    git read-tree "$head"
    git add -A
    tree=$(git write-tree)
    if [[ $(git rev-parse HEAD) != "$head" || $(git branch --show-current) != "$branch" ]]; then
        printf 'The checkout changed during the snapshot. Retry synchronization.\n' >&2
        return 1
    fi

    previous=$(git rev-parse --verify --quiet "refs/agents-sync/$id" || true)
    if [[ -n $previous && $(git rev-parse "$previous^{tree}") == "$tree" &&
        $(git rev-parse "$previous^1") == "$head" ]]; then
        snapshot=$previous
    else
        if [[ -n $previous ]]; then
            parents+=(-p "$previous")
        fi
        snapshot=$(git commit-tree "$tree" "${parents[@]}" -m "chore: Snapshot worktree on $branch")
    fi

    python3 scripts/agents.py guard --snapshot "$snapshot"
    git update-ref "refs/agents-sync/$id" "$snapshot"
    git -c remote.origin.mirror=false push --no-follow-tags --recurse-submodules=no origin "$snapshot:$snapshot_ref"
    printf 'Saved worktree snapshot on origin/%s\n' "${snapshot_ref#refs/heads/}"
)
