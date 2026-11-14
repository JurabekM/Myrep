# ROSTOR-2: reliz APK va AAB yig'ish (docs/play/RELEASE_CHECKLIST.md).
#
#   powershell -ExecutionPolicy Bypass -File tools/build_release.ps1 -SigningProperties C:\keys\rostor2\upload\key.properties
#   ... -ExpectedSignatureSha256 AB:CD:...   # "haqiqiymi?" ekranidagi ichki tekshiruv uchun
#   ... -NoBundle                            # faqat APK
#   ... -NoApk                               # faqat AAB (Play)
#   powershell -ExecutionPolicy Bypass -File tools/build_release.ps1 -AllowDebug   # debug imzoli SINOV nusxa
#
# - Dart: --obfuscate, belgilar --split-debug-info bilan alohida (crash'ni `flutter symbolize` bilan ochish uchun).
# - Android: R8 (build.gradle.kts). Imzo: key.properties repodan tashqarida.
# - -ExpectedSignatureSha256: Play orqali tarqatiladigan AAB uchun - Play Console'dagi "App signing key"
#   xeshi; to'g'ridan-to'g'ri APK uchun - upload kaliti xeshi (upload-cert-sha256.txt). Berilmasa
#   ilova ichidagi tekshiruv o'chiq, ekran faqat izni ko'rsatadi.
# - Natija release/<versiya>/ da (global qoida: build/ ichida qoldirilmaydi): ABI bo'yicha APK'lar,
#   AAB, har build'ning o'z mapping.txt va Dart belgilari (zip), SHA256SUMS.txt.
# - Oxirida har APK tools/check_release.py dan o'tadi (INTERNET yo'q, ruxsatlar, baza imzosi,
#   debuggable emas, debug kaliti emas).
#
# DIQQAT: bu fayl faqat ASCII bo'lsin (PowerShell 5.1).
param(
    [string]$SigningProperties = $env:ROSTOR2_SIGNING_PROPERTIES,
    [string]$ExpectedSignatureSha256 = "",
    [string]$Abis = "android-arm,android-arm64,android-x64",
    [switch]$NoBundle,
    [switch]$NoApk,
    [switch]$AllowDebug
)
$ErrorActionPreference = "Stop"
if ($NoBundle -and $NoApk) { throw "-NoBundle va -NoApk birga: yig'iladigan narsa qolmaydi." }
$root = Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $root "app")

if (-not $env:JAVA_HOME -or -not (Test-Path (Join-Path $env:JAVA_HOME "bin\java.exe"))) {
    $env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
}
if ((Get-PSDrive C).Free / 1GB -lt 50) { throw "C: diskda 50 GB dan kam joy - yig'ish to'xtatildi." }

if ($SigningProperties) {
    if (-not (Test-Path $SigningProperties)) { throw "Imzo fayli topilmadi: $SigningProperties" }
    $env:ROSTOR2_SIGNING_PROPERTIES = (Resolve-Path $SigningProperties).Path
    Write-Host "Imzo: $env:ROSTOR2_SIGNING_PROPERTIES"
} elseif ($AllowDebug) {
    Remove-Item Env:ROSTOR2_SIGNING_PROPERTIES -ErrorAction SilentlyContinue
    Write-Warning "Debug kaliti bilan SINOV nusxa yig'iladi (Play'ga yuklab bo'lmaydi)."
} else {
    throw "Imzo fayli berilmadi. -SigningProperties <key.properties> yoki sinov uchun -AllowDebug."
}
# Gradle -P xossalari. ORG_GRADLE_PROJECT_* flutter build orqali Gradle'ga yetmaydi.
$gradleArgs = @()
if ($ExpectedSignatureSha256) {
    $hex = $ExpectedSignatureSha256.Replace(":", "").Trim().ToUpper()
    if ($hex -notmatch '^[0-9A-F]{64}$') { throw "Imzo xeshi SHA-256 emas: $ExpectedSignatureSha256" }
    $gradleArgs += "--android-project-arg=expectedSignatureSha256=$hex"
    Write-Host "Kutilgan imzo SHA-256: $hex"
}

