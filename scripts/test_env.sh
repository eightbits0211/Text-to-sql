#!/bin/bash
#SBATCH --job-name=test_env
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=00:15:00
#SBATCH --output=%x_%j.log

echo "=== Hostname ==="
hostname
echo "=== NVIDIA-SMI ==="
nvidia-smi
echo "=== MPS and CUDA ENV ==="
env | grep -E "CUDA|MPS|SLURM"
echo "=== Python Test Starting ==="
/home/csisnlp_20/venv_nlp/bin/python3 -u -c "
import os, sys, torch
print('Python version:', sys.version, flush=True)
print('CUDA_VISIBLE_DEVICES:', os.environ.get('CUDA_VISIBLE_DEVICES'), flush=True)
print('CUDA Available:', torch.cuda.is_available(), flush=True)
if torch.cuda.is_available():
    print('Device count:', torch.cuda.device_count(), flush=True)
    print('Device name:', torch.cuda.get_device_name(0), flush=True)
    print('CUDA capability:', torch.cuda.get_device_capability(0), flush=True)
    x = torch.randn(10, 10, device='cuda')
    print('Tensor allocation on GPU OK:', x.device, flush=True)
    y = x @ x
    print('Tensor matrix multiplication on GPU OK:', y.shape, flush=True)
    print('ALL GPU TESTS PASSED SUCCESSFULLY!', flush=True)
"
echo "=== Python Test Completed ==="
