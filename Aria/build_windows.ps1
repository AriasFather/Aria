$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv-build\Scripts\python.exe"
if (-not (Test-Path $python)) {
    py -3.11 -m venv .venv-build
    if ($LASTEXITCODE -ne 0) { throw "Could not create the build environment." }
}

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip." }

& $python -m pip install -r requirements.txt aiohttp curl-cffi colorama pyinstaller
if ($LASTEXITCODE -ne 0) { throw "Could not install Aria build dependencies." }

& $python -m PyInstaller --noconfirm --clean aria.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed to build Aria." }

Write-Host "Build complete: $PSScriptRoot\dist\Aria\Aria.exe"
Write-Host "Keep the entire dist\Aria folder together when moving or sharing the app."