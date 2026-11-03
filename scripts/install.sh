#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# Apply without touching the timer first, e.g. during a migration rehearsal.
if [[ ${1:-} == --no-sync ]]; then
    shift
    exec bash "$script_dir/apply.sh" "$@"
fi
[[ $# == 0 ]] || { printf 'Użycie: install.sh [--no-sync [opcje apply.sh]]\n' >&2; exit 1; }
bash "$script_dir/install-sync.sh"
