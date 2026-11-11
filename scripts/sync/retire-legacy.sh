#!/usr/bin/env bash
# Sourced by installation and synchronization while holding the sync lock.
retire_legacy_sync() {
    local repository=$1 state=$2 legacy origin status legacy_git_dir archive
    legacy="$repository/.upstream/git-sync"
    [[ -e "$legacy" || -L "$legacy" ]] || return 0
    git -C "$repository" ls-files --error-unmatch -- .upstream/git-sync >/dev/null 2>&1 && return 0
    if [[ ! -f "$legacy/.git" || -L "$legacy" || -L "$legacy/.git" ]]; then
        printf 'Preserved unrecognized legacy path %s; move it outside the repository before retrying.\n' "$legacy" >&2
        return 1
    fi
    origin=$(git -C "$legacy" config --get remote.origin.url) || return 1
    if [[ $origin != https://github.com/simonthum/git-sync.git ]]; then
        printf 'Preserved legacy checkout with a different origin: %s\n' "$legacy" >&2
        return 1
    fi
    status=$(git -C "$legacy" status --porcelain --untracked-files=all) || return 1
    if [[ -n $status ]]; then
        printf 'Preserved local changes in %s; move the checkout outside the repository before retrying.\n' "$legacy" >&2
        return 1
    fi
    legacy_git_dir=$(git -C "$legacy" rev-parse --absolute-git-dir) || return 1
    archive=$(mktemp -d "$state/retired-git-sync.XXXXXX") || return 1
    mv -- "$legacy" "$archive/checkout"
    # Preserve the checkout and its local commits with a working Git connection after the move.
    printf 'gitdir: %s\n' "$legacy_git_dir" > "$archive/checkout/.git"
    git --git-dir="$legacy_git_dir" --work-tree="$archive/checkout" config core.worktree "$archive/checkout"
    printf 'Archived retired git-sync checkout at %s\n' "$archive/checkout"
}
