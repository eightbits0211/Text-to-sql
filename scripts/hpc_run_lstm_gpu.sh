#!/bin/bash
#SBATCH --job-name=csis_gpu_lstm
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=02:00:00
#SBATCH --output=lstm_gpu_%j.log

# Do NOT change --qos or remove --gres=mps:50 — this partition only
# accepts mps jobs under this QOS. Requesting --gres=gpu:1 or a
# different QOS here will be rejected at submission.

set -euo pipefail

echo "=========================================================="
echo "  CS F429 Text-to-SQL — LSTM GPU Training Job on Slurm"
echo "  Job ID: ${SLURM_JOB_ID:-interactive}"
echo "  Node  : $(hostname)"
echo "  Date  : $(date)"
echo "=========================================================="

# Activate Python virtual environment on HPC
if [ -f "/home/csisnlp_20/venv_nlp/bin/activate" ]; then
    source /home/csisnlp_20/venv_nlp/bin/activate
fi

# Verify PyTorch and CUDA
python3 -c "import torch; print('PyTorch:', torch.__version__, '| CUDA Available:', torch.cuda.is_available(), '| Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"

# Set dataset paths on HPC storage
export TEXT2SQL_WIKISQL_SOURCE=/home/csisnlp_20/datasets/wikisql/data/dev.jsonl
export TEXT2SQL_WIKISQL_DATABASE_ROOT=/home/csisnlp_20/datasets/wikisql/data
export TEXT2SQL_SPIDER_SOURCE=/home/csisnlp_20/datasets/spider/spider_data/dev.json
export TEXT2SQL_SPIDER_SCHEMA=/home/csisnlp_20/datasets/spider/spider_data/tables.json
export TEXT2SQL_SPIDER_DATABASE_ROOT=/home/csisnlp_20/datasets/spider/spider_data/database
export TEXT2SQL_ARTIFACT_DIRECTORY=/home/csisnlp_20/artifacts/lstm-gpu-run

mkdir -p /home/csisnlp_20/artifacts/lstm-gpu-run

cd /home/csisnlp_20/Text-to-sql

# Run full LSTM training on GPU (train on up to 56,000 WikiSQL training examples for 15 epochs)
python3 scripts/run_lstm_comparison.py \
    --train-limit 56000 \
    --epochs 15 \
    --batch-size 64 \
    --smoke-limit 200 \
    --device cuda

echo "=========================================================="
echo "  LSTM GPU Training Job Finished at $(date)"
echo "=========================================================="
