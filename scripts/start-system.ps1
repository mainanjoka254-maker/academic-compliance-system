$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$node = (Get-Command node -ErrorAction Stop).Source
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source

$serverDist = Join-Path $root "server\dist\src\index.js"
$clientDist = Join-Path $root "client\dist"
if (!(Test-Path $serverDist) -or !(Test-Path $clientDist)) {
  throw "Build first with: npm.cmd run build"
}

function Start-Detached($name, $workingDirectory, $arguments) {
  $existing = Get-Process node -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $node }
  Start-Process -FilePath $node -WorkingDirectory $workingDirectory -ArgumentList $arguments -WindowStyle Hidden
  Write-Host "$name started"
}

Start-Detached "Academic Compliance API" (Join-Path $root "server") @($serverDist)
Start-Detached "Academic Compliance dashboard" (Join-Path $root "client") @((Join-Path $root "client\node_modules\vite\bin\vite.js"), "preview", "--host", "0.0.0.0", "--port", "5173")
Write-Host "Dashboard: http://localhost:5173"
Write-Host "API health: http://localhost:4000/health"
