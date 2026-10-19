<#
.SYNOPSIS
  Bitta faylni Authenticode bilan imzolaydi. Tauri `signCommand` uni har bir binar, sidecar,
  o'chiruvchi va o'rnatuvchi uchun chaqiradi (scripts/build-installer.ps1 ulaydi).

.DESCRIPTION
  Sertifikat muhit o'zgaruvchilaridan olinadi (biri yetarli):

    TAMGA_SIGN_THUMBPRINT   sertifikat Windows omborida (CurrentUser\My yoki LocalMachine\My),
                            jumladan USB token / HSM (EV va OV sertifikatlar shunday keladi)
    TAMGA_SIGN_PFX          .pfx fayl yo'li; parol TAMGA_SIGN_PFX_PASSWORD da
    TAMGA_SIGN_AZURE_DLIB   Azure Trusted Signing: Azure.CodeSigning.Dlib.dll yo'li
    TAMGA_SIGN_AZURE_METADATA  va uning metadata.json fayli

  TAMGA_SIGN_TIMESTAMP   RFC 3161 vaqt tamg'asi serveri (standart: http://timestamp.digicert.com;
                         "none" - tamg'asiz, faqat sinov uchun). Tamg'a sertifikat muddati
                         tugagandan keyin ham imzoni haqiqiy qoldiradi.
  TAMGA_SIGN_REQUIRED=1  sertifikat sozlanmagan bo'lsa xato bilan to'xtaydi (reliz uchun).

  Hech narsa sozlanmagan bo'lsa fayl imzosiz qoladi va ogohlantirish chiqadi (dev build).
#>
param([Parameter(Mandatory = $true)][string]$File)
$ErrorActionPreference = "Stop"

function Find-SignTool {
    $c = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    $kits = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    $found = Get-ChildItem $kits -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
        Where-Object FullName -match '\\x64\\' | Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $found) { throw "signtool.exe topilmadi (Windows SDK kerak)" }
    $found.FullName
}

$args_ = @()
if ($env:TAMGA_SIGN_THUMBPRINT) {
    $args_ = @("/sha1", $env:TAMGA_SIGN_THUMBPRINT)
} elseif ($env:TAMGA_SIGN_PFX) {
    $args_ = @("/f", $env:TAMGA_SIGN_PFX)
    if ($env:TAMGA_SIGN_PFX_PASSWORD) { $args_ += @("/p", $env:TAMGA_SIGN_PFX_PASSWORD) }
} elseif ($env:TAMGA_SIGN_AZURE_DLIB -and $env:TAMGA_SIGN_AZURE_METADATA) {
    $args_ = @("/dlib", $env:TAMGA_SIGN_AZURE_DLIB, "/dmdf", $env:TAMGA_SIGN_AZURE_METADATA)
} else {
    if ($env:TAMGA_SIGN_REQUIRED -eq "1") { throw "imzo talab qilingan, lekin sertifikat sozlanmagan (TAMGA_SIGN_*)" }
    Write-Host "  [imzosiz] $File  (TAMGA_SIGN_* sozlanmagan)" -ForegroundColor Yellow
    exit 0
}

$ts = $env:TAMGA_SIGN_TIMESTAMP
if (-not $ts) { $ts = "http://timestamp.digicert.com" }
$tsArgs = @()
if ($ts -ne "none") { $tsArgs = @("/tr", $ts, "/td", "sha256") }

$signtool = Find-SignTool
# /fd sha256 - fayl xeshi; /d - Windows UAC va SmartScreen oynasida ko'rinadigan nom.
& $signtool sign /fd sha256 /d "TAMGA Studio" /du "https://github.com/JurabekM/Myrep" @args_ @tsArgs $File | Out-Null
if ($LASTEXITCODE -ne 0) {
    # Vaqt tamg'asi serveri vaqtincha javob bermasligi mumkin: bir marta qayta urinamiz.
    Start-Sleep -Seconds 3
    & $signtool sign /fd sha256 /d "TAMGA Studio" /du "https://github.com/JurabekM/Myrep" @args_ @tsArgs $File
    if ($LASTEXITCODE -ne 0) { throw "signtool xatosi ($LASTEXITCODE): $File" }
}
Write-Host "  [imzolandi] $File" -ForegroundColor Green
