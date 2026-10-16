#!/bin/bash
#SBATCH --job-name=csis_p3_smoke
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=02:00:00
#SBATCH --output=p3_smoke_%j.log

# Part 3 environment check: transformers + CUDA, a T5-base training step,
# and gpt-oss-20b loading (MXFP4 if supported, else bf16) on 2 dev questions.
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

$PY - <<'PY'
import torch, transformers
print("torch", torch.__version__, "transformers", transformers.__version__)
print("cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))
free, total = torch.cuda.mem_get_info(); print(f"gpu mem free {free/2**30:.1f} / {total/2**30:.1f} GiB")
PY

echo "--- T5 smoke (t5-base, 64 examples, 1 epoch, greedy decode 16 dev) ---"
$PY -u -m scripts.run_t5 --train --checkpoint google-t5/t5-base --epochs 1 --train-limit 64 --dev-limit 16 \
    --beams 1 --output-dir /home/csisnlp_20/artifacts/part3/smoke-t5

echo "--- gpt-oss-20b smoke (4 dev questions, 0 and 1 shot) ---"
$PY -u -m scripts.run_gpt --shots 0,1 --limit 4 --batch-size 2 \
    --output-dir /home/csisnlp_20/artifacts/part3/smoke-gpt
echo "Finished at $(date)"
