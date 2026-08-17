<#
.SYNOPSIS
    Builds the BuildControl Windows executable with PyInstaller.

.DESCRIPTION
    Produces dist\BuildControl\BuildControl.exe by default (folder build, fastest
    start-up). Pass -OneFile for a single portable .exe.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
    powershell -ExecutionPolicy Bypass -File .\build_exe.ps1 -OneFile -Clean
#>

[CmdletBinding()]
param(
    [switch]$OneFile,
    [switch]$Clean,
    [switch]$SkipTests,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "== BuildControl build ==" -ForegroundColor Cyan

# 1. Environment ------------------------------------------------------------- #
$version = & $Python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
Write-Host "Python $version"
if ([version]$version -lt [version]"3.12") {
    throw "Python 3.12 or newer is required (found $version)."
}

Write-Host "Installing dependencies..." -ForegroundColor Cyan
& $Python -m pip install --disable-pip-version-check --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# 2. Tests -------------------------------------------------------------------- #
if (-not $SkipTests) {
    Write-Host "Running tests..." -ForegroundColor Cyan
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "tests failed - build aborted" }
}

# 3. Clean -------------------------------------------------------------------- #
if ($Clean) {
    foreach ($dir in @("build", "dist")) {
        if (Test-Path $dir) {
            Write-Host "Removing $dir"
            Remove-Item -Recurse -Force $dir
        }
    }
    Get-ChildItem -Filter "*.spec" | Remove-Item -Force -ErrorAction SilentlyContinue
}

# 4. Build -------------------------------------------------------------------- #
$arguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "BuildControl",
    "--collect-submodules", "app",
    "--paths", ".",
    "--hidden-import", "sqlalchemy.dialects.sqlite",
    "--hidden-import", "bcrypt",
    "--hidden-import", "requests",
    "--hidden-import", "paho.mqtt.client",
    "--hidden-import", "cryptography",
    "--collect-data", "certifi",
    "--collect-data", "qtawesome",
    "--exclude-module", "tkinter",
    "--exclude-module", "matplotlib",
    "--exclude-module", "PySide6.QtWebEngineCore",
    "--exclude-module", "PySide6.QtQuick",
    "--exclude-module", "PySide6.Qt3DCore"
)
if ($OneFile) { $arguments += "--onefile" }

$icon = Join-Path $PSScriptRoot "app\resources\buildcontrol.ico"
if (Test-Path $icon) { $arguments += @("--icon", $icon) }

$arguments += "run.py"

Write-Host "Running PyInstaller..." -ForegroundColor Cyan
& $Python @arguments
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# 5. Report ------------------------------------------------------------------- #
$target = if ($OneFile) { "dist\BuildControl.exe" } else { "dist\BuildControl\BuildControl.exe" }
if (Test-Path $target) {
    $size = [math]::Round((Get-Item $target).Length / 1MB, 1)
    Write-Host ""
    Write-Host "BUILD OK -> $target ($size MB)" -ForegroundColor Green
    Write-Host "Data directory: $env:APPDATA\BuildControl"
} else {
    throw "Expected output not found: $target"
}
