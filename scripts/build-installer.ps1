# TAMGA o'rnatuvchisini (NSIS Setup.exe) yig'ish.
# Barcha vositalar release'da yig'iladi va Studio yoniga sidecar sifatida qo'shiladi
# (hook daemon'ni, Studio esa hook'ni o'z papkasidan qidiradi).
# Ishga tushirish (repo ildizidan):  powershell -ExecutionPolicy Bypass -File scripts/build-installer.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$target = if ($env:CARGO_TARGET_DIR) { $env:CARGO_TARGET_DIR } else { Join-Path $root "target" }
$triple = "x86_64-pc-windows-msvc"
$bins = "tamgad", "tamga-hook", "tamga-mcp-proxy", "tamga", "tamga-verify"
$crates = "tamgad", "tamga-hook", "tamga-mcp-proxy", "tamga-cli", "tamga-verify"

Push-Location $root
try {
    cargo build --release @($crates | ForEach-Object { "-p", $_ })
    if ($LASTEXITCODE -ne 0) { throw "cargo build yiqildi" }
    $dest = Join-Path $root "studio/src-tauri/binaries"
    New-Item -ItemType Directory -Force $dest | Out-Null
    foreach ($b in $bins) {
        Copy-Item (Join-Path $target "release/$b.exe") (Join-Path $dest "$b-$triple.exe") -Force
    }
    Push-Location (Join-Path $root "studio")
    pnpm install --frozen-lockfile
    pnpm tauri build --config src-tauri/tauri.bundle.json
    if ($LASTEXITCODE -ne 0) { throw "tauri build yiqildi" }
    Pop-Location
    $setup = Get-ChildItem (Join-Path $target "release/bundle/nsis/*.exe") | Sort-Object LastWriteTime | Select-Object -Last 1
    Write-Host "O'rnatuvchi: $($setup.FullName)" -ForegroundColor Green
} finally {
    Pop-Location
}
