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

Before configuring a local alias, confirm:

- HPC hostname
- HPC username
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

## Example local-only SSH configuration

The following is a template, not a configuration to use without confirmed
values:

```sshconfig
Host project-hpc
    HostName <confirmed-hpc-hostname>
    User <confirmed-hpc-username>
    Port <confirmed-port>
    IdentityFile ~/.ssh/<confirmed-key-filename>
    IdentitiesOnly yes
```

The actual host, user, port, and key filename must remain in the user's local
SSH configuration and must not be committed.

