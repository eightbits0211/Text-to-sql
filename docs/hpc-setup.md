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

## Information still needed

The currently supplied connection details are:

- Hostname: `hpc.bits-hyderabad.ac.in`
- Username: `csisnlp_20`
- Private key path: `~/.ssh/csisnlp_20`
- Port: assumed to be 22 unless the HPC documentation says otherwise

Before configuring a local alias, still confirm:

- SSH port, if not 22
- Remote project directory
- Whether the cluster requires a login node or a scheduler
- Scheduler type and requested resource format, if applicable

Do not infer these values from the key filename.

## Intended workflow

1. Confirm the HPC connection details.
2. Create a local SSH alias that references the existing key path.
3. Test a non-destructive SSH connection.
4. Create or clone the repository on the HPC.
5. Create the same Python 3.12/`uv` environment where supported.
6. Run CPU smoke tests before requesting GPU resources.
7. Submit training through the cluster scheduler rather than running long jobs
   on a login node.
8. Keep checkpoints and datasets in approved HPC storage, not Git.
9. Copy only reproducible metrics and report-ready artifacts back to the local
   workspace.

The provided connection was tested successfully on 2026-09-21 using a
non-destructive authentication command. The remote project directory and
scheduler are still not confirmed.

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
