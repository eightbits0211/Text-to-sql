#!/bin/bash
# Build the LMS upload: code archive (tracked files only, no data or checkpoints)
# plus the report PDF. Usage: scripts/make_lms_bundle.sh [output_dir]
set -euo pipefail
cd "$(dirname "$0")/.."
out="${1:-$HOME/Desktop/CS-F429-Part2-LMS}"
if [ -n "$(git status --porcelain -- src scripts tests docs pyproject.toml uv.lock README.md)" ]; then
  echo "Commit your changes first: the archive is built from HEAD." >&2
  exit 1
fi
mkdir -p "$out"
# Internal working notes (agent instructions, session logs, HPC account notes) are not shipped.
git archive --format=zip --prefix=Text-to-SQL-Part2/ -o "$out/Text-to-SQL-Part2-code.zip" HEAD -- . \
  ':(exclude)docs/agent-rules.md' \
  ':(exclude)docs/sub-agent-coordination-plan.md' \
  ':(exclude)docs/prd-authority-audit.md' \
  ':(exclude)docs/project-progress-log.md' \
  ':(exclude)docs/implementation-checkpoints.md' \
  ':(exclude)docs/part-2-submission-plan.md' \
  ':(exclude)docs/hpc-setup.md' \
  ':(exclude)docs/viva-qa-prep.md' \
  ':(exclude)state.md' \
  ':(exclude)scripts/make_lms_bundle.sh'
cp docs/part-2-report.pdf "$out/Part2-Report-Text-to-SQL.pdf"
echo "LMS bundle ($(git rev-parse --short HEAD)) written to $out:"
ls -la "$out"
