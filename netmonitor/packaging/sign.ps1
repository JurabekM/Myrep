<#
.SYNOPSIS
    NetMonitor.exe ni o'zi imzolangan (self-signed) sertifikat bilan imzolaydi (Authenticode, SHA-256).

.DESCRIPTION
    Ikki rejim:

    - odatiy: sertifikat joriy foydalanuvchining shaxsiy omborida (Cert:\CurrentUser\My) saqlanadi;
      yo'q bo'lsa yaratiladi, keyingi safar o'shasi ishlatiladi (srv1\packaging\sign.ps1 kabi);
    - -Ephemeral (CI uchun): har yig'ishda yangi sertifikat yaratiladi va imzodan keyin yopiq
      kaliti bilan birga o'chiriladi. Bu kalit bilan boshqa hech narsa imzolanmaydi.

    Yopiq kalit eksport qilinmaydigan qilib yaratiladi va hech qachon faylga yoki gitga tushmaydi.
    Ochiq qismi (.cer) exe yoniga yoziladi. Sertifikatni hech qaysi sertifikatlash markazi
    tasdiqlamagan: .cer o'rnatilmagan kompyuterda Windows "noma'lum noshir" deb ogohlantiradi,
    lekin imzo fayl o'zgarmaganini baribir ko'rsatadi.
    Vaqt tamg'asi qo'yilmaydi (tashqi serverga so'rov yo'q): imzo sertifikat muddati tugaguncha amal qiladi.
    Imzodan keyin fayl o'zgaradi, shuning uchun yonidagi .sha256 qayta yoziladi.
    Faqat ASCII (PowerShell 5.1 BOM'siz UTF-8 ni noto'g'ri o'qiydi).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\sign.ps1
    powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 -Ephemeral
#>
[CmdletBinding()]
param(
    [string]$File = '',
    [string]$Subject = 'CN=NetMonitor Release (self-signed)',
    [int]$Years = 5,
    [string]$CertificateOut = '',
    [switch]$Ephemeral
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

function Write-Step([string]$Text) { Write-Host "==> $Text" -ForegroundColor Cyan }
function Write-Note([string]$Text) { Write-Host "    $Text" }
function Stop-Sign([string]$Text) { Write-Host "!!  $Text" -ForegroundColor Yellow; exit 1 }

if (-not $File) { $File = Join-Path $Root 'release\NetMonitor.exe' }
if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { Stop-Sign "fayl topilmadi: $File (avval packaging\build.ps1)" }
$File = (Resolve-Path -LiteralPath $File).Path
if (-not $CertificateOut) { $CertificateOut = Join-Path (Split-Path -Parent $File) 'NetMonitor-codesign.cer' }

Write-Step "Sertifikat: $Subject"
$certificate = $null
if (-not $Ephemeral) {
    $certificate = Get-ChildItem -Path Cert:\CurrentUser\My -CodeSigningCert |
        Where-Object { $_.Subject -eq $Subject -and $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date).AddDays(30) } |
        Sort-Object NotAfter -Descending | Select-Object -First 1
}
if ($null -eq $certificate) {
    $certificate = New-SelfSignedCertificate -Type CodeSigningCert -Subject $Subject `
        -KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 -KeyUsage DigitalSignature `
        -KeyExportPolicy NonExportable -CertStoreLocation Cert:\CurrentUser\My `
        -NotAfter (Get-Date).AddYears($Years)
    Write-Note 'yangi sertifikat yaratildi (Cert:\CurrentUser\My)'
}
else { Write-Note 'mavjud sertifikat ishlatiladi' }
$thumbprint = $certificate.Thumbprint
Write-Note "barmoq izi (SHA-1): $thumbprint"
Write-Note ("amal qiladi: {0:yyyy-MM-dd} gacha" -f $certificate.NotAfter)

try {
    Write-Step "Imzolash: $File"
    $signature = Set-AuthenticodeSignature -FilePath $File -Certificate $certificate -HashAlgorithm SHA256
    # O'zi imzolangan sertifikat ishonchli ildizlarda yo'q: holat 'UnknownError' (zanjir ishonchsiz)
    # bo'ladi - bu kutilgan. 'HashMismatch' yoki 'NotSigned' esa xato.
    $check = Get-AuthenticodeSignature -FilePath $File
    if ($null -eq $check.SignerCertificate -or $check.SignerCertificate.Thumbprint -ne $thumbprint) {
        Stop-Sign "imzo qo'yilmadi (holat: $($signature.Status))"
    }
    if ($check.Status -notin @('Valid', 'UnknownError')) { Stop-Sign "imzo yaroqsiz (holat: $($check.Status))" }
    Write-Note "imzo holati: $($check.Status)"
    if ($check.Status -ne 'Valid') {
        Write-Note "(sertifikat bu kompyuterda ishonchli deb o'rnatilmagan - o'zi imzolangan uchun kutilgan holat)"
    }
    Export-Certificate -Cert $certificate -FilePath $CertificateOut -Type CERT | Out-Null
}
finally {
    if ($Ephemeral) {
        # Bir martalik kalit: imzodan keyin yopiq kalit bilan birga yo'q qilinadi.
        Remove-Item -LiteralPath "Cert:\CurrentUser\My\$thumbprint" -DeleteKey -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath "Cert:\CurrentUser\My\$thumbprint") { Stop-Sign "bir martalik sertifikat o'chirilmadi" }
        Write-Note "bir martalik sertifikat va yopiq kaliti o'chirildi"
    }
}

$hash = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLower()
Set-Content -LiteralPath "$File.sha256" -Encoding ASCII -Value "$hash  $([IO.Path]::GetFileName($File))"

Write-Step 'Tayyor'
Write-Note "imzolangan fayl: $File"
Write-Note "SHA-256: $hash"
Write-Note "ochiq sertifikat: $CertificateOut"
if ($env:GITHUB_OUTPUT) {
    Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "sha256=$hash"
    Add-Content -LiteralPath $env:GITHUB_OUTPUT -Value "thumbprint=$thumbprint"
}
