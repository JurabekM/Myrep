<#
.SYNOPSIS
    SRV_1 ni shu mashinaga o'rnatadi: Python muhiti, ma'lumotlar papkasi, shell yorlig'i.

.DESCRIPTION
    Administrator huquqi kerak emas. Qadamlar:
      1. uv borligini tekshiradi va Python muhitini tayyorlaydi (uv sync).
      2. tools\ dagi tashqi dasturlarni tekshiradi (yuklab olmaydi - tools\README.md).
      3. Ma'lumotlar papkasini yaratadi va uni faqat sizga, SYSTEM va administratorlarga ochadi.
      4. Ish stoli va Bosh menyuga "SRV_1" yorlig'ini qo'yadi.
    Windows xizmati alohida: install\service.ps1 -Action install (administrator oynasida).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install\install.ps1
#>
[CmdletBinding()]
param(
    [string]$DataDir = '',
    # Yorliqlar qo'yiladigan papkalar; bo'sh bo'lsa Ish stoli va Bosh menyu.
    [string[]]$ShortcutDir = @(),
    [switch]$NoShortcut,
    # Ishlab chiquvchi bog'liqliklarini (pytest, ruff, pyright) ham o'rnatadi.
    [switch]$Dev,
    [switch]$SkipSync
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')

$Repo = Get-RepoRoot
$customData = [bool]$DataDir
if (-not $DataDir) { $DataDir = Get-DefaultDataDir }
$DataDir = [IO.Path]::GetFullPath($DataDir)

function Install-Environment {
    Write-Step "Python muhiti"
    if ($SkipSync) { Write-Note "o'tkazib yuborildi (-SkipSync)"; return }
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -eq $uv) {
        Write-Problem "uv topilmadi. O'rnating: https://docs.astral.sh/uv/ (yoki: winget install astral-sh.uv)"
        exit 1
    }
    $free = [math]::Round((Get-PSDrive ($Repo.Substring(0, 1))).Free / 1GB, 1)
    if ($free -lt 2) { Write-Problem "Diskda atigi $free GB bo'sh joy bor; muhitga taxminan 0,6 GB kerak." }
    $arguments = @('sync', '--project', $Repo)
    if (-not $Dev) { $arguments += '--no-dev' }
    & $uv.Source @arguments
    if ($LASTEXITCODE -ne 0) { Write-Problem "uv sync xato bilan tugadi."; exit 1 }
}

function Show-Tools {
    Write-Step "Tashqi dasturlar (tools\)"
    $tools = @(
        @('caddy.exe', 'hosting: saytlar (majburiy)'),
        @('cloudflared.exe', 'hosting: internetga ochish'),
        @('nssm.exe', 'Windows xizmati'),
        @('avrdude\avrdude.exe', 'electronics: Arduino proshivkasi'),
        @('mosquitto\mosquitto.exe', 'iot: MQTT broker')
    )
    foreach ($tool in $tools) {
        $mark = 'yo''q'
        if (Test-Path -LiteralPath (Get-ToolPath $tool[0]) -PathType Leaf) { $mark = 'bor ' }
        Write-Note ("[{0}] {1,-26} {2}" -f $mark, $tool[0], $tool[1])
    }
    Write-Note "Yo'qlarini qayerdan olish va qanday tekshirish: tools\README.md"
}

function Protect-DataDir {
    # Meros ruxsatlar uziladi: ProgramData ichidagi papkani odatda hamma o'qiy oladi,
    # bu yerda esa token, bazalar va loyihalar turadi. SID'lar - Windows tiliga bog'liq emas.
    $me = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $grants = @("*${me}:(OI)(CI)F", '*S-1-5-18:(OI)(CI)F', '*S-1-5-32-544:(OI)(CI)F')
    & icacls.exe $DataDir /inheritance:r /grant:r @grants | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Problem "Ruxsatlarni cheklab bo'lmadi (icacls kodi $LASTEXITCODE)." }
}

function Install-DataDir {
    Write-Step "Ma'lumotlar papkasi: $DataDir"
    $created = -not (Test-Path -LiteralPath $DataDir)
    foreach ($sub in @('', 'logs', 'projects', 'plugins')) {
        New-Item -ItemType Directory -Force -Path (Join-Path $DataDir $sub) | Out-Null
    }
    if ($created) {
        Protect-DataDir
        Write-Note "yaratildi; faqat siz, SYSTEM va administratorlar kira oladi"
    }
    else {
        Write-Note "allaqachon bor - ichidagilar va ruxsatlariga tegilmadi"
    }
    if ($customData) {
        Write-Problem "Standart bo'lmagan papka. Yadro va shell uni SRV1_DATA_DIR orqali topadi:"
        Write-Note "[Environment]::SetEnvironmentVariable('SRV1_DATA_DIR', '$DataDir', 'User')"
    }
}

function Install-Shortcuts {
    Write-Step "Yorliqlar"
    if ($NoShortcut) { Write-Note "o'tkazib yuborildi (-NoShortcut)"; return }
    $folders = $ShortcutDir
    if ($folders.Count -eq 0) {
        $folders = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))
    }
    $shell = New-Object -ComObject WScript.Shell
    foreach ($folder in $folders) {
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
        $link = $shell.CreateShortcut((Join-Path $folder 'SRV_1.lnk'))
        $link.TargetPath = Get-VenvPython -Windowless
        $link.Arguments = '-m srv1_shell'
        $link.WorkingDirectory = $Repo
        $link.IconLocation = (Join-Path $Repo 'shell\srv1_shell\srv1.ico')
        $link.Description = 'SRV_1 boshqaruv oynasi'
        $link.Save()
        Write-Note (Join-Path $folder 'SRV_1.lnk')
    }
}

Install-Environment
Show-Tools
Install-DataDir
Install-Shortcuts

Write-Step "Tayyor. Keyingi qadam - yadroni ishga tushirish:"
Write-Note "sinab ko'rish:  uv run python -m srv1_core   (oyna yopilsa, yadro to'xtaydi)"
Write-Note "doimiy xizmat:  install\service.ps1 -Action install   (administrator oynasida)"
Write-Note "So'ng 'SRV_1' yorlig'ini oching. Qo'llanma: docs\qollanma.md"
