# AETHER-Q Sidecar Studio paketi: testlar → release yig'ish → dist\studio\ → Inno Setup o'rnatuvchisi.
# Testlar o'tmasa o'rnatuvchi yig'ilmaydi.
#
#   powershell -ExecutionPolicy Bypass -File scripts\package-studio.ps1
#
# Natija: dist\AETHER-Q-Studio-Setup-0.1.0.exe va dist\studio\ (o'rnatmasdan ishlatish uchun nusxa).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$cargo = Join-Path $root "scripts\cargo-msvc.ps1"
$go = if ($env:GO) { $env:GO } else { Join-Path $env:USERPROFILE "tools\go\bin\go.exe" }
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"

function Step($title, [scriptblock]$body) {
    Write-Host "== $title" -ForegroundColor Cyan
    & $body
    if ($LASTEXITCODE -ne 0) { throw "$title muvaffaqiyatsiz (kod $LASTEXITCODE)" }
}

Step "ikonka va sehrgar rasmlari" { python scripts\make_icon.py }
Step "testlar (aq-sidecar, aq-studio)" { powershell -ExecutionPolicy Bypass -File $cargo test -p aq-sidecar -p aq-studio }
Step "release yig'ish" { powershell -ExecutionPolicy Bypass -File $cargo build --release -p aq-sidecar -p aq-studio }
$stage = Join-Path $root "dist\studio"
New-Item -ItemType Directory -Force $stage | Out-Null
Step "aqctl (Go)" { Push-Location control; & $go build -o (Join-Path $stage "aqctl.exe") ./cmd/aqctl; Pop-Location }
Step "aether_new (Go)" { Push-Location aether_new; & $go build -o (Join-Path $stage "aether_new.exe") .; Pop-Location }
Copy-Item target\release\aq-studio.exe, target\release\aq-sidecar.exe $stage -Force
Copy-Item installer\README.txt $stage -Force
# Qaysi binar ekanini tekshirish (Windows exe nomlari registrga sezgir emas — adashib almashmasin).
# GUI exe konsolsiz: --version o'rniga exe ichidagi fayl ma'lumoti (winresource) tekshiriladi — bu ikonka
# resursi ham kompilyatsiya qilinganini tasdiqlaydi.
$vi = (Get-Item (Join-Path $stage "aq-studio.exe")).VersionInfo
if ([string]$vi.ProductName -ne "AETHER-Q Sidecar Studio") { throw "aq-studio.exe ProductName kutilmagan: '$($vi.ProductName)'" }
Write-Host "   $($vi.ProductName) $($vi.FileVersion)"
if (-not (Test-Path $iscc)) { throw "Inno Setup topilmadi: $iscc" }
Step "o'rnatuvchi (Inno Setup)" { & $iscc /Q installer\aq-studio.iss }
Get-ChildItem dist\AETHER-Q-Studio-Setup-*.exe | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
