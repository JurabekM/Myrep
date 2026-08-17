<#
.SYNOPSIS
    Builds the ExportFlow Windows executable with PyInstaller.

.DESCRIPTION
    Creates (or reuses) a virtual environment, installs the dependencies and
    produces dist\ExportFlow\ExportFlow.exe. Pass -OneFile for a single-file
    build (slower to start, easier to copy).

.EXAMPLE
    .\build_exe.ps1
    .\build_exe.ps1 -OneFile -Clean
#>

[CmdletBinding()]
param(
    [switch]$OneFile,
    [switch]$Clean,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

Write-Host "=== ExportFlow build ===" -ForegroundColor Cyan

$venv = Join-Path $root ".venv"
if (-not (Test-Path $venv)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $Python -m venv $venv
}

$venvPython = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment python not found at $venvPython"
}

Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r (Join-Path $root "requirements.txt") --quiet

if ($Clean) {
    Write-Host "Cleaning previous build output..." -ForegroundColor Yellow
    foreach ($dir in @("build", "dist")) {
        $path = Join-Path $root $dir
        if (Test-Path $path) { Remove-Item -Recurse -Force $path }
    }
    Get-ChildItem -Path $root -Filter "*.spec" | Remove-Item -Force
}

# Data files bundled next to the executable (templates + resources).
$dataArgs = @(
    "--add-data", "app\templates;templates",
    "--add-data", "app\resources;resources"
)

$modeArgs = if ($OneFile) { @("--onefile") } else { @("--onedir") }

$hiddenImports = @(
    "--hidden-import", "app.integrations.llm.demo_provider",
    "--hidden-import", "app.integrations.llm.openai_compatible",
    "--hidden-import", "app.integrations.email.providers",
    "--hidden-import", "app.integrations.crm.providers",
    "--hidden-import", "app.integrations.marketplace.providers",
    "--hidden-import", "keyring.backends.Windows",
    "--collect-submodules", "reportlab"
)

$excludes = @(
    "--exclude-module", "tkinter",
    "--exclude-module", "PySide6.QtWebEngineCore",
    "--exclude-module", "PySide6.Qt3DCore",
    "--exclude-module", "PySide6.QtMultimedia",
    "--exclude-module", "matplotlib",
    "--exclude-module", "pytest"
)

Write-Host "Running PyInstaller..." -ForegroundColor Yellow
$arguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "ExportFlow"
) + $modeArgs + $dataArgs + $hiddenImports + $excludes + @("app\main.py")

$iconPath = Join-Path $root "app\resources\exportflow.ico"
if (Test-Path $iconPath) {
    $arguments += @("--icon", $iconPath)
}

& $venvPython @arguments
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$exe = if ($OneFile) {
    Join-Path $root "dist\ExportFlow.exe"
} else {
    Join-Path $root "dist\ExportFlow\ExportFlow.exe"
}

if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "Build finished: $exe ($size MB)" -ForegroundColor Green
    Write-Host "The application stores its data in %LOCALAPPDATA%\ExportFlow" -ForegroundColor Gray
} else {
    throw "Executable was not produced"
}
