#!/usr/bin/env bash
# Install the approved document runtime under ~/.local/state/document-workflow.
# No sudo, no apt, no system packages, no files written into the repo.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
state="${DOCUMENT_WORKFLOW_STATE:-$HOME/.local/state/document-workflow}"
pandoc_version="3.14"
url="https://github.com/jgm/pandoc/releases/download/${pandoc_version}/pandoc-${pandoc_version}-linux-amd64.tar.gz"
work="/tmp/opencode/document-workflow-install-$$"

mkdir -p "$state/bin" "$work"
curl -fsSL --max-time 120 -o "$work/pandoc.tar.gz" "$url"
tar -xzf "$work/pandoc.tar.gz" -C "$work"
install -Dm755 "$work/pandoc-${pandoc_version}/bin/pandoc" "$state/bin/pandoc"

if [ ! -x "$state/venv/bin/python" ]; then
    python3 -m venv "$state/venv"
fi
"$state/venv/bin/python" -m pip install --no-cache-dir --disable-pip-version-check \
    "reportlab==5.1.0" "openpyxl==3.1.5"

printf 'Pandoc: %s\n' "$("$state/bin/pandoc" --version | head -1)"
printf 'ReportLab: %s\n' "$("$state/venv/bin/python" -c 'import reportlab;print(reportlab.Version)')"
printf 'openpyxl: %s\n' "$("$state/venv/bin/python" -c 'import openpyxl;print(openpyxl.__version__)')"
printf 'Skill: %s\n' "$root"
