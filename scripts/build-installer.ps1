# TAMGA o'rnatuvchisini (NSIS Setup.exe) yig'ish va imzolash.
# Barcha vositalar release'da yig'iladi va Studio yoniga sidecar sifatida qo'shiladi
# (hook daemon'ni, Studio esa hook'ni o'z papkasidan qidiradi).
#
# Ishga tushirish (repo ildizidan):  powershell -ExecutionPolicy Bypass -File scripts/build-installer.ps1
#
# Kod imzosi: scripts/sign.ps1 dagi TAMGA_SIGN_* o'zgaruvchilari (sertifikat ombori, .pfx yoki
# Azure Trusted Signing). Sozlanmagan bo'lsa — imzosiz dev build. Reliz uchun TAMGA_SIGN_REQUIRED=1.
# Imzolanadi: 5 ta sidecar (bundle'dan oldin), Studio exe, o'chiruvchi va o'rnatuvchining o'zi.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$target = if ($env:CARGO_TARGET_DIR) { $env:CARGO_TARGET_DIR } else { Join-Path $root "target" }
$triple = "x86_64-pc-windows-msvc"
$bins = "tamgad", "tamga-hook", "tamga-mcp-proxy", "tamga", "tamga-verify"
$crates = "tamgad", "tamga-hook", "tamga-mcp-proxy", "tamga-cli", "tamga-verify"
$sign = Join-Path $PSScriptRoot "sign.ps1"
$signing = [bool]($env:TAMGA_SIGN_THUMBPRINT -or $env:TAMGA_SIGN_PFX -or ($env:TAMGA_SIGN_AZURE_DLIB -and $env:TAMGA_SIGN_AZURE_METADATA))

Push-Location $root
try {
    cargo build --release @($crates | ForEach-Object { "-p", $_ })
    if ($LASTEXITCODE -ne 0) { throw "cargo build yiqildi" }
    $dest = Join-Path $root "studio/src-tauri/binaries"
    New-Item -ItemType Directory -Force $dest | Out-Null
    foreach ($b in $bins) {
        $out = Join-Path $dest "$b-$triple.exe"
        Copy-Item (Join-Path $target "release/$b.exe") $out -Force
        & powershell -NoProfile -ExecutionPolicy Bypass -File $sign $out
        if ($LASTEXITCODE -ne 0) { throw "imzolash yiqildi: $out" }
    }

    # Tauri har bir o'zi yaratgan faylni (Studio exe, uninstall.exe, Setup.exe) shu buyruq bilan imzolaydi.
    $signCfg = Join-Path ([IO.Path]::GetTempPath()) "tamga-sign-config.json"
    $cfg = @{ bundle = @{ windows = @{ signCommand = @{
        cmd = "powershell"; args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $sign, "%1") } } } }
    [IO.File]::WriteAllText($signCfg, ($cfg | ConvertTo-Json -Depth 6), (New-Object Text.UTF8Encoding $false))

    # Sertifikat bo'lmasa signCommand ulanmaydi: Tauri imzosiz fayllarni tekshirib, chalg'ituvchi xato yozadi.
    $configs = @("--config", "src-tauri/tauri.bundle.json")
    if ($signing) { $configs += @("--config", $signCfg) }

    Push-Location (Join-Path $root "studio")
    pnpm install --frozen-lockfile
    pnpm tauri build @configs
    if ($LASTEXITCODE -ne 0) { throw "tauri build yiqildi" }
    Pop-Location

    $setup = Get-ChildItem (Join-Path $target "release/bundle/nsis/*.exe") | Sort-Object LastWriteTime | Select-Object -Last 1
    $hash = (Get-FileHash $setup.FullName -Algorithm SHA256).Hash.ToLower()
    $sums = Join-Path $setup.DirectoryName "SHA256SUMS.txt"
    [IO.File]::WriteAllText($sums, "$hash  $($setup.Name)`n", (New-Object Text.UTF8Encoding $false))

    Write-Host ""
    Write-Host "O'rnatuvchi: $($setup.FullName)" -ForegroundColor Green
    Write-Host "SHA-256    : $hash  ($sums)"
    $sig = Get-AuthenticodeSignature $setup.FullName
    if ($sig.SignerCertificate) {
        Write-Host ("Imzo       : {0} | {1} | vaqt tamg'asi: {2}" -f $sig.Status, $sig.SignerCertificate.Subject, [bool]$sig.TimeStamperCertificate)
    } elseif ($signing) {
        throw "sertifikat sozlangan, lekin o'rnatuvchi imzolanmagan"
    } else {
        Write-Host "Imzo       : YO'Q (dev build; SmartScreen 'noma'lum nashriyotchi' deydi)" -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}
