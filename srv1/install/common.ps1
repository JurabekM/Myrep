# SRV_1 o'rnatish skriptlari uchun umumiy funksiyalar. Faqat ASCII (PowerShell 5.1 BOM'siz
# UTF-8 ni noto'g'ri o'qiydi).

$script:RepoRoot = Split-Path -Parent $PSScriptRoot

function Get-RepoRoot { return $script:RepoRoot }

function Get-DefaultDataDir {
    if ($env:SRV1_DATA_DIR) { return $env:SRV1_DATA_DIR }
    $base = $env:PROGRAMDATA
    if (-not $base) { $base = 'C:\ProgramData' }
    return (Join-Path $base 'SRV_1')
}

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-VenvPython([switch]$Windowless) {
    $name = 'python.exe'
    if ($Windowless) { $name = 'pythonw.exe' }
    # Setup.exe bilan o'rnatilgan nusxada ko'chma Python bor; repoda esa uv muhiti (.venv).
    $bundled = Join-Path (Get-RepoRoot) (Join-Path 'python' $name)
    if (Test-Path -LiteralPath $bundled -PathType Leaf) { return $bundled }
    return (Join-Path (Get-RepoRoot) (Join-Path '.venv\Scripts' $name))
}

function Get-ToolPath([string]$Relative) {
    return (Join-Path (Get-RepoRoot) (Join-Path 'tools' $Relative))
}

function Write-Step([string]$Text) { Write-Host "==> $Text" -ForegroundColor Cyan }
function Write-Note([string]$Text) { Write-Host "    $Text" }
function Write-Problem([string]$Text) { Write-Host "!!  $Text" -ForegroundColor Yellow }
