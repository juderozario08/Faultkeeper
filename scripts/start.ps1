<#
Start everything on Windows: backend stack (Docker), dashboard and Buggy Shop (Vite).

  scripts\start.cmd            start (installs dependencies on first run)
  scripts\start.cmd -Ai        also run Ollama in Docker and pull the default model
  scripts\start.cmd -Reset     clear demo issues after starting
  scripts\start.cmd -NoOpen    don't open the browser
#>
param([switch]$Ai, [switch]$Reset, [switch]$NoOpen)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Run = Join-Path $Root ".run"
New-Item -ItemType Directory -Force -Path $Run | Out-Null
$Model = if ($env:INSIGHTS_MODEL) { $env:INSIGHTS_MODEL } else { "qwen2.5-coder:3b" }

function Step($text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Magenta }
function Fail($text) { Write-Host "Error: $text" -ForegroundColor Red; exit 1 }
function Need($cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Fail "$cmd is not installed. $hint" }
}
function Test-Url($url) {
    try { Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}
function Wait-Url($url, $seconds, $label) {
    for ($i = 0; $i -lt $seconds; $i++) {
        if (Test-Url $url) { return }
        Start-Sleep -Seconds 1
    }
    Fail "$label did not become ready at $url (check: docker compose logs)"
}
function Test-Docker { cmd /c "docker info >nul 2>&1"; return ($LASTEXITCODE -eq 0) }
function Invoke-Native($what) {
    # Runs a native command; fails the script if it exits non-zero.
    & $what[0] $what[1..($what.Length - 1)]
    if ($LASTEXITCODE -ne 0) { Fail "'$($what -join ' ')' failed (exit $LASTEXITCODE)" }
}

Step "Checking prerequisites"
Need docker "Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
Need node "Install Node.js 20 or newer: https://nodejs.org"
Need npm "It ships with Node.js: https://nodejs.org"

if (-not (Test-Docker)) {
    $desktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (Test-Path $desktop) { Write-Host "Starting Docker Desktop..."; Start-Process $desktop }
    for ($i = 0; $i -lt 120; $i++) { if (Test-Docker) { break }; Start-Sleep -Seconds 1 }
    if (-not (Test-Docker)) { Fail "Docker is not running. Start Docker Desktop and try again." }
}
Write-Host "Docker, Node $(node --version) OK"

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Created .env from .env.example" }

Step "Installing JavaScript dependencies (first run only)"
foreach ($app in @("frontend", "demo\buggy-shop")) {
    if (-not (Test-Path (Join-Path $app "node_modules"))) {
        Push-Location $app
        Invoke-Native @("npm", "ci", "--no-audit", "--no-fund")
        Pop-Location
    } else { Write-Host "${app}: already installed" }
}

Step "Starting backend services (Docker)"
$compose = @("docker", "compose")
if ($Ai) { $compose += @("--profile", "ai") }
Invoke-Native ($compose + @("up", "-d", "--build"))
Write-Host "Waiting for the API..."
Wait-Url "http://localhost:8000/api/0/health/" 180 "The API"
Write-Host "API is healthy"

if ($Ai) {
    Step "Pulling the Insights model ($Model), first run can take a few minutes"
    Invoke-Native @("docker", "compose", "exec", "-T", "ollama", "ollama", "pull", $Model)
}
if ($Reset) {
    Step "Clearing demo issues"
    Invoke-Native @("docker", "compose", "exec", "-T", "web", "python", "manage.py", "reset_demo")
}

function Start-Vite($name, $dir, $port) {
    if (Test-Url "http://localhost:$port/") { Write-Host "$name already running on :$port"; return }
    # Launch fully detached (no inherited console/pipes), so it keeps running after
    # this window closes and never holds the caller's output open.
    $log = Join-Path $Run "$name.log"
    $result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine      = "cmd.exe /c node node_modules\vite\bin\vite.js > `"$log`" 2>&1"
        CurrentDirectory = (Join-Path $Root $dir)
    }
    if ($result.ReturnValue -ne 0) { Fail "Could not start $name (code $($result.ReturnValue))" }
    Set-Content -Path (Join-Path $Run "$name.pid") -Value $result.ProcessId
    Wait-Url "http://localhost:$port/" 60 $name
    Write-Host "$name running on :$port (log: .run\$name.log)"
}

Step "Starting the dashboard and the Buggy Shop"
Start-Vite "dashboard" "frontend" 5173
Start-Vite "buggy-shop" "demo\buggy-shop" 5174

if (-not $Ai) {
    if (Test-Url "http://localhost:11434/api/tags") { Write-Host "Ollama detected on :11434 (Issue Insights enabled)" }
    else { Write-Host "Tip: install Ollama (https://ollama.com) and run 'ollama pull $Model' to enable Issue Insights." }
}

Write-Host ""
Write-Host "Faultkeeper is running" -ForegroundColor Green
Write-Host "  Dashboard   http://localhost:5173   (admin@faultkeeper.local / faultkeeper)"
Write-Host "  Buggy Shop  http://localhost:5174   (click 'Break things')"
Write-Host "  Demo API    http://localhost:5175"
Write-Host "  Admin       http://localhost:8000/admin/"
Write-Host ""
Write-Host "Stop everything with: scripts\stop.cmd"

if (-not $NoOpen) {
    Start-Process "http://localhost:5174"
    Start-Process "http://localhost:5173"
}
