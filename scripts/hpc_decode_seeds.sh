#!/bin/bash
#SBATCH --job-name=csis_lstm_decode
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=02:00:00
#SBATCH --output=lstm_decode_%j.log

# Decode the multi-seed checkpoints (final and Spider-epoch-10) on full Spider
# dev and test with the as-submitted and final inference configurations.
# Official exact-set-match scoring is run afterwards on the synced predictions.
# Do NOT change --qos or remove --gres=mps:50 (see docs/hpc-setup.md).

set -euo pipefail
echo "Job ${SLURM_JOB_ID:-interactive} on $(hostname) at $(date)"
export TEXT2SQL_DATA_ROOT=/home/csisnlp_20/datasets
export PYTHONUNBUFFERED=1
export TORCH_DISABLE_NATIVE_JIT=1
export PYTHONPATH=/home/csisnlp_20/Text-to-sql/src:/home/csisnlp_20/Text-to-sql
cd /home/csisnlp_20/Text-to-sql

for seed in 42 7 13; do
  ckdir=/home/csisnlp_20/artifacts/lstm-seed-${seed}/lstm-checkpoint
  for ckpt in spider_checkpoint spider_epoch10_checkpoint; do
    [ -f "${ckdir}/${ckpt}.pt" ] || { echo "missing ${ckdir}/${ckpt}.pt"; continue; }
    for split in dev test; do
      /home/csisnlp_20/venv_nlp/bin/python3 -u -m scripts.run_ablation \
        --checkpoint "${ckdir}/${ckpt}.pt" --dataset spider --split "${split}" \
        --variants as_submitted,mask_render --workers 2 --no-official \
        --output-dir "/home/csisnlp_20/artifacts/decode/seed-${seed}/${ckpt}/spider-${split}"
    done
  done
done
echo "Finished at $(date)"
