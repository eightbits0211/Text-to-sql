#!/bin/bash
#SBATCH --job-name=test_env
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=00:05:00
#SBATCH --output=test_env_%j.log

echo "=== Hostname ==="
hostname
echo "=== NVIDIA-SMI ==="
nvidia-smi
echo "=== MPS and CUDA ENV ==="
env | grep -E "CUDA|MPS|SLURM"
echo "=== Python Test ==="
/home/csisnlp_20/venv_nlp/bin/python3 -c "
import os, torch
print('CUDA_VISIBLE_DEVICES:', os.environ.get('CUDA_VISIBLE_DEVICES'))
print('CUDA Available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('Device count:', torch.cuda.device_count())
    print('Device name:', torch.cuda.get_device_name(0))
    x = torch.randn(10, 10, device='cuda')
    print('Tensor on GPU OK:', (x @ x).shape)
"
