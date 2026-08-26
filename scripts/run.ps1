$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $projectRoot '.venv'
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    python -m venv $venv
}
& (Join-Path $venv 'Scripts\python.exe') -m pip install -r (Join-Path $projectRoot 'requirements.txt')
& (Join-Path $venv 'Scripts\python.exe') (Join-Path $projectRoot 'app.py')

