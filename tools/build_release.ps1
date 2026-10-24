# Release APK va AAB yig'ish (MVP_PLAN Vazifa 15, docs/RELEASE_CHECKLIST.md).
#
#   powershell -File tools/build_release.ps1
#   powershell -File tools/build_release.ps1 -SigningProperties C:\keys\baraka\key.properties
#   powershell -File tools/build_release.ps1 -NoBundle      # faqat APK
#
# - Dart: --obfuscate, belgilar (symbols) --split-debug-info bilan alohida
#   papkaga - crash stack'ini `flutter symbolize` bilan ochish uchun saqlang
#   (repoga qo'shilmaydi: build/ gitignore qilingan).
# - Android: R8 (isMinifyEnabled + isShrinkResources), build.gradle.kts.
# - Imzo: key.properties repodan tashqarida; berilmasa debug kaliti (faqat sinov).
# - Natija build/release/<versiya>/ da: ABI bo'yicha APK'lar, AAB (Play), har
#   build'ning O'Z mapping.txt va Dart belgilari (zip), SHA256SUMS.txt.
#   mapping va belgilar aynan o'sha build'niki bo'lishi shart: keyingi build
#   (shu jumladan -t integration_test) build/app/outputs/mapping ni qayta yozadi.
param(
    [string]$SigningProperties = $env:BARAKA_SIGNING_PROPERTIES,
    [string]$Abis = "android-arm,android-arm64,android-x64",
    [switch]$NoBundle
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not $env:JAVA_HOME) {
    $jbr = "C:\Program Files\Android\Android Studio\jbr"
    if (Test-Path $jbr) { $env:JAVA_HOME = $jbr }
}
if ($SigningProperties) {
    if (-not (Test-Path $SigningProperties)) { throw "Imzo fayli topilmadi: $SigningProperties" }
    $env:BARAKA_SIGNING_PROPERTIES = (Resolve-Path $SigningProperties).Path
    Write-Host "Imzo: $env:BARAKA_SIGNING_PROPERTIES"
} else {
    Write-Warning "Imzo fayli berilmadi - debug kaliti bilan imzolanadi (Play'ga yuklab bo'lmaydi)."
}

$version = (Select-String -Path pubspec.yaml -Pattern '^version:\s*(\S+)').Matches[0].Groups[1].Value
$out = "build/release/$version"
$mapping = "build/app/outputs/mapping/release/mapping.txt"
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force $out | Out-Null

function Save-BuildArtifacts([string]$Kind, [string]$Symbols) {
    if (-not (Test-Path $mapping)) { throw "mapping.txt topilmadi ($Kind): R8 ishlamadimi?" }
    Copy-Item $mapping "$out/mapping-$Kind.txt"
    Compress-Archive -Path "$Symbols/*" -DestinationPath "$out/symbols-$Kind.zip" -Force
}

# 1) APK - ABI bo'yicha (telefonga to'g'ridan-to'g'ri o'rnatish va sinov).
$symApk = "build/symbols/$version/apk"
flutter build apk --release --split-per-abi --target-platform $Abis `
    --obfuscate --split-debug-info=$symApk
if ($LASTEXITCODE -ne 0) { throw "flutter build apk yiqildi ($LASTEXITCODE)" }
Copy-Item build/app/outputs/flutter-apk/app-*-release.apk $out
Save-BuildArtifacts "apk" $symApk

# 2) AAB - Google Play uchun (barcha ABI bitta to'plamda).
if (-not $NoBundle) {
    $symAab = "build/symbols/$version/aab"
    flutter build appbundle --release --target-platform $Abis `
        --obfuscate --split-debug-info=$symAab
    if ($LASTEXITCODE -ne 0) { throw "flutter build appbundle yiqildi ($LASTEXITCODE)" }
    Copy-Item build/app/outputs/bundle/release/app-release.aab $out
    Save-BuildArtifacts "aab" $symAab
}

Get-ChildItem $out -File | Sort-Object Name | ForEach-Object {
    "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.Name
} | Set-Content -Encoding ascii "$out/SHA256SUMS.txt"

Write-Host ""
Write-Host "Natija: $out"
Get-ChildItem $out -File |
    ForEach-Object { "{0}  {1:N1} MB  {2}" -f $_.Name, ($_.Length / 1MB), $_.LastWriteTime }
