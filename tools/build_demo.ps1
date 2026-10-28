# Demo APK yig'ish - o'rtadagi odamga yoki hamkorga KO'RSATISH uchun.
#
#   powershell -File tools/build_demo.ps1              # 30 kunlik
#   powershell -File tools/build_demo.ps1 -Days 14
#
# Demo himoyasi:
# - paket nomi uz.barakadastur.demo: haqiqiy ilova (uz.barakadastur.app) o'rnini
#   egallay olmaydi va uni yangilay olmaydi;
# - har doim debug kaliti bilan imzolanadi (key.properties berilgan bo'lsa ham):
#   Google Play bunday faylni qabul qilmaydi;
# - launcher nomi "DEMO Baraka Dastur" (kesilsa ham DEMO ko'rinadi);
# - har ekranda "DEMO" lentasi va muallif / "nashr qilish taqiqlanadi" yozuvi;
# - muddat tugagach (-Days) ilova ochilmaydi, faqat xabar ko'rsatadi;
# - Dart kodi obfuskatsiya qilingan, R8 yoqilgan.
# Natija: release/demo/baraka-dastur-demo-<versiya+build>-<muddat>.apk va .sha256.
param(
    [int]$Days = 30,
    # Barcha ABI: plaginlarning native kutubxonalari hamma ABI uchun keladi;
    # Flutter faqat bittasiga yig'ilsa, boshqa ABI qurilmada ilova ochilmaydi.
    [string]$Abis = "android-arm,android-arm64,android-x64"
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not $env:JAVA_HOME) {
    $jbr = "C:\Program Files\Android\Android Studio\jbr"
    if (Test-Path $jbr) { $env:JAVA_HOME = $jbr }
}

# To'liq versiya (build raqami bilan): bir kunda yig'ilgan ikki demo bir-birining
# ustidan yozilmasin (muddat sanasi bir xil chiqadi).
$version = (Select-String -Path pubspec.yaml -Pattern '^version:\s*(\S+)').Matches[0].Groups[1].Value
$until = (Get-Date).AddDays($Days).ToString("yyyy-MM-dd")
$symbols = "build/symbols/demo-$version"

flutter build apk --release --target-platform $Abis `
    --obfuscate --split-debug-info=$symbols `
    --dart-define=BARAKA_DEMO=true --dart-define=BARAKA_DEMO_UNTIL=$until `
    --android-project-arg=baraka.demo=true
if ($LASTEXITCODE -ne 0) { throw "flutter build apk (demo) yiqildi ($LASTEXITCODE)" }

$out = "release/demo"
New-Item -ItemType Directory -Force $out | Out-Null
$apk = "$out/baraka-dastur-demo-$version-$until.apk"
Copy-Item build/app/outputs/flutter-apk/app-release.apk $apk -Force
$hash = (Get-FileHash $apk -Algorithm SHA256).Hash.ToLower()
[IO.File]::WriteAllText((Resolve-Path $out).Path + "\" + (Split-Path $apk -Leaf) + ".sha256", "$hash  $(Split-Path $apk -Leaf)`n")

Write-Host ""
Write-Host "Demo: $apk (muddat: $until gacha)"
Write-Host "SHA-256: $hash"
