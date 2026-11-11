#!/usr/bin/env bash
set -euo pipefail
destination=${1:?Usage: install-tools.sh ABSOLUTE_DIRECTORY}
[[ $destination == /* ]] || { printf 'Use an absolute destination.\n' >&2; exit 1; }
command -v go >/dev/null || { printf 'Go is required to install Gitleaks. Install Go and retry.\n' >&2; exit 1; }
temporary=$(mktemp -d)
trap 'rm -rf -- "$temporary"' EXIT
cd -- "$temporary"
curl -fsSLo download-actionlint.bash https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash
mkdir -p -- "$destination"
bash download-actionlint.bash latest "$destination"
GOBIN="$destination" go install "github.com/zricethezav/gitleaks/v8@${GITLEAKS_VERSION:-latest}"
