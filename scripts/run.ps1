param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { $projectPython = 'python' }
& $projectPython -m uvicorn agents.api:app --host 127.0.0.1 --port $Port --no-proxy-headers
exit $LASTEXITCODE
