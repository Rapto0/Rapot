[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    "PSAvoidUsingWriteHost",
    "",
    Justification = "Interactive release helper prints commands for operator review."
)]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9a-fA-F]{40}$")]
    [string]$VerifiedCommit,
    [string]$Branch = "main",
    [string]$Remote = "origin",
    [string]$Server = "root@138.68.71.27",
    [string]$ServerPath = "/root/Rapot",
    [switch]$Push,
    [switch]$IncludeMiddleware
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$GitArguments)
    $result = & git @GitArguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($GitArguments -join ' ') failed (exit $LASTEXITCODE)."
    }
    return $result
}

function ConvertTo-ShellLiteral {
    param([Parameter(Mandatory = $true)][string]$Value)
    # POSIX single-quoted string: a literal apostrophe closes/reopens the quote.
    $quote = [string][char]39
    $escapedQuote = $quote + [char]34 + $quote + [char]34 + $quote
    return $quote + $Value.Replace($quote, $escapedQuote) + $quote
}

if ($ServerPath -notmatch "^/" -or $ServerPath -match "[\r\n]") {
    throw "ServerPath must be an absolute POSIX path without line breaks."
}
if ($Branch -match "[\r\n]" -or $Remote -match "[\r\n]") {
    throw "Branch and Remote must not contain line breaks."
}
if ($Remote -notmatch "^[A-Za-z0-9][A-Za-z0-9._-]*$") {
    throw "Remote must be a configured Git remote name using letters, digits, '.', '_' or '-'."
}

$repoRoot = (Invoke-Git -GitArguments @("rev-parse", "--show-toplevel")).Trim()
Set-Location -LiteralPath $repoRoot
$null = Invoke-Git -GitArguments @("check-ref-format", "--branch", $Branch)
$currentBranch = (Invoke-Git -GitArguments @("branch", "--show-current")).Trim()
if ($currentBranch -ne $Branch) {
    throw "Current branch is '$currentBranch'; expected '$Branch'."
}
if (@(Invoke-Git -GitArguments @("status", "--porcelain")).Count -ne 0) {
    throw "Working tree must be clean. Review and commit selected changes before release."
}
$expectedHead = (Invoke-Git -GitArguments @("rev-parse", "HEAD")).Trim().ToLowerInvariant()
if ($expectedHead -ne $VerifiedCommit.ToLowerInvariant()) {
    throw "HEAD differs from VerifiedCommit. Re-run checks for the exact commit being released."
}
if ($Remote -notin @(Invoke-Git -GitArguments @("remote"))) {
    throw "Remote '$Remote' is not configured."
}

Write-Host "Verified commit supplied by operator: $expectedHead" -ForegroundColor Cyan
Write-Host "This helper does not run tests, create commits, connect over SSH, or deploy."
if ($Push) {
    $null = Invoke-Git -GitArguments @("push", $Remote, "${expectedHead}:refs/heads/$Branch")
    $remoteHead = @(Invoke-Git -GitArguments @("ls-remote", "--heads", $Remote, "refs/heads/$Branch"))
    if ($remoteHead.Count -ne 1 -or ($remoteHead[0] -split "\s+")[0] -ne $expectedHead) {
        throw "Remote branch does not match the verified commit. Do not deploy."
    }
    Write-Host "Push verified at the same full commit SHA." -ForegroundColor Green
} else {
    Write-Host "No push requested. Use -Push after completing the release checks." -ForegroundColor Yellow
}

$preflight = @'
set -eu
cd -- __SERVER_PATH__
test -z "$(git status --porcelain)" || { echo 'STOP: server checkout is dirty'; exit 1; }
git branch --show-current
git rev-parse HEAD
docker compose version
docker compose ps --all
ps -eo pid,ppid,comm
if command -v systemctl >/dev/null 2>&1; then
  systemctl --no-pager list-units --type=service --state=running
  systemctl --no-pager list-unit-files --type=service --state=enabled
fi
'@

$deployment = @'
set -eu
EXPECTED_COMMIT=__EXPECTED_COMMIT__
cd -- __SERVER_PATH__
test -z "$(git status --porcelain)" || { echo 'STOP: server checkout is dirty'; exit 1; }
test "$(git branch --show-current)" = __BRANCH__ || { echo 'STOP: unexpected server branch'; exit 1; }
command -v ss >/dev/null
command -v pgrep >/dev/null
if pgrep -f 'PM2.*God Daemon' >/dev/null; then
  echo 'STOP: active PM2 daemon; identify and migrate legacy processes first'
  exit 1
fi
if command -v systemctl >/dev/null 2>&1; then
  legacy_units="$(systemctl --no-legend list-units --type=service --state=active,activating | grep -Ei 'rapot|trading[-_]bot' || true)"
  test -z "$legacy_units" || { echo 'STOP: active legacy systemd service'; printf '%s\n' "$legacy_units"; exit 1; }