$version = (Select-String -Path pubspec.yaml -Pattern '^version:\s*(\S+)').Matches[0].Groups[1].Value
$suffix = if ($SigningProperties) { "" } else { "-SINOV" }
$out = Join-Path $root "release/$version$suffix"
$mapping = "build/app/outputs/mapping/release/mapping.txt"
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force $out | Out-Null

function Save-BuildArtifacts([string]$Kind, [string]$Symbols) {
    if (-not (Test-Path $mapping)) { throw "mapping.txt topilmadi ($Kind): R8 ishlamadimi?" }
    Copy-Item $mapping "$out/mapping-$Kind.txt"
    Compress-Archive -Path "$Symbols/*" -DestinationPath "$out/symbols-$Kind.zip" -Force
}

# Dart belgilari aynan shu build'niki bo'lishi uchun Flutter keshi tozalanadi.
Remove-Item -Recurse -Force .dart_tool/flutter_build, "build/symbols/$version" -ErrorAction SilentlyContinue

if (-not $NoApk) {
    $symApk = "build/symbols/$version/apk"
    flutter build apk --release --split-per-abi --target-platform $Abis --obfuscate --split-debug-info=$symApk @gradleArgs
    if ($LASTEXITCODE -ne 0) { throw "flutter build apk yiqildi ($LASTEXITCODE)" }
    Get-ChildItem build/app/outputs/flutter-apk/app-*-release.apk | ForEach-Object {
        $abi = $_.Name -replace '^app-(.+)-release\.apk$', '$1'
        Copy-Item $_.FullName "$out/ROSTOR-2-$version-$abi$suffix.apk"
    }
    Save-BuildArtifacts "apk" $symApk
}

if (-not $NoBundle) {
    $symAab = "build/symbols/$version/aab"
    flutter build appbundle --release --target-platform $Abis --obfuscate --split-debug-info=$symAab @gradleArgs
    if ($LASTEXITCODE -ne 0) { throw "flutter build appbundle yiqildi ($LASTEXITCODE)" }
    Copy-Item build/app/outputs/bundle/release/app-release.aab "$out/ROSTOR-2-$version$suffix.aab"
    Save-BuildArtifacts "aab" $symAab
}

# APK va AAB: INTERNET yo'q, baza imzosi, imzolovchi debug emas (AAB uchun -ExpectedSignatureSha256 qo'llanmaydi:
# u upload kaliti bilan imzolangan, Play esa app signing kaliti bilan qayta imzolaydi).
$checkArgs = @((Join-Path $root "tools/check_release.py")) + (Get-ChildItem "$out/*.apk", "$out/*.aab" | ForEach-Object { $_.FullName })
if ($AllowDebug -and -not $SigningProperties) { $checkArgs += "--allow-debug" }
if ($ExpectedSignatureSha256) { $checkArgs += @("--expect-cert", $ExpectedSignatureSha256) }
& py @checkArgs
if ($LASTEXITCODE -ne 0) { throw "check_release.py yiqildi - reliz kafolatlari buzilgan." }

# LF bilan: `sha256sum -c SHA256SUMS.txt` to'g'ridan-to'g'ri ishlaydi.
$sums = Get-ChildItem $out -File | Where-Object Name -ne "SHA256SUMS.txt" | Sort-Object Name | ForEach-Object {
    "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.Name
}
[IO.File]::WriteAllText((Join-Path (Resolve-Path $out) "SHA256SUMS.txt"), (($sums -join "`n") + "`n"))

Write-Host ""
Write-Host "Natija: $out"
Get-ChildItem $out -File | ForEach-Object { "{0}  {1:N1} MB  {2}" -f $_.Name, ($_.Length / 1MB), $_.LastWriteTime }
