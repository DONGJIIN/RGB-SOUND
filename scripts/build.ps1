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
& $python (Join-Path $projectRoot 'scripts\generate_icon.py')
& $python -m PyInstaller --noconfirm --clean --name RGB-SOUND --onefile --noconsole `
    --distpath $projectRoot `
    --add-data "rgb_sound/static;rgb_sound/static" `
    --icon (Join-Path $projectRoot 'assets\rgb-sound.ico') `
    --version-file (Join-Path $projectRoot 'scripts\version_info.txt') `
    --exclude-module comtypes.test `
    --exclude-module tkinter `
    --exclude-module pytest `
    --exclude-module webview.platforms.android `
    --exclude-module webview.platforms.cocoa `
    --exclude-module webview.platforms.gtk `
    --exclude-module webview.platforms.qt `
    (Join-Path $projectRoot 'app.py')
Write-Host "Build complete: $projectRoot\RGB-SOUND.exe"
} finally {
    Pop-Location
}
