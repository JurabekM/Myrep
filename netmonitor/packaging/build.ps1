<#
.SYNOPSIS
    NetMonitor.exe ni yig'adi (PyInstaller, bitta fayl) va release\ papkasiga qo'yadi.

.DESCRIPTION
    Qadamlar: alohida muhit (build\venv) -> kutubxonalar (xesh bilan, requirements-dev.txt) ->
    ruff va pytest -> PyInstaller -> yig'ilgan exe ni sinash (--version, --self-test,
    --list-ifaces) -> release\ papkasi va SHA-256.
    Imzo alohida qadam: packaging\sign.ps1.
    Faqat ASCII (PowerShell 5.1 BOM'siz UTF-8 ni noto'g'ri o'qiydi).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\build.ps1
    powershell -ExecutionPolicy Bypass -File packaging\build.ps1 -SkipTests
#>
[CmdletBinding()]
param(
    [switch]$SkipTests,
    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step([string]$Text) { Write-Host "==> $Text" -ForegroundColor Cyan }
function Write-Note([string]$Text) { Write-Host "    $Text" }
function Assert-Ok([string]$What) {
    if ($LASTEXITCODE -ne 0) { throw "$What muvaffaqiyatsiz (kod $LASTEXITCODE)" }
}

$Build = Join-Path $Root 'build'
$Release = Join-Path $Root 'release'
$Venv = Join-Path $Build 'venv'
$Py = Join-Path $Venv 'Scripts\python.exe'

Write-Step 'Muhit'
if (-not (Test-Path -LiteralPath $Py)) {
    & $Python -m venv $Venv
    Assert-Ok 'venv yaratish'
}
& $Py -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
Assert-Ok "Python versiyasi tekshiruvi (3.10 yoki yangirog'i kerak)"
& $Py -m pip install --disable-pip-version-check --quiet --require-hashes -r requirements-dev.txt
Assert-Ok "kutubxonalarni o'rnatish"
Write-Note (& $Py --version)

if (-not $SkipTests) {
    Write-Step 'Tekshiruv: ruff va pytest'
    & $Py -m ruff check .
    Assert-Ok 'ruff'
    & $Py -m pytest tests -q -p no:cacheprovider
    Assert-Ok 'pytest'
}

Write-Step 'PyInstaller'
$VersionFile = Join-Path $Build 'version_info.txt'
$Version = (& $Py packaging\make_version_info.py $VersionFile | Select-Object -Last 1).Trim()
Assert-Ok 'versiya manbasi'
Write-Note "versiya: $Version"
$Dist = Join-Path $Build 'dist'
foreach ($folder in @($Dist, (Join-Path $Build 'work'))) {
    if (Test-Path -LiteralPath $folder) { Remove-Item -LiteralPath $folder -Recurse -Force }
}
$pyinstallerArgs = @(
    '--noconfirm', '--clean', '--onefile', '--console',
    '--name', 'NetMonitor',
    '--version-file', $VersionFile,
    '--distpath', $Dist,
    '--workpath', (Join-Path $Build 'work'),
    '--specpath', $Build,
    '--collect-submodules', 'scapy.layers',
    '--collect-submodules', 'scapy.arch',
    '--collect-submodules', 'scapy.libs',
    '--exclude-module', 'tkinter',
    '--log-level', 'WARN',
    (Join-Path $Root 'netmonitor.py')
)
& $Py -m PyInstaller @pyinstallerArgs
Assert-Ok 'PyInstaller'
$Exe = Join-Path $Dist 'NetMonitor.exe'
if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "exe paydo bo'lmadi: $Exe" }

Write-Step "Yig'ilgan exe ni sinash"
$reported = (& $Exe --version | Select-Object -Last 1).Trim()
Assert-Ok '--version'
if ($reported -ne "NetMonitor $Version") { throw "versiya mos emas: '$reported'" }
Write-Note $reported
& $Exe --self-test
Assert-Ok '--self-test'
# Interfeyslar ro'yxati Npcap'siz ham chiqadi: Windows'ga xos qism yig'ilganini tekshiradi.
$probe = Join-Path $Build 'probe'
New-Item -ItemType Directory -Force -Path $probe | Out-Null
'{"log_folder": "logs"}' | Set-Content -LiteralPath (Join-Path $probe 'config.json') -Encoding ASCII
& $Exe --config (Join-Path $probe 'config.json') --list-ifaces
Assert-Ok '--list-ifaces'

Write-Step 'release\'
if (Test-Path -LiteralPath $Release) { Remove-Item -LiteralPath $Release -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Release | Out-Null
Copy-Item -LiteralPath $Exe -Destination $Release
Copy-Item -LiteralPath (Join-Path $Root 'config.example.json') -Destination $Release
Copy-Item -LiteralPath (Join-Path $Root 'README.md') -Destination (Join-Path $Release 'QOLLANMA.md')
$Final = Join-Path $Release 'NetMonitor.exe'
$hash = (Get-FileHash -LiteralPath $Final -Algorithm SHA256).Hash.ToLower()
Set-Content -LiteralPath "$Final.sha256" -Encoding ASCII -Value "$hash  NetMonitor.exe"
$sizeMb = [math]::Round((Get-Item -LiteralPath $Final).Length / 1MB, 1)

Write-Step 'Tayyor (imzolanmagan)'
Write-Note "$Final ($sizeMb MB)"
Write-Note "SHA-256: $hash"
Write-Note 'Keyingi qadam: packaging\sign.ps1'
if ($env:GITHUB_OUTPUT) { Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "version=$Version" }
