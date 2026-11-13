<#
.SYNOPSIS
    SRV_1 yadrosini Windows xizmati sifatida boshqaradi (NSSM orqali).

.DESCRIPTION
    install / remove / start / stop / restart - administrator PowerShell oynasida.
    status va plan - oddiy foydalanuvchi bilan ham ishlaydi.
    plan hech narsani o'zgartirmaydi: install bajaradigan NSSM buyruqlarini chiqaradi.

    Xizmat SIZNING foydalanuvchingiz nomidan ishlaydi (install parolni so'raydi):
    shunda token fayli, COM portlar va loyiha fayllari shell bilan bir xil egada bo'ladi.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install\service.ps1 -Action plan
    powershell -ExecutionPolicy Bypass -File install\service.ps1 -Action install
#>
[CmdletBinding()]
param(
    [ValidateSet('install', 'remove', 'start', 'stop', 'restart', 'status', 'plan')]
    [string]$Action = 'status',
    [string]$Name = 'SRV_1',
    [string]$DataDir = '',
    [string]$Account = '',
    [string]$Nssm = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')

if (-not $DataDir) { $DataDir = Get-DefaultDataDir }
if (-not $Account) { $Account = "$env:USERDOMAIN\$env:USERNAME" }
if (-not $Nssm) { $Nssm = Get-ToolPath 'nssm.exe' }
$Python = Get-VenvPython
$LogFile = Join-Path $DataDir 'logs\service.log'

# Har element: NSSM argumentlari. Parol bu ro'yxatda yo'q - u alohida, so'ralgandan keyin.
function Get-ServicePlan {
    return @(
        , @('install', $Name, $Python, '-m', 'srv1_core')
        , @('set', $Name, 'DisplayName', 'SRV_1 yadro')
        , @('set', $Name, 'Description', 'SRV_1 modulli server yadrosi (127.0.0.1:8710).')
        , @('set', $Name, 'AppDirectory', (Get-RepoRoot))
        , @('set', $Name, 'AppEnvironmentExtra', "SRV1_DATA_DIR=$DataDir", 'PYTHONUNBUFFERED=1')
        # Kechiktirilgan avtostart: 4 GB mashinada Windows yuklanishiga xalaqit bermaydi.
        , @('set', $Name, 'Start', 'SERVICE_DELAYED_AUTO_START')
        , @('set', $Name, 'AppStdout', $LogFile)
        , @('set', $Name, 'AppStderr', $LogFile)
        , @('set', $Name, 'AppRotateFiles', '1')
        , @('set', $Name, 'AppRotateOnline', '1')
        , @('set', $Name, 'AppRotateBytes', '1048576')
        # Yiqilsa 5 soniyadan keyin qayta ishga tushadi; sozlama xatosida (kod 2) - yo'q.
        , @('set', $Name, 'AppExit', 'Default', 'Restart')
        , @('set', $Name, 'AppExit', '2', 'Exit')
        , @('set', $Name, 'AppRestartDelay', '5000')
        , @('set', $Name, 'AppThrottle', '10000')
        # To'xtatish: avval Ctrl+C (yadro plaginlar va loyihalarni o'zi yopadi), 20 s kutadi.
        # Yopilmasa NSSM butun jarayon daraxtini o'ldiradi. Bu NSSM 2.24 da doimiy xatti-harakat;
        # 'AppKillProcessTree' parametri faqat 2.25 sinov yig'ilishlarida bor, shuning uchun qo'yilmaydi.
        , @('set', $Name, 'AppStopMethodConsole', '20000')
    )
}

function Format-Arguments([string[]]$Arguments) {
    return (($Arguments | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ')
}

function Invoke-Nssm([string[]]$Arguments) {
    & $Nssm @Arguments
    if ($LASTEXITCODE -ne 0) { throw "nssm $($Arguments[0]) xato bilan tugadi (kod $LASTEXITCODE)" }
}

function Assert-Ready {
    # NSSM konsolsiz yoki huquqsiz chaqirilsa xabar oynasi ochadi - shuning uchun avval tekshiramiz.
    if (-not (Test-Admin)) {
        Write-Problem "Bu amal uchun administrator huquqi kerak."
        Write-Note "PowerShell'ni 'Administrator sifatida ishga tushirish' bilan oching va qayta yuguring."
        exit 1
    }
    if (-not (Test-Path -LiteralPath $Nssm -PathType Leaf)) {
        Write-Problem "nssm.exe topilmadi: $Nssm (tools\README.md ga qarang)"
        exit 1
    }
}

function Get-ServiceState {
    $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($null -eq $service) { return 'not-installed' }
    return $service.Status.ToString().ToLower()
}

switch ($Action) {
    'plan' {
        Write-Step "Xizmat: $Name (hisob: $Account)"
        foreach ($arguments in Get-ServicePlan) { Write-Host ('nssm ' + (Format-Arguments $arguments)) }
        Write-Host "nssm set $Name ObjectName $Account <parol so'raladi>"
        Write-Host "nssm start $Name"
    }
    'status' {
        Write-Host "$Name`: $(Get-ServiceState)"
    }
    'install' {
        Assert-Ready
        if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
            Write-Problem "Python muhiti yo'q: $Python. Avval install\install.ps1 ni yuguring."
            exit 1
        }
        if ((Get-ServiceState) -ne 'not-installed') {
            Write-Problem "$Name xizmati allaqachon o'rnatilgan. Avval: -Action remove"
            exit 1
        }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogFile) | Out-Null
        Write-Step "Xizmat $Account nomidan ishlaydi. Windows parolingizni kiriting."
        $credential = Get-Credential -UserName $Account -Message "SRV_1 xizmati uchun Windows paroli"
        if ($null -eq $credential) { Write-Problem "Bekor qilindi."; exit 1 }
        try {
            foreach ($arguments in Get-ServicePlan) { Invoke-Nssm $arguments }
        }
        catch {
            # Yarim sozlangan xizmat qolmasin: u LocalSystem nomidan va avtostart bilan qolardi.
            & $Nssm remove $Name confirm | Out-Null
            Write-Problem "Xizmatni sozlab bo'lmadi ($($_.Exception.Message)); xizmat olib tashlandi."
            exit 1
        }
        try {
            # NSSM hisobga 'xizmat sifatida kirish' huquqini ham beradi.
            Invoke-Nssm @('set', $Name, 'ObjectName', $credential.UserName,
                $credential.GetNetworkCredential().Password)
        }
        catch {
            & $Nssm remove $Name confirm | Out-Null
            Write-Problem "Hisob yoki parol qabul qilinmadi; xizmat olib tashlandi."
            exit 1
        }
        Invoke-Nssm @('start', $Name)
        Write-Step "Tayyor. Holat: $(Get-ServiceState). Jurnal: $LogFile"
    }
    'remove' {
        Assert-Ready
        if ((Get-ServiceState) -eq 'not-installed') { Write-Note "$Name o'rnatilmagan."; exit 0 }
        if ((Get-ServiceState) -ne 'stopped') { & $Nssm stop $Name | Out-Null }
        Invoke-Nssm @('remove', $Name, 'confirm')
        Write-Step "$Name xizmati olib tashlandi. Ma'lumotlar joyida: $DataDir"
    }
    default {
        Assert-Ready
        Invoke-Nssm @($Action, $Name)
        Write-Host "$Name`: $(Get-ServiceState)"
    }
}
