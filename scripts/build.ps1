$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $projectRoot '.venv'
$packageOutput = Join-Path $projectRoot 'build\package-output'
Push-Location $projectRoot
try {
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    python -m venv $venv
}
$python = Join-Path $venv 'Scripts\python.exe'
& $python -m pip install -r (Join-Path $projectRoot 'requirements-dev.txt')
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed with exit code $LASTEXITCODE" }
& $python (Join-Path $projectRoot 'scripts\generate_icon.py')
if ($LASTEXITCODE -ne 0) { throw "Icon generation failed with exit code $LASTEXITCODE" }
& $python -m PyInstaller --noconfirm --clean --name RGB-SOUND --onefile --noconsole `
    --distpath $packageOutput `
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
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
$builtExe = Join-Path $packageOutput 'RGB-SOUND.exe'
$finalExe = Join-Path $projectRoot 'RGB-SOUND.exe'
try {
    Copy-Item -LiteralPath $builtExe -Destination $finalExe -Force
} catch {
    throw "Cannot replace RGB-SOUND.exe. Fully exit every running RGB-SOUND window and try again. $($_.Exception.Message)"
}
Write-Host "Build complete: $finalExe"
} finally {
    Pop-Location
}
