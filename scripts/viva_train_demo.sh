#!/bin/bash
# Run from the laptop during the viva: submits the small T5 training job to
# the HPC and streams its log live until it finishes. If the shared GPU
# partition does not start the job within WAIT_SECONDS (default 120), the job
# is cancelled and the same demo runs locally instead, so training is always shown.
#   scripts/viva_train_demo.sh                 # t5-small on soccer_2
#   DEMO_ARGS="--epochs 20" scripts/viva_train_demo.sh
#   LOCAL=1 scripts/viva_train_demo.sh         # skip the HPC
set -euo pipefail
WAIT_SECONDS=${WAIT_SECONDS:-120}
HPC="csisnlp_20@hpc.bits-hyderabad.ac.in"
SSH=(ssh -q -o BatchMode=yes -o ConnectTimeout=15 -i "$HOME/.ssh/csisnlp_20" "$HPC")

run_local() {
    echo "Running the same demo locally (text-to-sql-demo --train-demo --model t5)."
    cd "$(dirname "$0")/.."
    # t5-small is cached locally, so the fallback also works without internet.
    HF_HUB_OFFLINE=1 TRANSFORMERS_VERBOSITY=error uv run --extra modern python -m text_to_sql.transformer.train_demo \
        ${DEMO_ARGS:-} 2>&1 | grep -v -E "it/s\]|Loading weights|HTTP Request"
}

if [ -n "${LOCAL:-}" ]; then run_local; exit; fi

if ! job=$("${SSH[@]}" "cd ~/Text-to-sql && sbatch --parsable --export=ALL,DEMO_ARGS='${DEMO_ARGS:-}' scripts/hpc_t5_train_demo.sh"); then
    echo "Could not reach the HPC."
    run_local
    exit
fi
echo "Submitted HPC job $job; waiting up to ${WAIT_SECONDS}s for a GPU..."
if ! "${SSH[@]}" "waited=0
while squeue -h -j $job -t PD | grep -q $job; do
  [ \$waited -ge $WAIT_SECONDS ] && { scancel $job; echo 'GPU partition busy; cancelled job $job.'; exit 3; }
  sleep 2; waited=\$((waited + 2))
done
cd ~/Text-to-sql
until [ -f p3_demo_$job.log ]; do sleep 1; done
tail -n +1 -f p3_demo_$job.log & tailer=\$!
while squeue -h -j $job | grep -q $job; do sleep 2; done
sleep 2; kill \$tailer"; then
    run_local
fi
