#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd -- "$script_dir/.."
command=${1:-all}
case $command in
    all)
        for check in static repository tests secrets; do
            bash "$script_dir/check.sh" "$check"
        done
        npm run test:pr
        ;;
    tests) python3 scripts/quality/run_tests.py ;;
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
    secrets)
        base=$(git rev-parse --verify --end-of-options "${2:-origin/main}^{commit}")
        head=$(git rev-parse --verify --end-of-options "${3:-HEAD}^{commit}")
        gitleaks git --redact --no-banner --log-opts="$base..$head" .
        ;;
    *) printf 'Usage: check.sh [all|tests|static|repository|secrets [BASE HEAD]]\n' >&2; exit 2 ;;
esac
