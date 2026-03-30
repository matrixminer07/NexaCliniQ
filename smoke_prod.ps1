param(
  [Parameter(Mandatory = $true)]
  [string]$ApiBaseUrl,

  [string]$FrontendUrl = "",

  [switch]$SkipAuthFlows
)

$ErrorActionPreference = 'Stop'

function Write-Check {
  param(
    [string]$Name,
    [bool]$Ok,
    [string]$Detail = ""
  )
  if ($Ok) {
    Write-Host ("[PASS] " + $Name + " " + $Detail) -ForegroundColor Green
  } else {
    Write-Host ("[FAIL] " + $Name + " " + $Detail) -ForegroundColor Red
  }
}

function Invoke-Json {
  param(
    [string]$Method,
    [string]$Url,
    [object]$Body = $null
  )

  if ($null -eq $Body) {
    return Invoke-RestMethod -Uri $Url -Method $Method -TimeoutSec 30
  }

  return Invoke-RestMethod -Uri $Url -Method $Method -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 10) -TimeoutSec 30
}

$api = $ApiBaseUrl.TrimEnd('/')
$failures = 0

Write-Host "=== PharmaNexus Production Smoke ===" -ForegroundColor Cyan
Write-Host ("API Base: " + $api)
if ($FrontendUrl) {
  Write-Host ("Frontend: " + $FrontendUrl)
}

# 1) API health
try {
  $health = Invoke-Json -Method GET -Url "$api/health"
  $statusValue = $null
  if ($health -and $health.PSObject.Properties.Name -contains 'status') {
    $statusValue = $health.status
  } elseif ($health -and $health.PSObject.Properties.Name -contains 'data' -and $health.data -and $health.data.PSObject.Properties.Name -contains 'status') {
    $statusValue = $health.data.status
  }
  $ok = ($null -ne $health) -and ($statusValue -eq 'healthy')
  Write-Check -Name "GET /health" -Ok $ok -Detail ("status=" + $statusValue)
  if (-not $ok) { $failures++ }
} catch {
  Write-Check -Name "GET /health" -Ok $false -Detail $_.Exception.Message
  $failures++
}

# 2) Model info
try {
  $mi = Invoke-Json -Method GET -Url "$api/model/info"
  $ok = $null -ne $mi
  Write-Check -Name "GET /model/info" -Ok $ok
  if (-not $ok) { $failures++ }
} catch {
  Write-Check -Name "GET /model/info" -Ok $false -Detail $_.Exception.Message
  $failures++
}

# 3) Core prediction
$payload = @{
  compound_name = "SmokeCompoundA"
  toxicity = 0.30
  bioavailability = 0.70
  solubility = 0.60
  binding = 0.80
  molecular_weight = 0.50
}
try {
  $pred = Invoke-Json -Method POST -Url "$api/predict" -Body $payload
  $score = $pred.success_probability
  if ($null -eq $score -and $pred.data) { $score = $pred.data.success_probability }
  $ok = $null -ne $score
  Write-Check -Name "POST /predict" -Ok $ok -Detail ("score=" + $score)
  if (-not $ok) { $failures++ }
} catch {
  Write-Check -Name "POST /predict" -Ok $false -Detail $_.Exception.Message
  $failures++
}

# 4) History and scenarios
foreach ($path in @('/history','/scenarios','/stats')) {
  try {
    $null = Invoke-Json -Method GET -Url ($api + $path)
    Write-Check -Name ("GET " + $path) -Ok $true
  } catch {
    Write-Check -Name ("GET " + $path) -Ok $false -Detail $_.Exception.Message
    $failures++
  }
}

# 5) CORS preflight spot check
try {
  $resp = Invoke-WebRequest -Uri "$api/predict" -Method Options -TimeoutSec 20
  $ok = ($resp.StatusCode -eq 200 -or $resp.StatusCode -eq 204)
  Write-Check -Name "OPTIONS /predict" -Ok $ok -Detail ("http=" + $resp.StatusCode)
  if (-not $ok) { $failures++ }
} catch {
  Write-Check -Name "OPTIONS /predict" -Ok $false -Detail $_.Exception.Message
  $failures++
}

# 6) Frontend reachability (optional)
if ($FrontendUrl) {
  try {
    $f = Invoke-WebRequest -Uri $FrontendUrl -Method Get -TimeoutSec 20
    $ok = $f.StatusCode -eq 200
    Write-Check -Name "GET Frontend" -Ok $ok -Detail ("http=" + $f.StatusCode)
    if (-not $ok) { $failures++ }
  } catch {
    Write-Check -Name "GET Frontend" -Ok $false -Detail $_.Exception.Message
    $failures++
  }
}

if ($failures -gt 0) {
  Write-Host ("Smoke failed with " + $failures + " issue(s).") -ForegroundColor Red
  exit 1
}

Write-Host "Smoke passed. Safe for DNS cutover." -ForegroundColor Green
exit 0
