#!/usr/bin/env bash
# Sourced by run.sh while holding the sync lock.
publish_snapshot() (
    local snapshot_head=$1 source_branch=$2 snapshot_state=$3
    local scratch id snapshot_ref tree staged previous snapshot base
    local -a parents
    local -a commit=(git -c user.name='Agents Sync' -c user.email=agents-sync@localhost commit-tree --no-gpg-sign)

    scratch=$(mktemp -d "$snapshot_state/snapshot.XXXXXXXX")
    trap 'rm -rf -- "$scratch"' EXIT
    if [[ ! -f "$snapshot_state/snapshot-id" ]]; then
        python3 -c 'import uuid; print(uuid.uuid4().hex)' >"$scratch/id"
        mv -- "$scratch/id" "$snapshot_state/snapshot-id"
    fi
    id=$(cat "$snapshot_state/snapshot-id")
    [[ $id =~ ^[a-f0-9]{32}$ ]] || {
        printf 'Invalid snapshot ID in %s/snapshot-id\n' "$snapshot_state" >&2
        return 1
    }
    snapshot_ref="refs/heads/agents-wip/$id"

    # Capture the worktree without changing what the agent has staged.
    # Preserve the timestamp so Git rechecks files staged and edited in the same clock tick.
    cp -p -- "$(git rev-parse --git-path index)" "$scratch/index"
    cp -p -- "$scratch/index" "$scratch/staged"
    export GIT_INDEX_FILE="$scratch/staged"
    staged=$(git write-tree)
    export GIT_INDEX_FILE="$scratch/index"
    git add -A
    tree=$(git write-tree)
    if [[ $(git rev-parse HEAD) != "$snapshot_head" || $(git branch --show-current) != "$source_branch" ]]; then
        printf 'The checkout changed during the snapshot. Retry synchronization.\n' >&2
        return 1
    fi

    previous=$(git rev-parse --verify --quiet "refs/agents-sync/$id" || true)
    base=$snapshot_head
    if [[ $staged != "$tree" && $staged != "$(git rev-parse "$snapshot_head^{tree}")" ]]; then
        # Keep staged content when a later edit has overwritten it in the worktree.
        base=$(git rev-parse --verify --quiet "$previous^1" || true)
        if [[ -z $base || $base == "$snapshot_head" || $(git rev-parse "$base^{tree}") != "$staged" ||
            $(git rev-parse --verify --quiet "$base^1") != "$snapshot_head" ]]; then
            base=$("${commit[@]}" "$staged" -p "$snapshot_head" -m "chore: Snapshot staged changes on $source_branch")
        fi
    fi
    if [[ -n $previous && $(git rev-parse "$previous^{tree}") == "$tree" &&
        $(git rev-parse "$previous^1") == "$base" ]]; then
        snapshot=$previous
    else
        parents=(-p "$base")
        if [[ -n $previous ]]; then
            parents+=(-p "$previous")
        fi
        snapshot=$("${commit[@]}" "$tree" "${parents[@]}" -m "chore: Snapshot worktree on $source_branch")
    fi

    python3 scripts/agents.py guard --snapshot "$snapshot"
    git update-ref "refs/agents-sync/$id" "$snapshot"
    git -c remote.origin.mirror=false push --no-follow-tags --recurse-submodules=no origin "$snapshot:$snapshot_ref"
    printf 'Saved worktree snapshot on origin/%s\n' "${snapshot_ref#refs/heads/}"
)
