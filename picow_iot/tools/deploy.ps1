# Pico W ga loyihani yuklash (mpremote orqali)
#
# Talab:  pip install mpremote
# Ishlatish:  .\tools\deploy.ps1            -> hammasini yuklab, ishga tushiradi
#             .\tools\deploy.ps1 -NoRun     -> faqat yuklaydi
#             .\tools\deploy.ps1 -Wipe      -> avval platani tozalaydi

param(
    [switch]$NoRun,
    [switch]$Wipe
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command mpremote -ErrorAction SilentlyContinue)) {
    Write-Error "mpremote topilmadi. O'rnating:  pip install mpremote"
}

if (-not (Test-Path (Join-Path $root "secrets.py"))) {
    Write-Warning "secrets.py yo'q! secrets.py.example dan nusxa oling."
}

Write-Host "Plata qidirilmoqda..." -ForegroundColor Cyan
mpremote devs

if ($Wipe) {
    Write-Host "Flash tozalanmoqda..." -ForegroundColor Yellow
    mpremote exec "import os
for f in os.listdir('/'):
    try: os.remove('/'+f)
    except OSError: pass"
}

Write-Host "Papkalar yaratilmoqda..." -ForegroundColor Cyan
mpremote mkdir :lib 2>$null

$files = @("boot.py", "main.py", "config.py", "secrets.py")
foreach ($f in $files) {
    $p = Join-Path $root $f
    if (Test-Path $p) {
        Write-Host "  -> $f"
        mpremote cp $p ":$f"
    }
}

Get-ChildItem (Join-Path $root "lib") -Filter *.py | ForEach-Object {
    Write-Host "  -> lib/$($_.Name)"
    mpremote cp $_.FullName ":lib/$($_.Name)"
}

Write-Host "Yuklandi." -ForegroundColor Green

if (-not $NoRun) {
    Write-Host "Qayta yuklanmoqda — chiqishni ko'rish uchun Ctrl-C bosing" -ForegroundColor Cyan
    mpremote reset
    Start-Sleep -Milliseconds 500
    mpremote repl
}
