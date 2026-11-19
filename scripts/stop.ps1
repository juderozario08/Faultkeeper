<#
Stop everything started by start.ps1. Data (database, models) is kept.

  scripts\stop.cmd             stop all services
  scripts\stop.cmd -WipeData   also delete the database and model volumes
#>
param([switch]$WipeData)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Run = Join-Path $Root ".run"

foreach ($name in @("dashboard", "buggy-shop")) {
    $pidFile = Join-Path $Run "$name.pid"
    if (Test-Path $pidFile) {
        $id = [int](Get-Content $pidFile)
        if (Get-Process -Id $id -ErrorAction SilentlyContinue) {
            cmd /c "taskkill /PID $id /T /F >nul 2>&1"  # the whole tree (cmd -> node)
            Write-Host "Stopped $name (pid $id)"
        }
        Remove-Item $pidFile -Force
    }
}

# Fallback: any Node process still holding the dev-server ports.
foreach ($port in @(5173, 5174)) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        $proc = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -eq "node") {
            Stop-Process -Id $proc.Id -Force -Confirm:$false
            Write-Host "Stopped node on :$port (pid $($proc.Id))"
        }
    }
}

cmd /c "docker info >nul 2>&1"
if ($LASTEXITCODE -eq 0) {
    if ($WipeData) {
        docker compose --profile ai down -v
        Write-Host "Containers stopped and data volumes deleted."
    } else {
        docker compose --profile ai down
        Write-Host "Containers stopped. Data is kept."
    }
} else {
    Write-Host "Docker isn't running; nothing to stop there."
}
