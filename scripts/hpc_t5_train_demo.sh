#!/bin/bash
#SBATCH --job-name=csis_p3_demo
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:20:00
#SBATCH --output=p3_demo_%j.log

# Viva live-training demo: t5-small on one Spider database, a few minutes.
# Submitted and streamed by scripts/viva_train_demo.sh. DEMO_ARGS overrides,
# e.g. DEMO_ARGS="--databases soccer_2 --epochs 20" (no commas in --export).
# Do NOT change --qos or remove --gres=mps:50 (see docs/hpc-setup.md).
set -euo pipefail
export TEXT2SQL_DATA_ROOT=/home/csisnlp_20/datasets
export PYTHONUNBUFFERED=1
export TORCH_DISABLE_NATIVE_JIT=1
export HF_HUB_OFFLINE=1
export PYTHONPATH=/home/csisnlp_20/Text-to-sql/src:/home/csisnlp_20/Text-to-sql
export TRANSFORMERS_VERBOSITY=error
cd /home/csisnlp_20/Text-to-sql
echo "Job ${SLURM_JOB_ID} on $(hostname) ($(nvidia-smi --query-gpu=name --format=csv,noheader | head -1))"
/home/csisnlp_20/venv_nlp/bin/python3 -u -m text_to_sql.transformer.train_demo ${DEMO_ARGS:-} 2>&1 \
    | grep -v -E "it/s\]|Loading weights|HTTP Request"
echo "DEMO FINISHED"
