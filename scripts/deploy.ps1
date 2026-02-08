param(
    [Parameter(Mandatory = $false)]
    [string]$CommitMessage = "",

    [Parameter(Mandatory = $false)]
    [string]$Branch = "main",

    [Parameter(Mandatory = $false)]
    [string]$Remote = "origin",

    [Parameter(Mandatory = $false)]
    [string]$Server = "root@138.68.71.27",

    [Parameter(Mandatory = $false)]
    [string]$ServerPath = "/home/user/Rapot",

    [Parameter(Mandatory = $false)]
    [string]$Pm2Config = "ecosystem.config.js",

    [Parameter(Mandatory = $false)]
    [switch]$NoServer,

    [Parameter(Mandatory = $false)]
    [switch]$AllowPasswordPrompt,

    [Parameter(Mandatory = $false)]
    [switch]$ForceServerReset
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    Write-Host ""
    Write-Host "==> $Title" -ForegroundColor Cyan
    Write-Host "$Command" -ForegroundColor DarkGray
    Invoke-Expression $Command
}

# Ensure inside a git repo.
git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Current directory is not inside a Git repository."
}

$currentBranch = (git branch --show-current).Trim()
if ($currentBranch -ne $Branch) {
    throw "Current branch is '$currentBranch'. Switch to '$Branch' before deploy."
}

$status = (git status --porcelain)
if (-not [string]::IsNullOrWhiteSpace($status)) {
    Run-Step -Title "Stage all changes" -Command "git add -A"

    $staged = (git diff --cached --name-only)
    if (-not [string]::IsNullOrWhiteSpace($staged)) {
        if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
            $CommitMessage = "chore: auto deploy $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        }
        $escapedMessage = $CommitMessage.Replace('"', '\"')
        Run-Step -Title "Create commit" -Command "git commit -m `"$escapedMessage`""
    }
} else {
    Write-Host "No local changes to commit." -ForegroundColor Yellow
}

Run-Step -Title "Push to GitHub" -Command "git push $Remote $Branch"

if ($NoServer) {
    Write-Host ""
    Write-Host "Skipped server update (-NoServer)." -ForegroundColor Yellow
    exit 0
}

$sshBase = "-o ConnectTimeout=12"
if (-not $AllowPasswordPrompt) {
    $sshBase = "$sshBase -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
    Run-Step -Title "Check SSH key access" -Command "ssh $sshBase $Server `"echo ok`""
}

$serverCommands = @(
    "set -euo pipefail",
    "cd '$ServerPath'",
    "git fetch '$Remote' '$Branch'",
    "git checkout '$Branch'"
)

if ($ForceServerReset) {
    $serverCommands += "git reset --hard '$Remote/$Branch'"
} else {
    $serverCommands += "git pull --ff-only '$Remote' '$Branch'"
}

$serverCommands += @(
    "pm2 startOrReload '$Pm2Config' --update-env",
    "pm2 save",
    "echo SERVER_HEAD: `$(git rev-parse --short HEAD)",
    "git status --short",
    "pm2 status"
)

$serverScript = $serverCommands -join "; "
Run-Step -Title "Update server and reload services" -Command "ssh $sshBase $Server `"$serverScript`""

Write-Host ""
Write-Host "Deploy completed successfully." -ForegroundColor Green
