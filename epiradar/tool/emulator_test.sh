#!/usr/bin/env bash
# Emulyator/qurilmada to'liq tekshiruv (CI: .github/workflows/epiradar.yml → emulator).
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

echo "== 1. Kotlin instrumental testlar"
(cd android && ./gradlew app:connectedDebugAndroidTest --console=plain -Pandroid.testInstrumentationRunnerArguments.class=uz.epiradar.app.DeviceTest)
adb -s "$DEVICE" logcat -d | grep "EPIRADAR-DEVICE" || true

echo "== 2. Flutter integration_test"
flutter test integration_test/device_test.dart -d "$DEVICE" --reporter expanded

echo "== 3. Foydalanuvchi sifatida ishga tushirish"
adb -s "$DEVICE" install -r build/app/outputs/flutter-apk/app-debug.apk >/dev/null
adb -s "$DEVICE" logcat -c
adb -s "$DEVICE" shell am force-stop uz.epiradar.app
adb -s "$DEVICE" shell am start -W -n uz.epiradar.app/.MainActivity
sleep 25
adb -s "$DEVICE" exec-out screencap -p > "$OUT/home-api$API.png"
# Flutter semantik daraxti accessibility orqali ko'rinadi — ekrandagi matnlar logga.
for i in 1 2; do adb -s "$DEVICE" shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1 || true; sleep 3; done
adb -s "$DEVICE" shell cat /sdcard/ui.xml > "$OUT/ui-api$API.xml" || true
echo "-- Ekrandagi matnlar:"
grep -o 'content-desc="[^"]*"\|text="[^"]*"' "$OUT/ui-api$API.xml" | grep -v '=""' | sed 's/&#10;/ | /g' | head -60 || true
# Skrinshot logda (kichraytirilgan JPEG, base64) — artefaktsiz ko'rish uchun.
if command -v convert >/dev/null; then
  convert "$OUT/home-api$API.png" -resize 360x -quality 55 "$OUT/home-api$API.jpg"
  echo "EPIRADAR-SCREENSHOT-BEGIN"; base64 -w 0 "$OUT/home-api$API.jpg"; echo; echo "EPIRADAR-SCREENSHOT-END"
fi
adb -s "$DEVICE" logcat -d > "$OUT/logcat-api$API.txt"
if grep -E "FATAL EXCEPTION|ANR in uz.epiradar" "$OUT/logcat-api$API.txt"; then
  echo "!! Ilova qulagan yoki javob bermagan"; grep -A30 "FATAL EXCEPTION" "$OUT/logcat-api$API.txt" | head -60; exit 1
fi
echo "== Emulyator tekshiruvi muvaffaqiyatli (API $API)"
