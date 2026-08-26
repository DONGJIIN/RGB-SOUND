$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $projectRoot '.venv'
Push-Location $projectRoot
try {
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    python -m venv $venv
}
$python = Join-Path $venv 'Scripts\python.exe'
& $python -m pip install -r (Join-Path $projectRoot 'requirements-dev.txt')
& $python -m PyInstaller --noconfirm --clean --name RGB-SOUND --onefile --noconsole `
    --distpath $projectRoot `
    --add-data "rgb_sound/static;rgb_sound/static" `
    --collect-all pycaw --collect-all comtypes --collect-all webview `
    (Join-Path $projectRoot 'app.py')
Write-Host "Build complete: $projectRoot\RGB-SOUND.exe"
} finally {
    Pop-Location
}
