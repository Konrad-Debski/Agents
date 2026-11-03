#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd -- "$script_dir/.."
python3 scripts/agents.py guard
git add -A
python3 scripts/agents.py guard --staged
git diff --cached --quiet || git commit -m "Synchronize agent configuration"
