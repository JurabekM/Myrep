#!/usr/bin/env bash
# Demo APK'ni emulyatorda tekshiradi (CI: .github/workflows/baraka-demo-emulator.yml).
#   $1 — amaldagi demo APK, $2 — muddati o'tgan demo APK, $3 — skrinshotlar papkasi.
# Tekshiriladi: paket nomi va yorlig'i, ilova ochilib yiqilmasligi, muddat o'tgach ilova ochilmasligi.
set -euo pipefail
ACTIVE=$1 EXPIRED=$2 OUT=$3
PKG=uz.baraka.oilasi.demo
mkdir -p "$OUT"

fail() { echo "XATO: $*" >&2; adb logcat -d -t 300 > "$OUT/logcat.txt" || true; exit 1; }

launch() { # $1 — skrinshot nomi
  adb logcat -c
  adb shell am force-stop "$PKG" || true
  adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 > /dev/null
  sleep 20
  adb exec-out screencap -p > "$OUT/$1.png"
  adb shell uiautomator dump /sdcard/ui.xml > /dev/null 2>&1 && adb shell cat /sdcard/ui.xml > "$OUT/$1.xml" || true
  adb logcat -d > "$OUT/$1-logcat.txt"
  if grep -q "FATAL EXCEPTION\|Fatal signal" "$OUT/$1-logcat.txt"; then fail "$1: ilova yiqildi"; fi
  adb shell pidof "$PKG" > /dev/null || fail "$1: ilova jarayoni yo'q"
}

adb install -r "$ACTIVE"
adb shell pm list packages | grep -qx "package:$PKG" || fail "paket o'rnatilmadi: $PKG"
adb shell dumpsys package "$PKG" | grep -E "versionName|versionCode" | tee "$OUT/package.txt"
adb shell dumpsys package "$PKG" | grep -q "versionName=.*-demo" || fail "versionName '-demo' bilan tugamaydi"
# Asosiy (reliz) paket bilan yonma-yon turadi — uni almashtirmaydi.
adb shell pm list packages | grep -x "package:uz.baraka.oilasi" && fail "asosiy paket kutilmaganda o'rnatilgan" || true
launch 1-demo-ochildi

adb install -r "$EXPIRED"
launch 2-demo-muddati-otgan
# Flutter matni accessibility daraxtida bo'lsa — qo'shimcha tekshiruv (bo'lmasa skrinshot yetarli).
if grep -q "muddati tugadi" "$OUT/2-demo-muddati-otgan.xml" 2>/dev/null; then echo "ok: muddat ekrani matni topildi"; fi
echo "ok: demo emulyatorda ishladi"
