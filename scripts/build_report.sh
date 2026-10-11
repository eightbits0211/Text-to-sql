#!/bin/bash
# Build docs/part-2-report.{tex,pdf} from the Markdown source (single source of truth).
# Requires pandoc and xelatex (MacTeX).
set -euo pipefail
cd "$(dirname "$0")/../docs"
pandoc part-2-report.md \
  --from markdown+tex_math_dollars+pipe_tables+implicit_figures \
  --standalone --pdf-engine=xelatex \
  -V mainfont="Times New Roman" -V monofont="Menlo" \
  -V geometry:margin=0.9in -V fontsize=10pt -V colorlinks=true \
  -V header-includes='\usepackage{float}\floatplacement{figure}{H}' \
  -o part-2-report.tex
for _ in 1 2; do
  xelatex -interaction=nonstopmode -halt-on-error part-2-report.tex >/dev/null
done
rm -f part-2-report.aux part-2-report.log part-2-report.out
echo "built docs/part-2-report.pdf"
