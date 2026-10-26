#!/usr/bin/env sh
# Release smoke test (§5): installs the R8-minified release APK (debug-signed for CI only), launches it and
# checks that the process is alive and logcat has no fatal exception. Needs a running emulator/device.
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
