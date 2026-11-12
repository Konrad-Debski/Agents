#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd -- "$script_dir/.."
command=${1:-all}
case $command in
    all)
        for check in static repository tests commits; do
            bash "$script_dir/check.sh" "$check"
        done
        ;;
    tests) python3 -m unittest discover -s tests -v ;;
    static)
        shopt -s globstar nullglob
        files=(install.sh scripts/**/*.sh)
        for file in "${files[@]}"; do bash -n "$file"; done
        shellcheck "${files[@]}"
        python3 -m ruff check --isolated --no-cache --select E9,F scripts tests
        actionlint
        ;;
    repository)
        python3 scripts/agents.py validate
        python3 scripts/agents.py guard
        python3 scripts/quality/repository.py
        ;;
    commits)
        base=$(git rev-parse --verify --end-of-options "${2:-origin/main}^{commit}")
        head=$(git rev-parse --verify --end-of-options "${3:-HEAD}^{commit}")
        if git log --no-merges --format=%s "$base..$head" |
            grep -Ev '^(feat|fix|refactor|chore|docs|test|build|ci|perf|revert)(\([a-z0-9-]+\))?!?: .+'; then
            printf 'Use Conventional Commits for the commit subjects above.\n' >&2
            exit 1
        fi
        ;;
    *) printf 'Usage: check.sh [all|tests|static|repository|commits [BASE HEAD]]\n' >&2; exit 2 ;;
esac
