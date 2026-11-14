<#
.SYNOPSIS
    Ishlab turgan SRV_1 yadrosini (xizmat bo'lmagan) API orqali tartibli to'xtatadi.

.DESCRIPTION
    O'rnatuvchi yangilash va olib tashlashdan oldin chaqiradi: oynasiz ishlayotgan yadro
    dastur fayllarini band qilib turmasin. Yadro ishlamayotgan bo'lsa hech narsa qilmaydi.
    Chiqish kodi: 0 - yadro ishlamayapti yoki to'xtadi; 1 - hali ishlayapti (token yo'q,
    yadro eski yoki Windows xizmati sifatida ishlayapti).
    Mustaqil skript (common.ps1 kerak emas): o'rnatuvchi uni vaqtinchalik papkadan yuritadi.
    Faqat ASCII (PowerShell 5.1 BOM'siz UTF-8 ni noto'g'ri o'qiydi).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install\stop-core.ps1
#>
[CmdletBinding()]
param(
    [string]$DataDir = '',
    [int]$Port = 0,
    [int]$WaitSeconds = 45
)

$ErrorActionPreference = 'Stop'

if (-not $DataDir) {
    if ($env:SRV1_DATA_DIR) { $DataDir = $env:SRV1_DATA_DIR }
    else {
        $base = $env:PROGRAMDATA
        if (-not $base) { $base = 'C:\ProgramData' }
        $DataDir = Join-Path $base 'SRV_1'
    }
}

# Port: config.toml dagi [server] bo'limidan, bo'lmasa standart 8710.
function Get-CorePort {
    $config = Join-Path $DataDir 'config.toml'
    if (-not (Test-Path -LiteralPath $config -PathType Leaf)) { return 8710 }
    $section = ''
    foreach ($line in Get-Content -LiteralPath $config) {
        if ($line -match '^\s*\[([^\]]+)\]') { $section = $Matches[1].Trim(); continue }
        if ($section -eq 'server' -and $line -match '^\s*port\s*=\s*(\d+)') { return [int]$Matches[1] }
    }
    return 8710
}

function Test-Listening {
    $client = New-Object Net.Sockets.TcpClient
    try {
        $pending = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        return ($pending.AsyncWaitHandle.WaitOne(700) -and $client.Connected)
    }
    catch { return $false }
    finally { $client.Close() }
}

if ($Port -le 0) { $Port = Get-CorePort }
if (-not (Test-Listening)) { exit 0 }

$tokenFile = Join-Path $DataDir 'auth.token'
if (-not (Test-Path -LiteralPath $tokenFile -PathType Leaf)) { exit 1 }
$headers = @{ Authorization = 'Bearer ' + (Get-Content -LiteralPath $tokenFile -Raw).Trim() }
$base = "http://127.0.0.1:$Port/api/v1/system"

$corePid = 0
try {
    $info = Invoke-RestMethod -Method Get -Uri "$base/server" -Headers $headers -TimeoutSec 10
    $corePid = [int]$info.pid
    Invoke-RestMethod -Method Post -Uri "$base/shutdown" -Headers $headers -TimeoutSec 10 | Out-Null
}
catch { exit 1 }

# Port yopilgach ham yadro plaginlarni yopadi: jarayon tugaguncha kutamiz.
$deadline = (Get-Date).AddSeconds($WaitSeconds)
while ((Get-Date) -lt $deadline) {
    $alive = $corePid -gt 0 -and $null -ne (Get-Process -Id $corePid -ErrorAction SilentlyContinue)
    if (-not $alive -and -not (Test-Listening)) { exit 0 }
    Start-Sleep -Milliseconds 300
}
exit 1
