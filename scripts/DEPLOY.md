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
These commands now start directly from `cd ...` (no `ssh ...` line).
Run them in an already-open server shell, in the same order.

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
- Printed command list intentionally excludes `ssh ...`; open the server shell first, then run the list.
- Printed server flow now stops `frontend` before `npm run build` and starts it after build, to avoid `.next` race/restart loops.
- Frontend runtime is pinned to Node `20.x`:
  - `.nvmrc` exists in repo root and `frontend/`.
  - deploy commands run `nvm install && nvm use` when `nvm` is available.
  - deploy commands include a hard check that fails if active Node major is not `20`.
- Deploy commands now include a hard check for `SERVER_HEAD` vs expected local head and fail if they do not match.
- Deploy commands now wait for API health (`/health`) after PM2 reload before proceeding.
