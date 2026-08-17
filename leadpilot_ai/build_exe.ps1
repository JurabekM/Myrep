# =============================================================================
#  LeadPilot AI — Windows .exe build script
#  Usage:  powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "==> LeadPilot AI build" -ForegroundColor Cyan

# --- 1. Virtual environment --------------------------------------------------
if (-not (Test-Path ".\.venv")) {
    Write-Host "--> Creating virtual environment"
    python -m venv .venv
}
$python = Join-Path $root ".venv\Scripts\python.exe"

Write-Host "--> Installing dependencies"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt

# --- 2. Quality gates --------------------------------------------------------
Write-Host "--> Running tests"
& $python -m pytest tests -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed — build aborted" }

# --- 3. Clean previous artefacts --------------------------------------------
foreach ($dir in @("build", "dist")) {
    if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
}

# --- 4. PyInstaller ----------------------------------------------------------
Write-Host "--> Building the executable"
$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "LeadPilotAI",
    "--collect-all", "qtawesome",
    "--collect-submodules", "keyring.backends",
    "--hidden-import", "app.models",
    "--hidden-import", "reportlab.graphics.barcode",
    "--exclude-module", "tkinter",
    "--exclude-module", "matplotlib",
    "app\main.py"
)
& $python -m PyInstaller @pyinstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# --- 5. Result ---------------------------------------------------------------
$exe = Join-Path $root "dist\LeadPilotAI\LeadPilotAI.exe"
if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host ""
    Write-Host "BUILD OK" -ForegroundColor Green
    Write-Host "  $exe  ($size MB)"
    Write-Host "  Data directory at runtime: %APPDATA%\LeadPilotAI"
} else {
    throw "Executable was not produced"
}
