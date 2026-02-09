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
    Write-Host "Skipped server update (-NoServer)." -ForegroundColor Yellow
    exit 0
}

$sshArgs = @("-o", "ConnectTimeout=12")
if (-not $AllowPasswordPrompt) {
    $sshArgs += @("-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new")
    Run-Step -Title "Check SSH key access" -Executable "ssh" -Arguments ($sshArgs + @($Server, "echo ok"))
}

$serverCommands = @(
    "set -euo pipefail",
    "cd '$ServerPath'",
    'old_head=$(git rev-parse HEAD)',
    "git fetch '$Remote' '$Branch'",
    "git checkout '$Branch'"
)

if ($ForceServerReset) {
    $serverCommands += "git reset --hard '$Remote/$Branch'"
} else {
    $serverCommands += "git pull --ff-only '$Remote' '$Branch'"
}

$serverCommands += @(
    'new_head=$(git rev-parse HEAD)',
    'changed_files=$(git diff --name-only "$old_head" "$new_head" || true)',
    'if echo "$changed_files" | grep -q "^requirements\\.txt$" || echo "$changed_files" | grep -q "^pyproject\\.toml$"; then echo "Backend dependency changes detected. Installing Python requirements..."; python3 -m pip install -r requirements.txt; else echo "No backend dependency changes. Skipping pip install."; fi',
    (@'
if echo "$changed_files" | grep -q "^frontend/" || echo "$changed_files" | grep -q "^ecosystem\\.config\\.js$"; then echo "Frontend-related changes detected. Running build steps..."; if echo "$changed_files" | grep -q "^frontend/package-lock\\.json$" || echo "$changed_files" | grep -q "^frontend/package\\.json$"; then cd '{0}/frontend'; npm ci --include=dev; cd '{0}'; else echo "Dependency files unchanged. Skipping npm ci."; fi; cd '{0}/frontend'; npm run build; cd '{0}'; else echo "No frontend changes. Skipping npm ci/build."; fi
'@ -f $ServerPath),
    "pm2 delete frontend || true",
    "pm2 startOrReload '$Pm2Config' --update-env",
    "pm2 save",
    'echo SERVER_HEAD: $(git rev-parse --short HEAD)',
    "git status --short",
    "pm2 status"
)

$serverScript = $serverCommands -join "; "
$sshDisplay = "ssh $($sshArgs -join ' ') $Server `"$serverScript`""
Run-Step -Title "Update server and reload services" -Executable "ssh" -Arguments ($sshArgs + @($Server, $serverScript)) -DisplayCommand $sshDisplay

Write-Host ""
Write-Host "Deploy completed successfully." -ForegroundColor Green
