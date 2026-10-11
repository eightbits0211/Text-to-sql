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
git archive --format=zip --prefix=Text-to-SQL-Part2/ -o "$out/Text-to-SQL-Part2-code.zip" HEAD
cp docs/part-2-report.pdf "$out/Part2-Report-Text-to-SQL.pdf"
echo "LMS bundle ($(git rev-parse --short HEAD)) written to $out:"
ls -la "$out"