fi
for pid in $(pgrep -f '(python[^ ]* .*main[.]py|uvicorn.*api[.]main|start-api[.]sh)' || true); do
  if test -r "/proc/$pid/cgroup" && ! grep -Eq 'docker|containerd|kubepods' "/proc/$pid/cgroup"; then
    echo "STOP: host Python/API process $pid requires ownership review before migration"
    exit 1
  fi
done
check_port() {
  host_port="$1"; service="$2"; container_port="$3"
  if ss -H -ltn "sport = :$host_port" | grep -q .; then
    container="$(docker compose --profile middleware ps -q "$service")"
    test -n "$container" || { echo "STOP: port $host_port has an unknown owner"; exit 1; }
    docker port "$container" "$container_port/tcp" | grep -Eq ":$host_port$" || {
      echo "STOP: port $host_port does not belong to the expected Compose service"
      exit 1
    }
  fi
}
check_port 3000 frontend 3000
check_port 8000 api 8000
check_port 5000 bot 5000
__MIDDLEWARE_PORT__
git fetch --no-tags __REMOTE__ __BRANCH__
test "$(git rev-parse FETCH_HEAD)" = "$EXPECTED_COMMIT" || { echo 'STOP: remote commit changed'; exit 1; }
git merge --ff-only "$EXPECTED_COMMIT"
test "$(git rev-parse HEAD)" = "$EXPECTED_COMMIT" || { echo 'STOP: server commit mismatch'; exit 1; }
test -z "$(git status --porcelain)" || { echo 'STOP: server checkout changed'; exit 1; }
test -f .env || { echo 'STOP: production .env is missing'; exit 1; }
test -n "${RAPOT_DATA_DIR:-}" || { echo 'STOP: export the reviewed absolute RAPOT_DATA_DIR'; exit 1; }
case "$RAPOT_DATA_DIR" in /*) ;; *) echo 'STOP: RAPOT_DATA_DIR must be absolute'; exit 1;; esac
test -d "$RAPOT_DATA_DIR" || { echo 'STOP: reviewed data directory is missing'; exit 1; }
test -f "$RAPOT_DATA_DIR/trading_bot.db" || {
  test "${RAPOT_ALLOW_EMPTY_DATA:-}" = 1 || { echo 'STOP: existing database is missing'; exit 1; }
}
export RAPOT_RELEASE="$EXPECTED_COMMIT"
docker compose config --quiet
docker compose build api bot frontend
docker compose up -d --wait --wait-timeout 180 api bot frontend
__MIDDLEWARE__
curl --fail --silent --show-error http://127.0.0.1:8000/health
curl --fail --silent --show-error http://127.0.0.1:5000/health
curl --fail --silent --show-error --output /dev/null http://127.0.0.1:3000/
test "$(git rev-parse HEAD)" = "$EXPECTED_COMMIT"
docker compose ps --all
echo "Server checks passed for $EXPECTED_COMMIT; verify authenticated UI and reverse proxy separately."
'@

$middlewareCommands = "# Optional middleware profile was not requested."
$middlewarePort = "# Optional middleware port is not used."
if ($IncludeMiddleware) {
    $middlewarePort = "check_port 8001 middleware 8001"
    $middlewareCommands = @'
docker compose --profile middleware config --quiet
docker compose --profile middleware build middleware
docker compose --profile middleware up -d --wait --wait-timeout 180 middleware
curl --fail --silent --show-error http://127.0.0.1:8001/health
'@
}

foreach ($name in @("preflight", "deployment")) {
    $text = Get-Variable -Name $name -ValueOnly
    $text = $text.Replace("__SERVER_PATH__", (ConvertTo-ShellLiteral $ServerPath))
    $text = $text.Replace("__EXPECTED_COMMIT__", (ConvertTo-ShellLiteral $expectedHead))
    $text = $text.Replace("__BRANCH__", (ConvertTo-ShellLiteral $Branch))
    $text = $text.Replace("__REMOTE__", (ConvertTo-ShellLiteral $Remote))
    $text = $text.Replace("__MIDDLEWARE__", $middlewareCommands)
    $text = $text.Replace("__MIDDLEWARE_PORT__", $middlewarePort)
    Set-Variable -Name $name -Value $text
}

Write-Host ""
Write-Host "Recorded server (access unverified): $Server" -ForegroundColor Yellow
Write-Host "Open an authorized server shell. First run this read-only inventory block:" -ForegroundColor Cyan
Write-Host $preflight
Write-Host ""
Write-Host "Before proceeding, follow scripts/DEPLOY.md: identify legacy processes, back up data, and prepare the environment." -ForegroundColor Yellow
Write-Host "Unknown bot ownership or unresolved data paths block deployment. Never stop unknown processes automatically."
Write-Host "Then review and run this deployment block:" -ForegroundColor Cyan
Write-Host $deployment
Write-Host ""
Write-Host "Commands printed only. No server deployment was performed." -ForegroundColor Yellow
