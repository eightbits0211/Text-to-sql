#!/bin/bash
# Build docs/<name>.{tex,pdf} from the Markdown source (single source of truth).
# Usage: scripts/build_report.sh [name]   (default: part-3-report)
# Requires pandoc and xelatex (MacTeX).
set -euo pipefail
cd "$(dirname "$0")/../docs"
NAME=${1:-part-3-report}
pandoc "${NAME}.md" \
  --from markdown+tex_math_dollars+pipe_tables+implicit_figures+table_captions \
  --standalone --number-sections --pdf-engine=xelatex \
  -V documentclass=article -V fontsize=10pt -V geometry:margin=0.85in -V monofont=Menlo \
  -V colorlinks=true -V linkcolor=blue!60!black -V urlcolor=blue!60!black \
  -V header-includes='\usepackage{float}\floatplacement{figure}{H}\renewcommand{\thesection}{\alph{section}}' \
  -o ${NAME}.tex
for _ in 1 2; do
  xelatex -interaction=nonstopmode -halt-on-error ${NAME}.tex >/dev/null
done
grep -c "Missing character" ${NAME}.log || true
rm -f ${NAME}.aux ${NAME}.log ${NAME}.out
echo "built docs/${NAME}.pdf"
