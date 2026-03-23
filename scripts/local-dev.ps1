#Requires -Version 5.1
<#
  Local Docker Compose (Windows): same behavior as Makefile dev-* / down-local.
  Run from repo root:  pwsh -File .\scripts\local-dev.ps1
  Defaults to full Windows stack (vLLM + OpenClaw). Use -Profile core for GPU-free smoke.
#>
param(
    [ValidateSet('windows', 'mac', 'core', 'down')]
    [string]$Profile = 'windows'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $RepoRoot

function Ensure-LocalEnv {
    if (-not (Test-Path '.env.local')) {
        Copy-Item '.env.local.example' '.env.local'
    }
    New-Item -ItemType Directory -Force -Path 'secrets' | Out-Null
    if (-not (Test-Path 'secrets/1password-credentials.json')) {
        Copy-Item 'secrets/1password-credentials.json.example' 'secrets/1password-credentials.json'
    }
}

function Get-DotEnvValue {
    param([string]$Key)
    $escaped = [regex]::Escape($Key)
    $line = Get-Content '.env.local' -ErrorAction SilentlyContinue |
        Where-Object { $_ -match "^\s*$escaped\s*=" } |
        Select-Object -First 1
    if (-not $line) { return $null }
    ($line -replace "^\s*$escaped\s*=\s*", '').Trim()
}

$composeArgs = @(
    'compose',
    '--env-file', '.env.local',
    '-f', 'docker-compose.local.yml'
)

Ensure-LocalEnv

if ($Profile -eq 'down') {
    & docker @composeArgs `
        --profile core --profile mac --profile windows `
        down --remove-orphans
    exit $LASTEXITCODE
}

if ($Profile -eq 'mac') {
    $model = Get-DotEnvValue 'OLLAMA_MODEL'
    if ([string]::IsNullOrWhiteSpace($model)) { $model = 'qwen2.5-coder:7b' }
    $env:LOCAL_LLM_BASE_URL = 'http://ollama:11434'
    $env:LOCAL_LLM_MODEL = $model
}
elseif ($Profile -eq 'windows') {
    $model = Get-DotEnvValue 'VLLM_MODEL'
    if ([string]::IsNullOrWhiteSpace($model)) { $model = 'Qwen/Qwen2.5-Coder-7B-Instruct' }
    $env:LOCAL_LLM_BASE_URL = 'http://vllm:8000/v1'
    $env:LOCAL_LLM_MODEL = $model
}

$profileFlag = switch ($Profile) {
    'core' { @('--profile', 'core') }
    'mac' { @('--profile', 'mac') }
    'windows' { @('--profile', 'windows') }
    default { throw "Unexpected profile: $Profile" }
}

& docker @composeArgs @profileFlag up -d --build
exit $LASTEXITCODE
