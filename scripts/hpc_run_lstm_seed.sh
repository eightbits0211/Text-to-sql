#!/bin/bash
#SBATCH --job-name=csis_lstm_seed
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=02:00:00
#SBATCH --output=lstm_seed_%j.log

# Multi-seed replication of the Job 361547 recipe (10 WikiSQL + 25 Spider epochs).
# Train-only: checkpoints are decoded afterwards by scripts/run_ablation.py.
# Also logs per-epoch Spider dev NLL and saves a Spider epoch-10 checkpoint
# (epoch-count isolation). Usage: sbatch --export=ALL,SEED=7 scripts/hpc_run_lstm_seed.sh
#
# Do NOT change --qos or remove --gres=mps:50 (see docs/hpc-setup.md).

set -euo pipefail
SEED="${SEED:?set SEED via --export}"

echo "Job ${SLURM_JOB_ID:-interactive} on $(hostname) at $(date) | seed=${SEED}"

export TEXT2SQL_WIKISQL_SOURCE=/home/csisnlp_20/datasets/wikisql/data/dev.jsonl
export TEXT2SQL_WIKISQL_DATABASE_ROOT=/home/csisnlp_20/datasets/wikisql/data
export TEXT2SQL_SPIDER_SOURCE=/home/csisnlp_20/datasets/spider/spider_data/dev.json
export TEXT2SQL_SPIDER_SCHEMA=/home/csisnlp_20/datasets/spider/spider_data/tables.json
export TEXT2SQL_SPIDER_DATABASE_ROOT=/home/csisnlp_20/datasets/spider/spider_data/database
export TEXT2SQL_ARTIFACT_DIRECTORY=/home/csisnlp_20/artifacts/lstm-seed-${SEED}
export PYTHONUNBUFFERED=1
export TORCH_DISABLE_NATIVE_JIT=1
export PYTHONPATH=/home/csisnlp_20/Text-to-sql/src:/home/csisnlp_20/Text-to-sql

mkdir -p "${TEXT2SQL_ARTIFACT_DIRECTORY}"
cd /home/csisnlp_20/Text-to-sql

/home/csisnlp_20/venv_nlp/bin/python3 -u scripts/run_lstm_comparison.py \
    --train-limit 56000 \
    --epochs 10 \
    --spider-train-limit 7000 \
    --spider-epochs 25 \
    --batch-size 64 \
    --full-eval \
    --device cuda \
    --seed "${SEED}" \
    --save-spider-epochs 10 \
    --track-dev-loss \
    --skip-eval

echo "Finished at $(date)"
