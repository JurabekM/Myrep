<#
.SYNOPSIS
  AI Business Advisor - bitta buyruq bilan ishga tushirish.

.DESCRIPTION
  Docker mavjudligini tekshiradi, .env faylni avtomatik yaratadi (SECRET_KEY
  generatsiya qilinadi, AI kalitini so'raydi) va butun stackni ko'taradi.

.EXAMPLE
  .\run.ps1            # ishga tushirish (build + up)
  .\run.ps1 -Stop      # to'xtatish
  .\run.ps1 -Logs      # loglarni ko'rish
  .\run.ps1 -Status    # servislar holati
#>
param(
    [switch]$Stop,
    [switch]$Logs,
    [switch]$Status
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "  OK $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "  !! $msg" -ForegroundColor Yellow }

# ---------------------------------------------------------- Docker tekshiruvi
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Host ""
    Write-Host "Docker o'rnatilmagan!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Loyiha MongoDB, Redis, Qdrant va RabbitMQ servislariga muhtoj -"
    Write-Host "ularni alohida o'rnatish o'rniga Docker Desktop yetarli:"
    Write-Host ""
    Write-Host "  1-usul (tavsiya):  winget install Docker.DockerDesktop" -ForegroundColor White
    Write-Host "  2-usul:            https://www.docker.com/products/docker-desktop/" -ForegroundColor White
    Write-Host ""
    Write-Host "O'rnatgach kompyuterni qayta yoqing, Docker Desktop'ni oching"
    Write-Host "va bu skriptni qayta ishga tushiring: .\run.ps1"
    exit 1
}

# Docker engine ishlayaptimi?
docker info 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Docker o'rnatilgan, ammo ishlamayapti." -ForegroundColor Red
    Write-Host "Docker Desktop ilovasini oching va u to'liq yuklangach qayta urinib ko'ring."
    $dockerDesktop = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktop) {
        Write-Step "Docker Desktop ishga tushirilmoqda..."
        Start-Process $dockerDesktop
        Write-Host "1-2 daqiqa kutib, skriptni qayta ishga tushiring: .\run.ps1"
    }
    exit 1
}
Write-Ok "Docker ishlamoqda"

# ------------------------------------------------------------- Boshqaruv rejimlari
if ($Stop) {
    Write-Step "Servislar to'xtatilmoqda..."
    docker compose down
    exit $LASTEXITCODE
}
if ($Logs) {
    docker compose logs -f --tail 100
    exit 0
}
if ($Status) {
    docker compose ps
    exit 0
}

# ------------------------------------------------------------------ .env yaratish
if (-not (Test-Path ".env")) {
    Write-Step ".env fayli yaratilmoqda..."
    Copy-Item ".env.example" ".env"

    # Xavfsiz SECRET_KEY generatsiyasi (64 belgi)
    $bytes = New-Object byte[] 48
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $secret = [Convert]::ToBase64String($bytes) -replace '[/+=]', 'x'
    (Get-Content ".env") -replace '^SECRET_KEY=.*', "SECRET_KEY=$secret" |
        Set-Content ".env" -Encoding utf8
    Write-Ok "SECRET_KEY generatsiya qilindi"

    # AI kalitini so'rash
    Write-Host ""
    Write-Host "AI ishlashi uchun kamida bitta API kaliti kerak." -ForegroundColor White
    Write-Host "OpenAI kalitini kiriting (https://platform.openai.com/api-keys)"
    Write-Host "yoki bo'sh qoldirib keyin .env fayliga o'zingiz yozing:"
    $openaiKey = Read-Host "OPENAI_API_KEY"
    if ($openaiKey) {
        (Get-Content ".env") -replace '^OPENAI_API_KEY=.*', "OPENAI_API_KEY=$openaiKey" |
            Set-Content ".env" -Encoding utf8
        Write-Ok "OpenAI kaliti saqlandi"
    } else {
        Write-Warn2 "AI kaliti kiritilmadi - chat/AI funksiyalari kalit kiritilguncha ishlamaydi."
        Write-Warn2 "Keyin .env faylini ochib OPENAI_API_KEY= qatorini to'ldiring."
    }
} else {
    Write-Ok ".env fayli mavjud"
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match '(?m)^OPENAI_API_KEY=\s*$' -and
        $envContent -match '(?m)^ANTHROPIC_API_KEY=\s*$') {
        Write-Warn2 "Hech bir AI API kaliti kiritilmagan - .env faylini tekshiring."
    }
}

# ---------------------------------------------------------------- Ishga tushirish
Write-Step "Stack qurilmoqda va ishga tushirilmoqda (birinchi marta 5-10 daqiqa)..."
docker compose up --build -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "Xatolik! Loglarni ko'ring: .\run.ps1 -Logs" -ForegroundColor Red
    exit 1
}

Write-Step "Backend tayyor bo'lishi kutilmoqda..."
$ready = $false
foreach ($i in 1..60) {
    Start-Sleep -Seconds 3
    try {
        $res = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3
        if ($res.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
}

Write-Host ""
if ($ready) {
    Write-Host "================ TAYYOR! ================" -ForegroundColor Green
} else {
    Write-Warn2 "Backend hali javob bermayapti (birinchi build uzoq davom etishi mumkin)."
    Write-Warn2 "Holatni tekshiring: .\run.ps1 -Status  |  Loglar: .\run.ps1 -Logs"
}
Write-Host ""
Write-Host "  Ilova (frontend):   http://localhost:3000"
Write-Host "  API hujjati:        http://localhost:8000/docs"
Write-Host "  Grafana monitoring: http://localhost:3001  (admin/admin)"
Write-Host "  RabbitMQ:           http://localhost:15672 (guest/guest)"
Write-Host ""
Write-Host "  To'xtatish:  .\run.ps1 -Stop"
Write-Host "  Loglar:      .\run.ps1 -Logs"
Write-Host ""
