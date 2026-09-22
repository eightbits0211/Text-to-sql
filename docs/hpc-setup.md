# HPC Setup Notes

The project may use the HPC for transformer fine-tuning or larger evaluation
runs. HPC access is environment-specific and must remain outside the
repository's source and configuration files.

## Security rules

- Never commit or paste the private SSH key.
- Never copy the private key into the repository, `.env` files, artifacts, or
  experiment logs.
- Keep the key in `~/.ssh/` with restrictive permissions.
- Use an SSH host alias in the user's local `~/.ssh/config`; do not hardcode
  private paths or credentials in project code.
- Store only non-sensitive setup instructions in this document.

## Confirmed Cluster Configuration (Updated 2026-09-22)

- Hostname: `hpc.bits-hyderabad.ac.in` (SSH port 22)
- Username: `csisnlp_20`
- Private key path: `~/.ssh/csisnlp_20`
- Partition: `gpu_rtx_pro_6000_6_csis_hyd`
- QOS: `gpu_csis_course`
- Resource limit: `--gres=mps:50` (MPS 50 = max half a card's compute and VRAM)
- CPUs per task: 4 (`--cpus-per-task=4`)
- Memory: 80GB (`--mem=80G`)
- Time limit: 2 hours (`--time=02:00:00`)
- Remote project directory: `/home/csisnlp_20/Text-to-sql`
- Remote datasets directory: `/home/csisnlp_20/datasets`
- HPC documentation & FAQ: <https://sharanga.hpc.bits-hyderabad.ac.in/docs/faq/>
- HPC Support: <hpc@hyderabad.bits-pilani.ac.in>

> [!IMPORTANT]
> The `gpu_rtx_pro_6000_6_csis_hyd` partition only accepts MPS jobs under the
> `gpu_csis_course` QOS. Requesting `--gres=gpu:1` or a different QOS will be
> rejected at submission. Do not change `--qos` or remove `--gres=mps:50`.

## Slurm Batch Job Template (`mock_job.sh`)

```bash
#!/bin/bash
#SBATCH --job-name=csis_gpu_job
#SBATCH --partition=gpu_rtx_pro_6000_6_csis_hyd
#SBATCH --qos=gpu_csis_course
#SBATCH --gres=mps:50
#SBATCH --cpus-per-task=4
#SBATCH --mem=80G
#SBATCH --time=02:00:00
#SBATCH --output=%x_%j.log

# Do NOT change --qos or remove --gres=mps:50 — this partition only
# accepts mps jobs under this QOS. Requesting --gres=gpu:1 or a
# different QOS here will be rejected at submission.

# Additional script content goes here
python3 your_script.py
```

## Intended workflow

1. Connect to login node: `ssh -i ~/.ssh/csisnlp_20 csisnlp_20@hpc.bits-hyderabad.ac.in`
2. Set up Python virtual environment with PyTorch + CUDA support.
3. Sync repository and dataset splits to `/home/csisnlp_20/`.
4. Submit training job using `sbatch scripts/hpc_run_lstm_gpu.sh`.
5. Monitor job via `squeue -u csisnlp_20` and inspect logs `%x_%j.log`.
6. Retrieve evaluation summary, manifest, and checkpoint artifacts back to local workspace.

## Example local-only SSH configuration

The following is a template, not a configuration to use without confirmed
values:

```sshconfig
Host project-hpc
    HostName hpc.bits-hyderabad.ac.in
    User csisnlp_20
    Port 22
    IdentityFile ~/.ssh/csisnlp_20
    IdentitiesOnly yes
```

The actual connection configuration should remain in the user's local SSH
configuration and must not be committed. The private key itself must never be
read, copied, or committed.
