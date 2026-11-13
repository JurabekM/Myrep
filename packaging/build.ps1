<#
.SYNOPSIS
    SRV_1 reliz o'rnatuvchisini yig'adi: release\SRV_1-Setup-<versiya>.exe

.DESCRIPTION
    Qadamlar:
      1. Testlar (o'tmasa o'rnatuvchi yig'ilmaydi; -SkipTests bilan o'tkazib yuboriladi).
      2. dist\SRV_1\ ga to'plam: ko'chma Python 3.12 (uv boshqaradigan), bog'liqliklar
         (uv.lock dan, xesh bilan, ishlab chiqish paketlarisiz), yadro, SDK, shell, plaginlar,
         install\ skriptlari, qo'llanma, tools\caddy.exe va tools\nssm.exe.
      3. To'plamni sinash (import) va .pyc ga kompilyatsiya.
      4. Inno Setup bilan Setup.exe (-SkipInstaller bilan o'tkazib yuboriladi).
    Faqat ASCII (PowerShell 5.1 BOM'siz UTF-8 ni noto'g'ri o'qiydi).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\build.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipInstaller,
    [string]$Iscc = ''
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$Stage = Join-Path $Repo 'dist\SRV_1'
$Release = Join-Path $Repo 'release'
# tools\README.md dagi qiymat (nssm-2.24, win64).
$NssmSha256 = 'f689ee9af94b00e9e3f0bb072b34caaf207f32dcb4f5782fc9ca351df9a06c97'

function Write-Step([string]$Text) { Write-Host "==> $Text" -ForegroundColor Cyan }
function Write-Note([string]$Text) { Write-Host "    $Text" }
function Stop-Build([string]$Text) { Write-Host "!!  $Text" -ForegroundColor Yellow; exit 1 }

function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { Stop-Build "$([IO.Path]::GetFileName($Exe)) $($Arguments[0]) xato bilan tugadi (kod $LASTEXITCODE)" }
}

