# Google Play upload kalitini yaratish (docs/RELEASE_CHECKLIST.md, 2-bo'lim).
#
#   powershell -ExecutionPolicy Bypass -File tools/create_upload_key.ps1
#   powershell -ExecutionPolicy Bypass -File tools/create_upload_key.ps1 -Dir D:\keys\baraka
#
# Skriptni FAQAT o'zingiz, o'z terminalingizda ishga tushiring: parol shu yerda
# so'raladi va hech qayerga (chat, repo, log) yuborilmaydi.
#
# - Kalit: PKCS12, RSA 4096, 10000 kun (~27 yil; Play kalit 2033-10-22 dan
#   keyin tugashini talab qiladi). Kalit va ombor paroli bitta (PKCS12 talabi).
# - Natija <Dir> ichida: upload.jks (kalit), key.properties (Gradle uchun; parol
#   ochiq matnda - papka repodan tashqarida bo'lishi shart) va
#   upload-cert-sha256.txt (sertifikat xeshi - maxfiy emas).
# - Mavjud kalit ustidan hech qachon yozilmaydi.
#
# DIQQAT: bu fayl faqat ASCII bo'lsin - Windows PowerShell 5.1 BOM'siz UTF-8'ni
# ANSI deb o'qiydi.
param(
    [string]$Dir = "C:\keys\baraka",
    [string]$Alias = "baraka",
    [string]$DName = "CN=JurabekM, C=UZ"
)
$ErrorActionPreference = "Stop"

$keytool = $null
foreach ($jdk in @($env:JAVA_HOME, "C:\Program Files\Android\Android Studio\jbr")) {
    if ($jdk -and (Test-Path (Join-Path $jdk "bin\keytool.exe"))) {
        $keytool = Join-Path $jdk "bin\keytool.exe"
        break
    }
}
if (-not $keytool) { throw "keytool topilmadi: JAVA_HOME ni JDK 21 ga (Android Studio jbr) yo'naltiring." }

$repo = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$full = [IO.Path]::GetFullPath($Dir)
if ($full.StartsWith($repo, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Kalit papkasi repodan TASHQARIDA bo'lsin: $full"
}
if ($full -match "OneDrive|Dropbox|Google Drive") {
    throw "Kalitni sinxronlanadigan papkaga qo'ymang: $full. Zaxirani qo'lda, shifrlangan joyga oling."
}
$jks = Join-Path $full "upload.jks"
$props = Join-Path $full "key.properties"
$shaFile = Join-Path $full "upload-cert-sha256.txt"
if ((Test-Path $jks) -or (Test-Path $props)) {
    throw "Kalit allaqachon bor: $full. Uni O'CHIRMANG va ustidan yozmang - eski kalit bilan imzolangan ilovani faqat shu kalit yangilay oladi."
}

function Read-Secret([string]$Prompt) {
    $secure = Read-Host -AsSecureString $Prompt
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

Write-Host "Parol: kamida 12 belgi, faqat lotin harflari, raqamlar va belgilar (bo'sh joysiz)."
Write-Host "Parolni parol menejeriga yoki qog'ozga yozib, xavfsiz joyda saqlang."
$pass = Read-Secret "Kalit paroli"
# key.properties Java tomonidan ISO-8859-1 sifatida o'qiladi: faqat ko'rinadigan ASCII.
if ($pass.Length -lt 12 -or $pass -notmatch '^[\x21-\x7E]+$') {
    throw "Parol kamida 12 belgi va faqat ASCII (lotin harfi, raqam, belgi; bo'sh joysiz) bo'lsin."
}
if ((Read-Secret "Parolni qayta kiriting") -ne $pass) { throw "Parollar mos kelmadi." }

New-Item -ItemType Directory -Force $full | Out-Null
$env:BARAKA_UPLOAD_KEY_PASS = $pass
# keytool oddiy xabarlarini stderr'ga yozadi: PowerShell 5.1 ularni xato deb
# to'xtamasin - natija faqat chiqish kodi bilan tekshiriladi.
$ErrorActionPreference = "Continue"
try {
    & $keytool -genkeypair -v -keystore $jks -storetype PKCS12 -alias $Alias `
        -keyalg RSA -keysize 4096 -validity 10000 -dname $DName `
        -storepass:env BARAKA_UPLOAD_KEY_PASS -keypass:env BARAKA_UPLOAD_KEY_PASS 2>&1 |
        ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) { throw "keytool -genkeypair yiqildi ($LASTEXITCODE)" }
    $list = & $keytool -list -v -keystore $jks -alias $Alias -storepass:env BARAKA_UPLOAD_KEY_PASS 2>&1 |
        ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) { throw "keytool -list yiqildi ($LASTEXITCODE)" }
} finally {
    Remove-Item Env:BARAKA_UPLOAD_KEY_PASS -ErrorAction SilentlyContinue
    $ErrorActionPreference = "Stop"
}

$sha = ($list | Select-String 'SHA256:\s*([0-9A-Fa-f:]+)').Matches[0].Groups[1].Value
if (-not $sha) { throw "Sertifikat SHA-256 xeshi o'qilmadi." }

# Java .properties: teskari chiziq ekranlanadi; yo'l - to'g'ri chiziq bilan.
$escaped = $pass.Replace('\', '\\')
$lines = @(
    "storeFile=$($jks.Replace('\', '/'))",
    "storePassword=$escaped",
    "keyAlias=$Alias",
    "keyPassword=$escaped"
)
[IO.File]::WriteAllText($props, (($lines -join "`n") + "`n"), [Text.Encoding]::ASCII)
[IO.File]::WriteAllText($shaFile, "$sha`n", [Text.Encoding]::ASCII)
$pass = $null; $escaped = $null; $lines = $null

Write-Host ""
Write-Host "Tayyor:"
Write-Host "  kalit           $jks"
Write-Host "  key.properties  $props"
Write-Host "  SHA-256         $sha"
Write-Host ""
Write-Host "Keyingi qadamlar:"
Write-Host "  1) $full papkasini IKKI joyga zaxiralang (masalan, shifrlangan USB va boshqa disk)."
Write-Host "     Parolni alohida saqlang. Kalit yo'qolsa, to'g'ridan-to'g'ri tarqatilgan ilovani yangilab bo'lmaydi."
Write-Host "  2) Reliz yig'ish:"
Write-Host "     powershell -ExecutionPolicy Bypass -File tools/build_release.ps1 -SigningProperties `"$props`" -ExpectedSignatureSha256 $sha"
