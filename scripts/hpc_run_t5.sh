#!/bin/bash
#SBATCH --job-name=csis_p3_t5
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=02:00:00
#SBATCH --output=p3_t5_%j.log

# Fine-tune T5-base on Spider train (keep best dev-loss checkpoint), then
# decode Spider dev greedy and beam-4. Override with T5_ARGS, e.g.
#   sbatch --export=ALL,T5_ARGS="--epochs 20" scripts/hpc_run_t5.sh
# Do NOT change --qos or remove --gres=mps:50 (see docs/hpc-setup.md).
set -euo pipefail
echo "Job ${SLURM_JOB_ID:-interactive} on $(hostname) at $(date)"
export TEXT2SQL_DATA_ROOT=/home/csisnlp_20/datasets
export PYTHONUNBUFFERED=1
export TORCH_DISABLE_NATIVE_JIT=1
# Models are pre-downloaded on the login node; compute nodes run offline.
export HF_HUB_OFFLINE=1
export PYTHONPATH=/home/csisnlp_20/Text-to-sql/src:/home/csisnlp_20/Text-to-sql
PY=/home/csisnlp_20/venv_nlp/bin/python3
cd /home/csisnlp_20/Text-to-sql

$PY -u -m scripts.run_t5 --train --checkpoint google-t5/t5-base --epochs 25 --batch-size 16 \
    --learning-rate 3e-4 --beams 1,4 --output-dir /home/csisnlp_20/artifacts/part3/t5-base ${T5_ARGS:-}
echo "Finished at $(date)"
