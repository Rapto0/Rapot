# Auto Deploy (Local -> GitHub -> Server)

This script automates:
1. `git add -A`
2. `git commit`
3. `git push origin main`
4. server update via SSH
5. `pm2 startOrReload ecosystem.config.js`

File: `scripts/deploy.ps1`

## 1) One-time setup (recommended)

Use SSH key auth so deploy runs without password prompts:

```powershell
ssh-keygen -t ed25519 -C "rapot-deploy"
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@138.68.71.27 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

## 2) Basic usage

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1 -CommitMessage "fix: your message"
```

## 3) Useful options

Update only local+GitHub (skip server):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1 -CommitMessage "chore: update" -NoServer
```

Allow password prompt for SSH (if key is not ready):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1 -CommitMessage "chore: update" -AllowPasswordPrompt
```

Force server to exactly match `origin/main` (destructive on server local edits):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1 -CommitMessage "deploy" -ForceServerReset
```

## Notes

- Script expects current branch to be `main`.
- Without `-ForceServerReset`, server uses `git pull --ff-only` (safer).
- If pre-commit hooks fail during commit, deploy stops so you can fix issues.
