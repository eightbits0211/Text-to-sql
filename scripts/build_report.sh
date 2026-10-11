#!/bin/bash
# Build docs/part-2-report.{tex,pdf} from the Markdown source (single source of truth).
# Requires pandoc and xelatex (MacTeX).
set -euo pipefail
cd "$(dirname "$0")/../docs"
pandoc part-2-report.md \
  --from markdown+tex_math_dollars+pipe_tables+implicit_figures+table_captions \
  --standalone --number-sections --pdf-engine=xelatex \
  -V documentclass=article -V fontsize=10pt -V geometry:margin=1in \
  -V colorlinks=true -V linkcolor=blue!60!black -V urlcolor=blue!60!black \
  -V header-includes='\usepackage{float}\floatplacement{figure}{H}\renewcommand{\thesection}{\alph{section}}' \
  -o part-2-report.tex
for _ in 1 2; do
  xelatex -interaction=nonstopmode -halt-on-error part-2-report.tex >/dev/null
done
grep -c "Missing character" part-2-report.log || true
rm -f part-2-report.aux part-2-report.log part-2-report.out
echo "built docs/part-2-report.pdf"
