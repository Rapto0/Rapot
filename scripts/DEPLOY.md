# Deploy Flow (Local -> GitHub + Manual Server)

This script automates:
1. `git add -A`
2. `git commit`
3. `git push origin main`
4. prints server deploy commands for you to run manually

File: `scripts/deploy.ps1`

Default server path: `/root/Rapot`

## 1) Basic usage

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1 -CommitMessage "fix: your message"
```

After this command, script prints numbered server commands.
Run them on your server in the same order.

## 2) Useful options

Update only local+GitHub and do not print server commands:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1 -CommitMessage "chore: update" -NoServer
```

Force server reset command in printed output (destructive on server local edits):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1 -CommitMessage "deploy" -ForceServerReset
```

Use a custom server path:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1 -CommitMessage "deploy" -ServerPath "/home/user/Rapot"
```

## Notes

- Script expects current branch to be `main`.
- Without `-ForceServerReset`, printed commands use `git pull --ff-only` (safer).
- If pre-commit hooks fail during commit, deploy stops so you can fix issues.
- Script no longer executes SSH deploy automatically; it prints commands for manual run.
