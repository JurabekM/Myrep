# cargo ni MSVC muhitida ishga tushiradi (Visual Studio 2022 Build Tools, vcvars64.bat orqali).
# Ishlatish:  powershell -ExecutionPolicy Bypass -File scripts\cargo-msvc.ps1 test --workspace
# Sabab: bu mashinada GNU toolchain (dlltool / -lgcc_eh) bog'liqliklar bilan ishlamaydi.

$vcvars = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $vcvars)) {
    Write-Error "vcvars64.bat topilmadi: $vcvars"
    exit 1
}
$dump = cmd /c "`"$vcvars`" >nul 2>&1 && set"
foreach ($line in $dump) {
    if ($line -match '^([^=]+)=(.*)$') {
        try { Set-Item -Path ("env:" + $matches[1]) -Value $matches[2] -ErrorAction Stop } catch { }
    }
}
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& cargo +stable-x86_64-pc-windows-msvc @args
exit $LASTEXITCODE
