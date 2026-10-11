#!/bin/bash
#SBATCH --job-name=csis_wikisql_decode
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=02:00:00
#SBATCH --output=wikisql_decode_%j.log

# Full WikiSQL dev (8,415) inference ablation on the Job 361547 Stage-1
# checkpoint (wikisql_checkpoint.pt, saved before any Spider training).
# Do NOT change --qos or remove --gres=mps:50 (see docs/hpc-setup.md).

set -euo pipefail
echo "Job ${SLURM_JOB_ID:-interactive} on $(hostname) at $(date)"
export TEXT2SQL_DATA_ROOT=/home/csisnlp_20/datasets
export PYTHONUNBUFFERED=1
export TORCH_DISABLE_NATIVE_JIT=1
export PYTHONPATH=/home/csisnlp_20/Text-to-sql/src:/home/csisnlp_20/Text-to-sql
cd /home/csisnlp_20/Text-to-sql

/home/csisnlp_20/venv_nlp/bin/python3 -u -m scripts.run_ablation \
  --checkpoint /home/csisnlp_20/artifacts/lstm-gpu-run/lstm-checkpoint/wikisql_checkpoint.pt \
  --dataset wikisql --split dev --variants raw,as_submitted,render,mask_render \
  --with-template --workers 3 \
  --output-dir /home/csisnlp_20/artifacts/decode/wikisql-dev-stage1
echo "Finished at $(date)"
