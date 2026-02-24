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
    [string]$ServerPath = "/root/Rapot",

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
        [string]$Executable,
        [Parameter(Mandatory = $false)]
        [string[]]$Arguments = @(),
        [Parameter(Mandatory = $false)]
        [string]$DisplayCommand = ""
    )

    if ([string]::IsNullOrWhiteSpace($DisplayCommand)) {
        $DisplayCommand = "$Executable $($Arguments -join ' ')".Trim()
    }

    Write-Host ""
    Write-Host "==> $Title" -ForegroundColor Cyan
    Write-Host "$DisplayCommand" -ForegroundColor DarkGray

    & $Executable @Arguments

    if (-not $?) {
        throw "Command failed: $DisplayCommand"
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $DisplayCommand"
    }
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
    Run-Step -Title "Stage all changes" -Executable "git" -Arguments @("add", "-A")

    $staged = (git diff --cached --name-only)
    if (-not [string]::IsNullOrWhiteSpace($staged)) {
        if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
            $CommitMessage = "chore: auto deploy $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        }
        Run-Step -Title "Create commit" -Executable "git" -Arguments @("commit", "-m", $CommitMessage)
    }
} else {
    Write-Host "No local changes to commit." -ForegroundColor Yellow
}

Run-Step -Title "Push to GitHub" -Executable "git" -Arguments @("push", $Remote, $Branch)

if ($NoServer) {
    Write-Host ""
    Write-Host "Skipped server deploy command output (-NoServer)." -ForegroundColor Yellow
    exit 0
}

if ($AllowPasswordPrompt) {
    Write-Host ""
    Write-Host "Note: -AllowPasswordPrompt is ignored in manual server deploy mode." -ForegroundColor Yellow
}

$serverCommands = @()
$serverCommands += "ssh $Server"
$serverCommands += "cd '$ServerPath'"
$serverCommands += "git fetch '$Remote' '$Branch'"
$serverCommands += "git checkout '$Branch'"

if ($ForceServerReset) {
    $serverCommands += "git reset --hard '$Remote/$Branch'"
} else {
    $serverCommands += "git pull --ff-only '$Remote' '$Branch'"
}

$serverCommands += @(
    "python3 -m pip install -r requirements.txt",
    "cd '$ServerPath/frontend'",
    "npm ci --include=dev",
    "npm run build",
    "cd '$ServerPath'",
    "pm2 delete frontend || true",
    "pm2 startOrReload '$Pm2Config' --update-env",
    "pm2 save",
    "echo SERVER_HEAD: `$(git rev-parse --short HEAD)",
    "git status --short",
    "pm2 status",
    "curl -I http://127.0.0.1:3000/dashboard"
)

Write-Host ""
Write-Host "==> Manual Server Deploy Commands" -ForegroundColor Cyan
Write-Host "Run the following commands on your server, in order:" -ForegroundColor Yellow
Write-Host ""
for ($i = 0; $i -lt $serverCommands.Count; $i++) {
    Write-Host ("{0}. {1}" -f ($i + 1), $serverCommands[$i]) -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Commit + push completed. Server deploy commands printed." -ForegroundColor Green