function Copy-Tree([string]$From, [string]$To, [string[]]$ExcludeDirs = @(), [string[]]$ExcludeFiles = @()) {
    $arguments = @($From, $To, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:1', '/W:1')
    if ($ExcludeDirs.Count) { $arguments += '/XD'; $arguments += $ExcludeDirs }
    if ($ExcludeFiles.Count) { $arguments += '/XF'; $arguments += $ExcludeFiles }
    & robocopy.exe @arguments | Out-Null
    if ($LASTEXITCODE -ge 8) { Stop-Build "robocopy xato bilan tugadi (kod $LASTEXITCODE): $From" }
}

function Get-Version {
    $line = Select-String -LiteralPath (Join-Path $Repo 'pyproject.toml') -Pattern '^version\s*=\s*"([^"]+)"' |
        Select-Object -First 1
    if ($null -eq $line) { Stop-Build "pyproject.toml da versiya topilmadi" }
    return $line.Matches[0].Groups[1].Value
}

function Find-Iscc {
    if ($Iscc) { return $Iscc }
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    Stop-Build "ISCC.exe topilmadi. Inno Setup 6 ni o'rnating yoki -Iscc <yo'l> bering."
}

Set-Location -LiteralPath $Repo
$Version = Get-Version
$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { Stop-Build "uv topilmadi" }
$free = [math]::Round((Get-PSDrive ($Repo.Substring(0, 1))).Free / 1GB, 1)
if ($free -lt 3) { Stop-Build "Diskda atigi $free GB bo'sh joy bor; yig'ishga taxminan 2 GB kerak." }
foreach ($tool in @('caddy.exe', 'nssm.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $Repo "tools\$tool") -PathType Leaf)) {
        Stop-Build "tools\$tool yo'q (tools\README.md ga qarang)"
    }
}
$nssmHash = (Get-FileHash -LiteralPath (Join-Path $Repo 'tools\nssm.exe') -Algorithm SHA256).Hash.ToLower()
if ($nssmHash -ne $NssmSha256) { Stop-Build "tools\nssm.exe xeshi kutilganidan farq qiladi: $nssmHash" }

Write-Step "SRV_1 $Version relizi (bo'sh joy: $free GB)"

# --- 1. testlar ------------------------------------------------------------------------------
if ($SkipTests) { Write-Step "Testlar o'tkazib yuborildi (-SkipTests)" }
else {
    Write-Step "Testlar"
    Invoke-Checked $uv @('run', 'pytest', '-q', '-p', 'no:cacheprovider')
}

# --- 2. to'plam ------------------------------------------------------------------------------
Write-Step "To'plam: $Stage"
if (Test-Path -LiteralPath $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Stage | Out-Null

$base = (& $uv run --no-sync python -c "import sys; print(sys.base_prefix)").Trim()
if (-not (Test-Path -LiteralPath (Join-Path $base 'python.exe') -PathType Leaf)) {
    Stop-Build "asosiy Python topilmadi: $base"
}
$baseVersion = (& (Join-Path $base 'python.exe') -c "import sys; print('%d.%d' % sys.version_info[:2])").Trim()
if ($baseVersion -ne '3.12') { Stop-Build "Python 3.12 kerak, topilgani: $baseVersion ($base)" }
Write-Note "Python: $base"
# Kerak bo'lmagan qismlar: testlar, IDLE, tkinter/Tcl, pip. site-packages noldan to'ldiriladi.
$skipDirs = @('Lib\test', 'Lib\idlelib', 'Lib\tkinter', 'Lib\turtledemo', 'Lib\ensurepip',
    'Lib\site-packages', 'tcl', 'Scripts', 'include', 'libs', 'share') | ForEach-Object { Join-Path $base $_ }
Copy-Tree $base (Join-Path $Stage 'python') ($skipDirs + '__pycache__') `
    @('_tkinter.pyd', 'tcl86t.dll', 'tk86t.dll', 'EXTERNALLY-MANAGED', '*.pdb')
$py = Join-Path $Stage 'python\python.exe'
$site = Join-Path $Stage 'python\Lib\site-packages'
New-Item -ItemType Directory -Force -Path $site | Out-Null

Write-Step "Bog'liqliklar (uv.lock, xesh bilan)"
$requirements = Join-Path $Repo 'dist\requirements.txt'
Invoke-Checked $uv @('export', '--frozen', '--no-dev', '--no-emit-project', '--format',
    'requirements-txt', '--quiet', '-o', $requirements)
Invoke-Checked $uv @('pip', 'install', '--python', $py, '--target', $site, '--require-hashes',
    '--link-mode', 'copy', '--no-compile', '--quiet', '-r', $requirements)
if (Test-Path -LiteralPath (Join-Path $site 'bin')) { Remove-Item -LiteralPath (Join-Path $site 'bin') -Recurse -Force }
# Yadro, SDK va shell paket sifatida o'rnatilmaydi: papkalari repo tuzilmasida qoladi
# (yadro plaginlar va tools\ ni o'z fayliga nisbatan topadi).
Set-Content -LiteralPath (Join-Path $site 'srv1.pth') -Encoding ASCII `
    -Value @('..\..\..\core', '..\..\..\sdk', '..\..\..\shell')

Write-Step "SRV_1 fayllari"
$tracked = & git -C $Repo ls-files -- core sdk shell plugins install docs/qollanma.md docs/img tools/README.md
if ($LASTEXITCODE -ne 0 -or -not $tracked) { Stop-Build "git ls-files ishlamadi" }
foreach ($relative in $tracked) {
    $target = Join-Path $Stage ($relative -replace '/', '\')
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath (Join-Path $Repo $relative) -Destination $target
}
Copy-Item -LiteralPath (Join-Path $Repo 'tools\caddy.exe'), (Join-Path $Repo 'tools\nssm.exe') `
    -Destination (Join-Path $Stage 'tools')
$licenses = Join-Path $Stage 'licenses'
New-Item -ItemType Directory -Force -Path $licenses | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'THIRD-PARTY.md') -Destination $licenses
# Caddy Apache-2.0 da: litsenziya matni Python paketlaridan biridan olinadi (aynan o'sha matn).
$apache = Get-ChildItem -Path $site -Recurse -Filter 'LICENSE.APACHE' -File | Select-Object -First 1
if ($null -eq $apache) { Stop-Build "Apache-2.0 litsenziya matni topilmadi (cryptography paketida bo'lishi kerak edi)" }
Copy-Item -LiteralPath $apache.FullName -Destination (Join-Path $licenses 'Apache-2.0.txt')
Set-Content -LiteralPath (Join-Path $Stage 'VERSION') -Encoding ASCII -Value $Version

# --- 3. sinash va kompilyatsiya --------------------------------------------------------------
Write-Step "To'plamni sinash"
$check = "import srv1_core, srv1_sdk, srv1_shell, PyQt6.QtWidgets, pyqtgraph, polars, duckdb, " +
    "win32job, serial, pymodbus, paho.mqtt.client, esptool, watchdog, apscheduler; print(srv1_core.__version__)"
$reported = (& $py -I -c $check)
if ($LASTEXITCODE -ne 0) { Stop-Build "to'plamdagi Python modullarni import qila olmadi" }
if ("$reported".Trim() -ne $Version) { Stop-Build "versiya mos emas: paket '$reported', pyproject '$Version'" }
Write-Note "import: yaxshi (versiya $reported)"

Write-Step "Kompilyatsiya (.pyc)"
# O'rnatilgan papka (Program Files) yozishga yopiq: .pyc oldindan tayyorlanadi.
$app = @('core', 'sdk', 'shell', 'plugins') | ForEach-Object { Join-Path $Stage $_ }
Invoke-Checked $py (@('-I', '-m', 'compileall', '-q', '-j', '0', '--invalidation-mode', 'unchecked-hash') + $app)
# Kutubxonalarda Python 3.12 da kompilyatsiya bo'lmaydigan namuna fayllar bo'lishi mumkin - xato emas.
& $py -I -m compileall -q -j 0 --invalidation-mode unchecked-hash (Join-Path $Stage 'python\Lib') | Out-Null

$size = (Get-ChildItem -LiteralPath $Stage -Recurse -File | Measure-Object Length -Sum).Sum
Write-Note ("to'plam hajmi: {0:N0} MB" -f ($size / 1MB))

# --- 4. o'rnatuvchi --------------------------------------------------------------------------
if ($SkipInstaller) { Write-Step "O'rnatuvchi o'tkazib yuborildi (-SkipInstaller)"; exit 0 }
Write-Step "Inno Setup"
$compiler = Find-Iscc
New-Item -ItemType Directory -Force -Path $Release | Out-Null
Invoke-Checked $compiler @('/Qp', "/DAppVersion=$Version", "/DStageDir=$Stage", "/DOutputDir=$Release",
    (Join-Path $PSScriptRoot 'srv1.iss'))
$setup = Join-Path $Release "SRV_1-Setup-$Version.exe"
if (-not (Test-Path -LiteralPath $setup -PathType Leaf)) { Stop-Build "o'rnatuvchi paydo bo'lmadi: $setup" }
$hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLower()
Set-Content -LiteralPath "$setup.sha256" -Encoding ASCII -Value "$hash  SRV_1-Setup-$Version.exe"
Write-Step "Tayyor"
Write-Note $setup
Write-Note ("hajmi: {0:N1} MB" -f ((Get-Item -LiteralPath $setup).Length / 1MB))
Write-Note "SHA-256: $hash"
Write-Note "Oraliq to'plam (o'chirsa bo'ladi): $Stage"
