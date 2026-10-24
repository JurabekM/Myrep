# Android emulyator oynasini ekranga sig'diradi (o'lchaydi, kerak bo'lsa suradi).
#
# Nima uchun alohida skript: emulyator YOPILAYOTGANDA oyna holatini
# emulator-user.ini ga qayta yozadi. Shu bois ini'ni bir marta to'g'rilash
# yetmaydi - keyingi ishga tushishda oyna yana ekran tepasidan chiqib ketadi.
# Bu skript ishga tushgandan keyin oynaning HAQIQIY koordinatalarini
# (GetWindowRect) o'lchaydi va ishchi maydondan chiqqan bo'lsa ichkariga suradi.
#
#   powershell -File tools/emulator_window.ps1            # o'lchash + tuzatish
#   powershell -File tools/emulator_window.ps1 -CheckOnly # faqat o'lchash
param([switch]$CheckOnly)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class AqWin {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
"@
[AqWin]::SetProcessDPIAware() | Out-Null
Add-Type -AssemblyName System.Windows.Forms
$ish = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea

# FAQAT telefon oynasi: qemu-system jarayoni, sarlavhasi "Android Emulator".
# (emulator.exe ning konsol oynasini o'lchash yolg'on "sig'adi" natija berardi.)
$proc = Get-Process -ErrorAction SilentlyContinue |
  Where-Object { $_.MainWindowHandle -ne 0 -and $_.ProcessName -like "qemu-system*" -and $_.MainWindowTitle -like "Android Emulator*" } |
  Select-Object -First 1
if (-not $proc) { "emulyator oynasi topilmadi"; exit 2 }

$r = New-Object AqWin+RECT
[AqWin]::GetWindowRect($proc.MainWindowHandle, [ref]$r) | Out-Null
$w = $r.R - $r.L; $h = $r.B - $r.T
"ishchi maydon: {0}x{1} at ({2},{3})" -f $ish.Width, $ish.Height, $ish.X, $ish.Y
"oyna [$($proc.MainWindowTitle)]: ({0},{1})-({2},{3})  {4}x{5}" -f $r.L, $r.T, $r.R, $r.B, $w, $h

$sigadi = $r.T -ge $ish.Y -and $r.B -le $ish.Bottom -and $r.L -ge $ish.X -and $r.R -le $ish.Right
if ($sigadi) { "HOLAT: oyna to'liq ko'rinadi"; exit 0 }
if ($CheckOnly) { "HOLAT: oyna ekrandan CHIQIB KETGAN"; exit 1 }

# Balandlik sig'masa - oyna o'lchamini kichraytiramiz (emulyator kontentni
# o'zi qayta masshtablaydi); keyin ishchi maydonning o'ng yuqori burchagiga.
if ($h -gt ($ish.Height - 20)) {
  $yangiH = $ish.Height - 40
  $w = [int]($w * $yangiH / $h); $h = $yangiH
}
$x = $ish.Right - $w - 120
$y = $ish.Y + 20
[AqWin]::SetWindowPos($proc.MainWindowHandle, [IntPtr]::Zero, $x, $y, $w, $h, 0x0004) | Out-Null
Start-Sleep -Milliseconds 800
[AqWin]::GetWindowRect($proc.MainWindowHandle, [ref]$r) | Out-Null
"tuzatildi -> ({0},{1})-({2},{3})" -f $r.L, $r.T, $r.R, $r.B
if ($r.T -ge $ish.Y -and $r.B -le $ish.Bottom -and $r.L -ge $ish.X -and $r.R -le $ish.Right) {
  "HOLAT: oyna to'liq ko'rinadi"; exit 0
} else { "HOLAT: tuzatib bo'lmadi"; exit 1 }
