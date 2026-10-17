#!/bin/bash
# Build the LMS upload: code archive (tracked files only, no data or checkpoints)
# plus the report PDF.
#   scripts/make_lms_bundle.sh [output_dir]           # Part 3 (default)
#   PART=2 scripts/make_lms_bundle.sh [output_dir]    # Part 2 bundle as submitted
set -euo pipefail
cd "$(dirname "$0")/.."
part="${PART:-3}"
out="${1:-$HOME/Desktop/CS-F429-Part${part}-LMS}"
if [ -n "$(git status --porcelain -- src scripts tests docs pyproject.toml uv.lock README.md)" ]; then
  echo "Commit your changes first: the archive is built from HEAD." >&2
  exit 1
fi
report="docs/part-${part}-report.pdf"
[ -f "$report" ] || { echo "Missing $report; build it with scripts/build_report.sh part-${part}-report" >&2; exit 1; }
mkdir -p "$out"
# Internal working notes (agent instructions, session logs, HPC account notes,
# plans and viva notes) are not shipped.
git archive --format=zip --prefix="Text-to-SQL-Part${part}/" -o "$out/Text-to-SQL-Part${part}-code.zip" HEAD -- . \
  ':(exclude)docs/agent-rules.md' \
  ':(exclude)docs/sub-agent-coordination-plan.md' \
  ':(exclude)docs/prd-authority-audit.md' \
  ':(exclude)docs/project-progress-log.md' \
  ':(exclude)docs/implementation-checkpoints.md' \
  ':(exclude)docs/part-2-submission-plan.md' \
  ':(exclude)docs/part-3-plan.md' \
  ':(exclude)docs/hpc-setup.md' \
  ':(exclude)docs/viva-qa-prep.md' \
  ':(exclude)docs/viva-qa-part3.md' \
  ':(exclude)docs/viva-day-checklist.md' \
  ':(exclude)state.md' \
  ':(exclude)scripts/make_lms_bundle.sh'
cp "$report" "$out/Part${part}-Report-Text-to-SQL.pdf"
echo "LMS bundle ($(git rev-parse --short HEAD)) written to $out:"
ls -la "$out"
