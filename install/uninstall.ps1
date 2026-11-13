<#
.SYNOPSIS
    SRV_1 yorliqlarini olib tashlaydi va xizmat holatini ko'rsatadi.

.DESCRIPTION
    Ma'lumotlar papkasiga, Python muhitiga va tools\ ga TEGMAYDI - ularni o'zingiz
    o'chirasiz (yo'llari oxirida chiqadi). Xizmat o'rnatilgan bo'lsa, avval
    administrator oynasida: install\service.ps1 -Action remove
#>
[CmdletBinding()]
param(
    [string[]]$ShortcutDir = @(),
    [string]$Name = 'SRV_1'
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')

$folders = $ShortcutDir
if ($folders.Count -eq 0) {
    $folders = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))
}
Write-Step "Yorliqlar"
foreach ($folder in $folders) {
    $link = Join-Path $folder 'SRV_1.lnk'
    if (Test-Path -LiteralPath $link -PathType Leaf) {
        Remove-Item -LiteralPath $link -Force
        Write-Note "o'chirildi: $link"
    }
}

Write-Step "Xizmat"
if ($null -ne (Get-Service -Name $Name -ErrorAction SilentlyContinue)) {
    Write-Problem "$Name xizmati hali o'rnatilgan. Administrator oynasida:"
    Write-Note "install\service.ps1 -Action remove"
}
else {
    Write-Note "o'rnatilmagan"
}

Write-Step "Qo'lda o'chiriladi (xohlasangiz)"
Write-Note "ma'lumotlar (token, bazalar, loyihalar, zaxiralar): $(Get-DefaultDataDir)"
Write-Note "Python muhiti: $(Join-Path (Get-RepoRoot) '.venv')"
Write-Note "shell sozlamasi: $(Join-Path $env:APPDATA 'SRV_1')"
