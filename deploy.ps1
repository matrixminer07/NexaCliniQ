param(
  [switch]$Build = $true,
  [switch]$Detach = $true
)

$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

if (-not (Test-Path '.env')) {
  Copy-Item '.env.example' '.env'
  Write-Host 'Created .env from .env.example. Update secrets before production use.' -ForegroundColor Yellow
}

function Get-EnvValue {
  param([string]$Key)
  $line = Get-Content '.env' | Where-Object { $_ -match "^$Key=" } | Select-Object -Last 1
  if (-not $line) { return '' }
  return ($line -split '=', 2)[1]
}

function Test-SecretValue {
  param([string]$Key)
  $value = Get-EnvValue -Key $Key
  if ([string]::IsNullOrWhiteSpace($value)) {
    throw "Missing required $Key in .env"
  }
  if ($value.Length -lt 32) {
    throw "$Key must be at least 32 characters for production deployments"
  }
  if ($value -match 'your-secret|change-me|replace-with') {
    throw "$Key appears to be a placeholder. Set a strong random value before deploying."
  }
}

Test-SecretValue -Key 'SECRET_KEY'
Test-SecretValue -Key 'JWT_SECRET_KEY'
Test-SecretValue -Key 'AUTH_JWT_SECRET'

$composeArgs = @('compose', 'up')
if ($Build) { $composeArgs += '--build' }
if ($Detach) { $composeArgs += '-d' }

Write-Host ('Running: docker ' + ($composeArgs -join ' ')) -ForegroundColor Cyan
docker @composeArgs

Write-Host 'Services status:' -ForegroundColor Green
docker compose ps

Write-Host 'Backend health check:' -ForegroundColor Green
try {
  $resp = Invoke-WebRequest -UseBasicParsing http://localhost/health -TimeoutSec 15
  Write-Host ('HTTP ' + $resp.StatusCode)
} catch {
  Write-Host 'Health endpoint not reachable yet. Check logs with: docker compose logs -f backend nginx' -ForegroundColor Yellow
}
