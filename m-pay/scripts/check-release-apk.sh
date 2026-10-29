#!/usr/bin/env bash
# Release APK'da sinov ko'prigi (virtual NFC) yo'qligini tekshiradi: u faqat debug build uchun
# (relay hujumi uchun eshik bo'lmasin). Debug APK'da esa borligi tasdiqlanadi (tekshiruv ishlayotganini isbotlash).
#   bash scripts/check-release-apk.sh [modul ...]   (standart: wallet-demo wallet-app)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$(command -v python || command -v python3)"
has_bridge() { # APK ichidagi manifest va dex'larda sinf nomini qidiradi
  "$PY" - "$1" <<'EOF'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
needles = [b"VirtualNfcService", "VirtualNfcService".encode("utf-16-le")]
hit = any(n in z.read(name) for name in z.namelist()
          if name.endswith(".dex") or name == "AndroidManifest.xml" for n in needles)
print("bor" if hit else "yo'q")
EOF
}

# Modullar: argumentlar yoki ikkala hamyon (demo va mijoz ilovasi, ADR-0030).
for m in ${@:-wallet-demo wallet-app}; do
  APKS="$ROOT/android/$m/build/outputs/apk"
  DEBUG="$APKS/debug/$m-debug.apk"
  RELEASE="$APKS/release/$m-release.apk"
  [ -f "$RELEASE" ] || RELEASE="$APKS/release/$m-release-unsigned.apk"
  for f in "$DEBUG" "$RELEASE"; do
    [ -f "$f" ] || { echo "XATO: $f yo'q — avval ./gradlew :$m:assembleDebug :$m:assembleRelease"; exit 1; }
  done
  d="$(has_bridge "$DEBUG")"; r="$(has_bridge "$RELEASE")"
  echo "$m — debug: $d, release: $r"
  [ "$d" = "bor" ] || { echo "XATO: $m debug APK'da ko'prik topilmadi — tekshiruv noto'g'ri"; exit 1; }
  [ "$r" = "yo'q" ] || { echo "XATO: $m release APK'da virtual NFC ko'prigi bor!"; exit 1; }
done
echo "RELEASE OK: sinov ko'prigi release'da yo'q"
