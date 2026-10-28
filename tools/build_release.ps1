# Release APK va AAB yig'ish (MVP_PLAN Vazifa 15, docs/RELEASE_CHECKLIST.md).
#
#   powershell -File tools/build_release.ps1
#   powershell -File tools/build_release.ps1 -SigningProperties C:\keys\baraka\key.properties `
#       -ExpectedSignatureSha256 AB:CD:...     # tools/create_upload_key.ps1 chiqargan xesh
#   powershell -File tools/build_release.ps1 -NoBundle      # faqat APK
#   powershell -File tools/build_release.ps1 -NoApk         # faqat AAB (Play)
#
# - Dart: --obfuscate, belgilar (symbols) --split-debug-info bilan alohida
#   papkaga - crash stack'ini `flutter symbolize` bilan ochish uchun saqlang
#   (repoga qo'shilmaydi: build/ gitignore qilingan).
# - Android: R8 (isMinifyEnabled + isShrinkResources), build.gradle.kts.
# - Imzo: key.properties repodan tashqarida; berilmasa debug kaliti (faqat sinov).
# - Imzo xeshi (-ExpectedSignatureSha256): ilova ichidagi yaxlitlik tekshiruvi
#   uchun (BuildConfig.EXPECTED_SIGNATURE_SHA256). Play orqali tarqatiladigan
#   AAB uchun - Play Console'dagi "App signing key" xeshi, to'g'ridan-to'g'ri
#   APK uchun - upload kaliti xeshi. Berilmasa tekshiruv o'chiq.
# - Natija build/release/<versiya>/ da: ABI bo'yicha APK'lar, AAB (Play), har
#   build'ning O'Z mapping.txt va Dart belgilari (zip), SHA256SUMS.txt.
#   mapping va belgilar aynan o'sha build'niki bo'lishi shart: keyingi build
#   (shu jumladan -t integration_test) build/app/outputs/mapping ni qayta yozadi.
param(
    [string]$SigningProperties = $env:BARAKA_SIGNING_PROPERTIES,
    [string]$ExpectedSignatureSha256 = $env:BARAKA_EXPECTED_SIGNATURE_SHA256,
    [string]$Abis = "android-arm,android-arm64,android-x64",
    [switch]$NoBundle,
    [switch]$NoApk
)
$ErrorActionPreference = "Stop"
if ($NoBundle -and $NoApk) { throw "-NoBundle va -NoApk birga: yig'iladigan narsa qolmaydi." }
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
# Gradle -P xossalari (build.gradle.kts). ORG_GRADLE_PROJECT_* muhit
# o'zgaruvchisi flutter build orqali Gradle'ga yetib bormaydi.
$gradleArgs = @()
if ($ExpectedSignatureSha256) {
    $hex = $ExpectedSignatureSha256.Replace(":", "").Trim().ToUpper()
    if ($hex -notmatch '^[0-9A-F]{64}$') { throw "Imzo xeshi SHA-256 emas: $ExpectedSignatureSha256" }
    $gradleArgs += "--android-project-arg=expectedSignatureSha256=$hex"
    Write-Host "Kutilgan imzo SHA-256: $hex"
} elseif ($SigningProperties) {
    Write-Warning "Imzo xeshi berilmadi (-ExpectedSignatureSha256) - ilova ichidagi imzo tekshiruvi o'chiq qoladi."
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

# Dart belgilari aynan shu build'niki bo'lishi uchun Flutter keshi tozalanadi:
# kesh "o'zgarmagan" deb hisoblasa, --split-debug-info papkasi qayta yozilmaydi.
Remove-Item -Recurse -Force .dart_tool/flutter_build, "build/symbols/$version" -ErrorAction SilentlyContinue

# 1) APK - ABI bo'yicha (telefonga to'g'ridan-to'g'ri o'rnatish va sinov).
if (-not $NoApk) {
    $symApk = "build/symbols/$version/apk"
    flutter build apk --release --split-per-abi --target-platform $Abis `
        --obfuscate --split-debug-info=$symApk @gradleArgs
    if ($LASTEXITCODE -ne 0) { throw "flutter build apk yiqildi ($LASTEXITCODE)" }
    Copy-Item build/app/outputs/flutter-apk/app-*-release.apk $out
    Save-BuildArtifacts "apk" $symApk
}

# 2) AAB - Google Play uchun (barcha ABI bitta to'plamda).
if (-not $NoBundle) {
    $symAab = "build/symbols/$version/aab"
    flutter build appbundle --release --target-platform $Abis `
        --obfuscate --split-debug-info=$symAab @gradleArgs
    if ($LASTEXITCODE -ne 0) { throw "flutter build appbundle yiqildi ($LASTEXITCODE)" }
    Copy-Item build/app/outputs/bundle/release/app-release.aab $out
    Save-BuildArtifacts "aab" $symAab
}

# LF bilan: `sha256sum -c SHA256SUMS.txt` to'g'ridan-to'g'ri ishlaydi.
$sums = Get-ChildItem $out -File | Sort-Object Name | ForEach-Object {
    "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.Name
}
[IO.File]::WriteAllText((Join-Path (Resolve-Path $out) "SHA256SUMS.txt"), (($sums -join "`n") + "`n"))

Write-Host ""
Write-Host "Natija: $out"
Get-ChildItem $out -File |
    ForEach-Object { "{0}  {1:N1} MB  {2}" -f $_.Name, ($_.Length / 1MB), $_.LastWriteTime }
