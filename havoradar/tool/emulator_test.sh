#!/usr/bin/env bash
# Emulyator/qurilmada to'liq tekshiruv (CI: .github/workflows/havoradar.yml → emulator).
#  1) Kotlin instrumental testlar: SyncWorker (jonli internet), bildirishnomalar, WorkManager.
#  2) Flutter integration_test: haqiqiy UI + MethodChannel + Kotlin yadro.
#  3) Ilovani oddiy foydalanuvchidek ishga tushirish: ekran matni, skrinshot, crash tekshiruvi.
set -euo pipefail
cd "$(dirname "$0")/.."
DEVICE="${DEVICE:-emulator-5554}"
OUT="${OUT:-build/device}"
mkdir -p "$OUT"
adb -s "$DEVICE" wait-for-device
API=$(adb -s "$DEVICE" shell getprop ro.build.version.sdk | tr -d '\r')
echo "== Qurilma: API $API"

echo "== 0. Debug APK (gradlew va local.properties ham yaratiladi)"
flutter build apk --debug
# integration_test shu faylni test versiyasi bilan almashtiradi — oddiy ilovani alohida saqlaymiz.
cp build/app/outputs/flutter-apk/app-debug.apk "$OUT/havoradar-debug.apk"

echo "== 1. Kotlin instrumental testlar"
(cd android && ./gradlew app:connectedDebugAndroidTest --console=plain -Pandroid.testInstrumentationRunnerArguments.class=uz.havoradar.app.DeviceTest)
adb -s "$DEVICE" logcat -d | grep "HAVORADAR-DEVICE" || true

echo "== 2. Flutter integration_test"
flutter test integration_test/device_test.dart -d "$DEVICE" --reporter expanded

echo "== 3. Foydalanuvchi sifatida ishga tushirish"
adb -s "$DEVICE" install -r "$OUT/havoradar-debug.apk" >/dev/null
adb -s "$DEVICE" logcat -c
adb -s "$DEVICE" shell am force-stop uz.havoradar.app
adb -s "$DEVICE" shell am start -W -n uz.havoradar.app/.MainActivity
sleep 30
adb -s "$DEVICE" exec-out screencap -p > "$OUT/home-api$API.png"
echo "-- Flutter loglari:"; adb -s "$DEVICE" logcat -d -s flutter:I | tail -15 || true
# Skrinshot logda (kichraytirilgan JPEG, base64) — artefaktni yuklamasdan ko'rish uchun.
IM=$(command -v magick || command -v convert || true)
if [ -z "$IM" ] && [ -n "${CI:-}" ]; then
  sudo apt-get install -y -qq imagemagick >/dev/null 2>&1 || true
  IM=$(command -v magick || command -v convert || true)
fi
if [ -n "$IM" ]; then
  "$IM" "$OUT/home-api$API.png" -resize 360x -quality 55 "$OUT/home-api$API.jpg"
  echo "HAVORADAR-SCREENSHOT-BEGIN"; base64 -w 0 "$OUT/home-api$API.jpg"; echo; echo "HAVORADAR-SCREENSHOT-END"
else
  echo "(ImageMagick yo'q — skrinshot faqat $OUT/home-api$API.png faylida)"
fi
adb -s "$DEVICE" logcat -d > "$OUT/logcat-api$API.txt"
if grep -E "FATAL EXCEPTION|ANR in uz.havoradar" "$OUT/logcat-api$API.txt"; then
  echo "!! Ilova qulagan yoki javob bermagan"; grep -A30 "FATAL EXCEPTION" "$OUT/logcat-api$API.txt" | head -60; exit 1
fi
echo "== Emulyator tekshiruvi muvaffaqiyatli (API $API)"
