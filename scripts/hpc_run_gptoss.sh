#!/bin/bash
#SBATCH --job-name=csis_p3_gpt
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=02:00:00
#SBATCH --output=p3_gpt_%j.log

# gpt-oss-20b zero-shot and few-shot on Spider dev. Override with GPT_ARGS,
# e.g. --limit 200 or --shots 0 to fit the 2-hour limit.
# Do NOT change --qos or remove --gres=mps:50 (see docs/hpc-setup.md).
set -euo pipefail
echo "Job ${SLURM_JOB_ID:-interactive} on $(hostname) at $(date)"
export TEXT2SQL_DATA_ROOT=/home/csisnlp_20/datasets
export PYTHONUNBUFFERED=1
export TORCH_DISABLE_NATIVE_JIT=1
# Models are pre-downloaded on the login node; compute nodes run offline.
export HF_HUB_OFFLINE=${HF_HUB_OFFLINE:-1}
export PYTHONPATH=/home/csisnlp_20/Text-to-sql/src:/home/csisnlp_20/Text-to-sql
PY=/home/csisnlp_20/venv_nlp/bin/python3
cd /home/csisnlp_20/Text-to-sql
echo "hub reachable: $(timeout 10 curl -sI https://huggingface.co | head -1 || echo no)"

$PY -u -m scripts.run_gpt --shots 0,3 --split dev --batch-size 8 \
    --output-dir /home/csisnlp_20/artifacts/part3/gpt-oss-20b ${GPT_ARGS:-}
echo "Finished at $(date)"
