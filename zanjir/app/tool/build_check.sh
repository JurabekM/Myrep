#!/usr/bin/env bash
# Android release build'ining TEXNIK tekshiruvi (12-faza, ADR-0016): R8, obfuskatsiya, manifest, imzo zanjiri ishlaydimi.
#
# Bir martalik kalit bilan imzolaydi (vaqtinchalik papkada yaratiladi va oxirida o'chiriladi) — bu AAB TARQATILMAYDI va
# Play'ga yuklanmaydi (yuklansa, o'sha kalit upload kaliti bo'lib qolardi). Haqiqiy release — faqat `build_release.sh`
# foydalanuvchi kaliti bilan (3-inson darvozasi). Haqiqiy `android/key.properties` bo'lsa — ishlamaydi (tegilmaydi).
#
#   app/tool/build_check.sh        # natija: app/build/check/ (AAB, mapping, symbols, hisobot)
set -euo pipefail

APP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEYPROPS="$APP/android/key.properties"
[[ ! -e "$KEYPROPS" ]] || { echo "android/key.properties mavjud — tekshiruv haqiqiy kalitga tegmaydi" >&2; exit 1; }
TMP="$(mktemp -d)"
cleanup() { rm -f "$KEYPROPS"; rm -rf "$TMP"; }
trap cleanup EXIT

pw="$(od -An -tx1 -N24 /dev/urandom | tr -d ' \n')"
keytool -genkeypair -keystore "$TMP/check.jks" -storetype PKCS12 -alias check -keyalg RSA -keysize 3072 -validity 1 \
  -dname "CN=ZANJIR build check - NOT FOR RELEASE" -storepass "$pw" -keypass "$pw" -noprompt >/dev/null 2>&1
printf 'storeFile=%s\nstorePassword=%s\nkeyAlias=check\nkeyPassword=%s\n' "$TMP/check.jks" "$pw" "$pw" > "$KEYPROPS"

cd "$APP"
OUT="$APP/build/check"
rm -rf "$OUT" && mkdir -p "$OUT"
flutter build appbundle --release --obfuscate --split-debug-info="$OUT/symbols"
cp build/app/outputs/bundle/release/app-release.aab "$OUT/zanjir-check.aab"
"$APP/tool/verify_aab.sh" "$OUT/zanjir-check.aab" --expect-cn "ZANJIR build check - NOT FOR RELEASE" | tee "$OUT/report.txt"
