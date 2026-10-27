#!/usr/bin/env sh
# Release smoke test (§5): R8 bilan minifikatsiya qilingan release APK'ni o'rnatadi (faqat CI uchun debug imzoli), ishga tushiradi va
# jarayon tirikligini va logcat'da fatal exception yo'qligini tekshiradi. Ishlab turgan emulator/qurilma kerak.
set -eu
cd "$(dirname "$0")/.."
./gradlew :app:assembleRelease -Psv.signWithDebug=true
APK=app/build/outputs/apk/release/app-release.apk
adb install -r "$APK"
adb logcat -c
adb shell am start -W -n uz.sectorverify/uz.sectorverify.app.MainActivity
sleep 8
PID=$(adb shell pidof uz.sectorverify || true)
if [ -z "$PID" ]; then echo "SMOKE: jarayon topilmadi (ilova yiqildi)"; adb logcat -d | tail -200; exit 1; fi
if adb logcat -d | grep -E "FATAL EXCEPTION|AndroidRuntime: Process: uz.sectorverify"; then echo "SMOKE: yiqilish"; exit 1; fi
echo "SMOKE: OK (pid $PID)"
