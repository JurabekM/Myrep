# Android emulyatorni ekranga SIG'ADIGAN qilib ishga tushiradi.
#
# Tuzoq: emulyator YOPILAYOTGANDA oyna holatini (window.scale = -1, ya'ni
# "avtomatik") emulator-user.ini ga qayta yozadi. 1080x2400 telefon avtomatik
# masshtabda monitordan baland chiqadi va oyna ekran tepasidan chiqib ketadi.
# Shu bois:
#   1) ishga tushirishdan OLDIN ini har safar qayta yoziladi;
#   2) ishga tushgach TELEFON oynasining haqiqiy koordinatalari o'lchanadi va
#      kerak bo'lsa tuzatiladi (emulator_window.ps1);
#   3) natija chiqariladi - "ko'rinadi" deb taxmin qilinmaydi.
#
#   powershell -File tools/start_emulator.ps1 [-Avd Medium_Phone_API_36.0] [qo'shimcha emulyator argumentlari]
#
# DIQQAT: bu fayl faqat ASCII bo'lsin - Windows PowerShell 5.1 BOM'siz UTF-8'ni
# ANSI deb o'qiydi va o'zbekcha tutuq belgilari skriptni buzadi.
param(
  [string]$Avd = "Medium_Phone_API_36.0",
  [double]$Scale = 0.30,
  [Parameter(ValueFromRemainingArguments = $true)][string[]]$Extra
)
$ErrorActionPreference = "Stop"
$avdRoot = Join-Path $env:USERPROFILE ".android\avd"
$ini = Get-Content (Join-Path $avdRoot "$Avd.ini")
# .ini fayl AVD NOMI bilan emas, path= ko'rsatgan HAQIQIY papkada yotadi.
$papka = ($ini | Where-Object { $_ -like "path=*" }) -replace "^path=", ""
$user = Join-Path $papka "emulator-user.ini"
$eski = if (Test-Path $user) { Get-Content $user } else { @() }
$qolgan = $eski | Where-Object { $_ -notmatch "^window\.(x|y|scale)\s*=" }
$yangi = @("window.x = 1100", "window.y = 0", ("window.scale = {0:F6}" -f $Scale).Replace(",", ".")) + $qolgan
Set-Content -Path $user -Value $yangi -Encoding ascii
"emulator-user.ini: scale=$Scale, y=0 ($user)"

$emu = Join-Path $env:LOCALAPPDATA "Android\Sdk\emulator\emulator.exe"
# $args - PowerShell'ning avtomatik o'zgaruvchisi, shu bois boshqa nom.
$emuArgs = @("-avd", $Avd, "-no-snapshot-save", "-no-boot-anim")
if ($Extra) { $emuArgs += ($Extra | Where-Object { $_ }) }
# Konsol oynasi yashiriladi (telefon oynasi alohida Qt oynasi).
Start-Process -FilePath $emu -ArgumentList $emuArgs -WindowStyle Hidden | Out-Null

# TELEFON oynasi paydo bo'lishini kutib, o'lchaymiz va kerak bo'lsa tuzatamiz.
$tekshir = Join-Path $PSScriptRoot "emulator_window.ps1"
for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep -Seconds 2
  $bor = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowHandle -ne 0 -and $_.ProcessName -like "qemu-system*" -and $_.MainWindowTitle -like "Android Emulator*"
  }
  if ($bor) { Start-Sleep -Seconds 4; break }
}
& powershell -NoProfile -ExecutionPolicy Bypass -File $tekshir
