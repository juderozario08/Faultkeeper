<#
Run every check on Windows: lint, types, tests, builds, Docker smoke test, end-to-end ingest, production image.

  scripts\check.cmd                everything (needs Docker for the last steps)
  scripts\check.cmd -Quick         lint, types, unit tests and builds only (no Docker)
  scripts\check.cmd -InstallHook   run the quick checks automatically before every git push
#>
param([switch]$Quick, [switch]$InstallHook)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($InstallHook) {
    $hook = Join-Path $Root ".git\hooks\pre-push"
    $body = "#!/bin/sh`n# Installed by scripts/check.ps1: quick checks before every push.`nexec powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"`$(git rev-parse --show-toplevel)/scripts/check.ps1`" -Quick`n"
    [IO.File]::WriteAllText($hook, $body)
    Write-Host "Installed pre-push hook: quick checks now run before every 'git push'."
    exit 0
}

$results = New-Object System.Collections.Generic.List[object]
$clock = [Diagnostics.Stopwatch]::StartNew()

function Run($label, [scriptblock]$block) {
    Write-Host ""
    Write-Host "==> $label" -ForegroundColor Magenta
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $global:LASTEXITCODE = 0
    $ok = $true
    try { & $block; if ($LASTEXITCODE -ne 0) { $ok = $false } } catch { Write-Host $_ -ForegroundColor Red; $ok = $false }
    $results.Add([pscustomobject]@{ Check = $label; Result = $(if ($ok) { "PASS" } else { "FAIL" }); Seconds = [int]$watch.Elapsed.TotalSeconds })
}
function In-Dir($dir, [scriptblock]$block) { Push-Location (Join-Path $Root $dir); try { & $block } finally { Pop-Location } }
function Npm-Install($dir) { if (-not (Test-Path (Join-Path $Root "$dir\node_modules"))) { In-Dir $dir { npm ci --no-audit --no-fund } } }
function Test-Health {
    try { Invoke-WebRequest "http://localhost:8000/api/0/health/" -UseBasicParsing -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}

# ---------------- backend ----------------
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Run "backend: install"     { In-Dir backend { uv sync --frozen } }
    Run "backend: ruff lint"   { In-Dir backend { uv run ruff check . } }
    Run "backend: ruff format" { In-Dir backend { uv run ruff format --check . } }
    Run "backend: mypy"        { In-Dir backend { uv run mypy . } }
    Run "backend: pytest"      { In-Dir backend { uv run pytest } }
    Run "pyright (editor types)" { uvx pyright }
} else {
    Write-Host "uv not found (https://docs.astral.sh/uv/); running backend checks inside Docker instead."
    Run "backend: lint, types, tests (Docker)" {
        docker compose run --rm --no-deps -T web sh -c "ruff check . && ruff format --check . && mypy . && DJANGO_SETTINGS_MODULE=faultkeeper.settings_test pytest"
    }
}

# ---------------- frontend ----------------
Run "frontend: install"   { Npm-Install frontend }
Run "frontend: lint"      { In-Dir frontend { npm run lint } }
Run "frontend: typecheck" { In-Dir frontend { npm run typecheck } }
Run "frontend: tests"     { In-Dir frontend { npm test } }
Run "frontend: build"     { In-Dir frontend { npm run build } }

# ---------------- demo storefront ----------------
Run "buggy-shop: install"   { Npm-Install "demo\buggy-shop" }
Run "buggy-shop: typecheck" { In-Dir "demo\buggy-shop" { npm run typecheck } }
Run "buggy-shop: build"     { In-Dir "demo\buggy-shop" { npm run build } }

# ---------------- docker: smoke, end-to-end, production image ----------------
if (-not $Quick) {
    $wasRunning = Test-Health
    Run "docker: stack starts and is healthy" {
        if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
        docker compose up -d --build
        if ($LASTEXITCODE -ne 0) { return }
        for ($i = 0; $i -lt 180; $i++) { if (Test-Health) { return }; Start-Sleep -Seconds 1 }
        docker compose logs --tail 50
        $global:LASTEXITCODE = 1
    }
    Run "e2e: 300 events -> exactly 7 issues" {
        docker compose run --rm --no-deps -T -v "${Root}\loadtest:/lt" web python /lt/send_events.py `
            --dsn http://79a635b512d79894d720b95fbdad5008@web:8000/3 `
            --events 300 --bugs 7 --concurrency 8 --verify --expect-exact
    }
    Run "docker: production image builds" { docker build -q -t faultkeeper:check . }
    if (-not $wasRunning) { docker compose down 2>&1 | Out-Null }
}

# ---------------- summary ----------------
Write-Host ""
$results | Format-Table -AutoSize | Out-String | Write-Host
$failed = @($results | Where-Object { $_.Result -eq "FAIL" }).Count
Write-Host ("{0} checks, {1} failed, {2}s total" -f $results.Count, $failed, [int]$clock.Elapsed.TotalSeconds) `
    -ForegroundColor $(if ($failed) { "Red" } else { "Green" })
if ($failed) { exit 1 } else { exit 0 }
