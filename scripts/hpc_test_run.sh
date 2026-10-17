#!/bin/bash
#SBATCH --job-name=csis_p3_test
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=02:00:00
#SBATCH --output=p3_test_%j.log

# ONE-TIME Spider test run (2,147 questions) for the final report. Run only
# after every setting is frozen on dev; nothing is tuned on these results.
#   sbatch --export=ALL,SYSTEM=t5 scripts/hpc_test_run.sh            # T5 greedy/beam + A/B ablation
#   sbatch --export=ALL,SYSTEM=gpt,SHOTS=0 scripts/hpc_test_run.sh   # gpt-oss best dev setting
# Do NOT change --qos or remove --gres=mps:50 (see docs/hpc-setup.md).
set -euo pipefail
echo "Job ${SLURM_JOB_ID:-interactive} on $(hostname) at $(date): SYSTEM=${SYSTEM:?set SYSTEM=t5 or gpt}"
export TEXT2SQL_DATA_ROOT=/home/csisnlp_20/datasets
export PYTHONUNBUFFERED=1
export TORCH_DISABLE_NATIVE_JIT=1
export HF_HUB_OFFLINE=${HF_HUB_OFFLINE:-1}
export PYTHONPATH=/home/csisnlp_20/Text-to-sql/src:/home/csisnlp_20/Text-to-sql
PY=/home/csisnlp_20/venv_nlp/bin/python3
A=/home/csisnlp_20/artifacts/part3
cd /home/csisnlp_20/Text-to-sql

case "$SYSTEM" in
  t5)
    $PY -u -m scripts.run_t5 --model-dir $A/t5-base-ex/best --split test \
        --beams 1,4 --novelty-k 8 --output-dir $A/test/t5-base-ex ;;
  gpt)
    $PY -u -m scripts.run_gpt --split test --shots "${SHOTS:?set SHOTS}" --batch-size 16 \
        --dequantize --correction-retries 2 --output-dir $A/test/gpt-oss-20b-${SHOTS}shot ;;
  *) echo "unknown SYSTEM=$SYSTEM"; exit 2 ;;
esac
echo "Finished at $(date)"
