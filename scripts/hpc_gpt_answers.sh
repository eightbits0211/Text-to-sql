#!/bin/bash
#SBATCH --job-name=csis_p3_gptans
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=00:30:00
#SBATCH --output=p3_gptans_%j.log

# Precompute the gpt-oss-20b answers the laptop CLI demo shows. Extra viva
# questions: sbatch --export=ALL,QUESTIONS=/path/to/questions.tsv ...
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

# Precompute gpt-oss-20b answers for the CLI demo (dev + scripted + viva questions).
A=/home/csisnlp_20/artifacts/part3
$PY -u -m scripts.precompute_gpt_answers \
    --dev-predictions $A/gpt-oss-20b-0shot/spider-dev/gpt-0shot-fix2/predictions.jsonl \
    ${QUESTIONS:+--questions $QUESTIONS} --output $A/gpt_answers.json
echo "Finished at $(date)"
