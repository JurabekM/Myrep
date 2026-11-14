<#
.SYNOPSIS
    SRV_1 o'rnatuvchisini o'zi imzolangan (self-signed) sertifikat bilan imzolaydi.

.DESCRIPTION
    Sertifikat (kod imzosi, RSA 3072, SHA-256) joriy foydalanuvchining shaxsiy omborida
    (Cert:\CurrentUser\My) saqlanadi; yo'q bo'lsa yaratiladi. Yopiq kalit eksport qilinmaydigan
    qilib yaratiladi va hech qachon faylga yoki gitga tushmaydi.
    Ochiq qismi (.cer) o'rnatuvchi yoniga yoziladi. Boshqa kompyuterda Windows noshirni tanishi
    uchun shu .cer ni o'sha kompyuterga o'rnatish kerak (docs\reliz.md); o'rnatilmasa Windows
    "noma'lum noshir" deb ogohlantiradi, lekin imzo fayl o'zgarmaganini baribir ko'rsatadi.
    Vaqt tamg'asi qo'yilmaydi (tashqi serverga so'rov yuborilmaydi): imzo sertifikat muddati
    tugaguncha amal qiladi.
    Imzodan keyin fayl o'zgaradi, shuning uchun yonidagi .sha256 qayta yoziladi.
    Faqat ASCII (PowerShell 5.1 BOM'siz UTF-8 ni noto'g'ri o'qiydi).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File packaging\sign.ps1
    powershell -ExecutionPolicy Bypass -File packaging\sign.ps1 -File release\SRV_1-Setup-1.1.0.exe
#>
[CmdletBinding()]
param(
    [string]$File = '',
    [string]$Subject = 'CN=SRV_1 Release (self-signed)',
    [int]$Years = 5,
    [string]$CertificateOut = ''
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot

function Write-Step([string]$Text) { Write-Host "==> $Text" -ForegroundColor Cyan }
function Write-Note([string]$Text) { Write-Host "    $Text" }
function Stop-Sign([string]$Text) { Write-Host "!!  $Text" -ForegroundColor Yellow; exit 1 }

if (-not $File) {
    $line = Select-String -LiteralPath (Join-Path $Repo 'pyproject.toml') -Pattern '^version\s*=\s*"([^"]+)"' |
        Select-Object -First 1
    if ($null -eq $line) { Stop-Sign "pyproject.toml da versiya topilmadi" }
    $File = Join-Path $Repo ("release\SRV_1-Setup-{0}.exe" -f $line.Matches[0].Groups[1].Value)
}
if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { Stop-Sign "fayl topilmadi: $File" }
$File = (Resolve-Path -LiteralPath $File).Path
if (-not $CertificateOut) { $CertificateOut = Join-Path (Split-Path -Parent $File) 'SRV_1-codesign.cer' }

Write-Step "Sertifikat: $Subject"
$certificate = Get-ChildItem -Path Cert:\CurrentUser\My -CodeSigningCert |
    Where-Object { $_.Subject -eq $Subject -and $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date).AddDays(30) } |
    Sort-Object NotAfter -Descending | Select-Object -First 1
if ($null -eq $certificate) {
    $certificate = New-SelfSignedCertificate -Type CodeSigningCert -Subject $Subject `
        -KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 -KeyUsage DigitalSignature `
        -KeyExportPolicy NonExportable -CertStoreLocation Cert:\CurrentUser\My `
        -NotAfter (Get-Date).AddYears($Years)
    Write-Note "yangi sertifikat yaratildi (Cert:\CurrentUser\My)"
}
else { Write-Note "mavjud sertifikat ishlatiladi" }
Write-Note "barmoq izi: $($certificate.Thumbprint)"
Write-Note ("amal qiladi: {0:yyyy-MM-dd} gacha" -f $certificate.NotAfter)

Write-Step "Imzolash: $File"
$signature = Set-AuthenticodeSignature -FilePath $File -Certificate $certificate -HashAlgorithm SHA256
# O'zi imzolangan sertifikat ishonchli ildizlarda yo'q: holat 'UnknownError' (zanjir ishonchsiz)
# bo'ladi - bu kutilgan. 'HashMismatch' yoki 'NotSigned' esa xato.
$check = Get-AuthenticodeSignature -FilePath $File
if ($null -eq $check.SignerCertificate -or $check.SignerCertificate.Thumbprint -ne $certificate.Thumbprint) {
    Stop-Sign "imzo qo'yilmadi (holat: $($signature.Status))"
}
if ($check.Status -notin @('Valid', 'UnknownError')) { Stop-Sign "imzo yaroqsiz (holat: $($check.Status))" }
Write-Note "imzo holati: $($check.Status)"
if ($check.Status -ne 'Valid') {
    Write-Note "(sertifikat bu kompyuterda ishonchli deb o'rnatilmagan - o'zi imzolangan uchun kutilgan holat)"
}

Export-Certificate -Cert $certificate -FilePath $CertificateOut -Type CERT | Out-Null
$hash = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLower()
Set-Content -LiteralPath "$File.sha256" -Encoding ASCII -Value "$hash  $([IO.Path]::GetFileName($File))"

Write-Step "Tayyor"
Write-Note "imzolangan fayl: $File"
Write-Note "SHA-256: $hash"
Write-Note "ochiq sertifikat: $CertificateOut"
