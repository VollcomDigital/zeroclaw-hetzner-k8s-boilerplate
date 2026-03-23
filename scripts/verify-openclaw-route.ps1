#Requires -Version 5.1
<#
  Quick check: openclaw must be Up and Traefik must route OPENCLAW_HOST (from .env.local) to port 80.
  Run from repo root: pwsh -File .\scripts\verify-openclaw-route.ps1
#>
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRoot

$envFile = Join-Path $RepoRoot '.env.local'
if (-not (Test-Path $envFile)) {
    Write-Error "Missing .env.local — copy .env.local.example first."
}

$hostHeader = 'openclaw.localhost'
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*OPENCLAW_HOST\s*=\s*(.+)\s*$') {
        $val = $Matches[1].Trim()
        if ($val) { $hostHeader = $val }
    }
}

Write-Host "Using Host: $hostHeader (from OPENCLAW_HOST in .env.local)"
& docker compose --env-file $envFile -f (Join-Path $RepoRoot 'docker-compose.local.yml') --profile windows ps openclaw
$code = curl.exe -sS -o NUL -w "%{http_code}" "http://127.0.0.1/" -H "Host: $hostHeader"
Write-Host "HTTP $code for GET http://127.0.0.1/ with Host: $hostHeader"
if ($code -eq '404') {
    Write-Host @"

404 means Traefik has no router for this Host — usually openclaw is not Up or the stack was started without --profile windows.
Recreate: docker compose --env-file .env.local -f docker-compose.local.yml --profile windows up -d --force-recreate openclaw traefik
"@
}
