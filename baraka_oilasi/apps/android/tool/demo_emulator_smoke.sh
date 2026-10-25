#!/usr/bin/env bash
# Demo APK'ni emulyatorda tekshiradi (CI: .github/workflows/baraka-demo-emulator.yml).
#   $1 — amaldagi demo APK, $2 — muddati o'tgan demo APK, $3 — skrinshotlar papkasi.
# Tekshiriladi: paket nomi va versiyasi, ilova ochilib yiqilmasligi, muddat o'tgach ilova ochilmasligi.
# «DEMO» belgisi (Banner — chizma, accessibility daraxtida yo'q) skrinshotda ko'riladi.
set -euo pipefail
ACTIVE=$1 EXPIRED=$2 OUT=$3
PKG=uz.baraka.oilasi.demo
mkdir -p "$OUT"

fail() { echo "XATO: $*" >&2; adb logcat -d -t 300 > "$OUT/logcat.txt" || true; exit 1; }

# `grep -q` quvurda erta chiqadi va pipefail bilan adb SIGPIPE'dan yiqiladi — chiqish avval faylga.
packages() { adb shell pm list packages > "$OUT/packages.txt"; }

launch() { # $1 — skrinshot nomi
  adb logcat -c
  adb shell am force-stop "$PKG" || true
  adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 > /dev/null
  # Oyna fokusga kelguncha (60 s gacha), keyin Flutter birinchi kadrlari va yadro uchun.
  for _ in $(seq 60); do
    adb shell dumpsys window > "$OUT/window.txt"
    grep -q "mCurrentFocus=.*$PKG" "$OUT/window.txt" && break
    sleep 1
  done
  grep -q "mCurrentFocus=.*$PKG" "$OUT/window.txt" || fail "$1: ilova oynasi ochilmadi"
  sleep 10
  # Qurilma ichidagi `screencap` swiftshader'li headless emulyatorda bo'sh fayl beradi — kadr
  # emulyatorning o'zidan (konsol buyrug'i, hostga yoziladi); bo'lmasa — qurilmadagi screencap.
  adb emu screenrecord screenshot "$OUT/$1.png" > /dev/null || true
  if [ ! -s "$OUT/$1.png" ]; then
    adb shell screencap -p /sdcard/shot.png && adb pull /sdcard/shot.png "$OUT/$1.png" > /dev/null || true
  fi
  [ -s "$OUT/$1.png" ] || echo "::warning::$1: skrinshot bo'sh"
  adb shell uiautomator dump /sdcard/ui.xml > /dev/null 2>&1 && adb shell cat /sdcard/ui.xml > "$OUT/$1.xml" || : > "$OUT/$1.xml"
  adb logcat -d > "$OUT/$1-logcat.txt"
  # Faqat shu ilovaning yiqilishi (Java: «Process: <pkg>», native: «>>> <pkg> <<<»).
  if grep -qE "Process: $PKG|>>> $PKG <<<" "$OUT/$1-logcat.txt"; then fail "$1: ilova yiqildi"; fi
  adb shell pidof "$PKG" > /dev/null || fail "$1: ilova jarayoni yo'q"
}

adb install -r "$ACTIVE"
packages
grep -qx "package:$PKG" "$OUT/packages.txt" || fail "paket o'rnatilmadi: $PKG"
# Asosiy (reliz) paket bilan yonma-yon turadi — uni almashtirmaydi.
if grep -qx "package:uz.baraka.oilasi" "$OUT/packages.txt"; then fail "asosiy paket kutilmaganda o'rnatilgan"; fi
adb shell dumpsys package "$PKG" > "$OUT/package-dump.txt"
grep -E "versionName|versionCode" "$OUT/package-dump.txt" | tee "$OUT/package.txt"
grep -q "versionName=.*-demo" "$OUT/package.txt" || fail "versionName '-demo' bilan tugamaydi"
launch 1-demo-ochildi

adb install -r "$EXPIRED"
launch 2-demo-muddati-otgan
# Muddat ekrani: Flutter matni accessibility daraxtida bo'lsa — qat'iy tekshiruv. Daraxt umuman
# bo'sh bo'lsa (semantika yoqilmagan), faqat ogohlantirish — skrinshot qo'lda ko'riladi.
if grep -q "muddati tugadi" "$OUT/2-demo-muddati-otgan.xml"; then
  echo "ok: muddat ekrani matni topildi"
elif grep -oE '<node [^>]*>' "$OUT/2-demo-muddati-otgan.xml" | grep "package=\"$PKG\"" \
    | grep -E '(text|content-desc)="[^"]' > /dev/null; then
  fail "muddati o'tgan demo muddat ekranini ko'rsatmadi"
else
  echo "::warning::accessibility daraxti bo'sh — muddat ekranini skrinshotdan tekshiring"
fi
echo "ok: demo emulyatorda ishladi"
