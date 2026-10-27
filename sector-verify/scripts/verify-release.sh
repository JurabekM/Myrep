#!/usr/bin/env sh
# Imzolangan release artefaktini tekshiradi (H3, ADR-019): CI va Linux/macOS'da qo'lda ishlatiladi.
#   APK: v3 imzo, sertifikat SHA-256, versionName, targetSdk.   AAB: JAR imzo va sertifikat SHA-256.
#   minSdk 29 (≥ 28) da apksigner faqat v3 bilan imzolaydi — v1/v2 = false normal.
# Foydalanish: scripts/verify-release.sh <app-release.apk|app-release.aab> <kutilgan versionName> [kutilgan sertifikat SHA-256]
# Sertifikat barmoq izi keytool (AB:CD:…) yoki apksigner (abcd…) ko'rinishida berilishi mumkin.
set -eu

FILE=$1
WANT_VERSION=$2
WANT_CERT=$(printf '%s' "${3:-}" | tr -d ': ' | tr 'A-F' 'a-f')
TARGET_SDK=36

fail() { echo "VERIFY: $*" >&2; exit 1; }

SDK=${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}
if [ -z "$SDK" ] && [ -f local.properties ]; then SDK=$(sed -n 's/^sdk\.dir=//p' local.properties); fi
[ -n "$SDK" ] || fail "Android SDK topilmadi (ANDROID_HOME yoki local.properties sdk.dir)"
BT=$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)
[ -f "$FILE" ] || fail "fayl yo'q: $FILE"

check_cert() {
    [ -n "$WANT_CERT" ] || return 0
    [ "$1" = "$WANT_CERT" ] || fail "sertifikat SHA-256 mos emas: $1 (kutilgan $WANT_CERT)"
}

case "$FILE" in
    *.apk)
        OUT=$("$BT/apksigner" verify --verbose --print-certs "$FILE") || fail "apksigner: imzo yaroqsiz"
        echo "$OUT" | grep -q 'certificate DN: .*CN=Android Debug' && fail "debug kalit bilan imzolangan"
        echo "$OUT" | grep -q '(APK Signature Scheme v3): true' || fail "v3 imzo yo'q"
        CERT=$(echo "$OUT" | sed -n 's/^Signer #1 certificate SHA-256 digest: //p')
        check_cert "$CERT"
        BADGING=$("$BT/aapt2" dump badging "$FILE")
        VERSION=$(echo "$BADGING" | sed -n "s/^package:.* versionName='\([^']*\)'.*/\1/p")
        TARGET=$(echo "$BADGING" | sed -n "s/^targetSdkVersion:'\([0-9]*\)'.*/\1/p")
        [ "$VERSION" = "$WANT_VERSION" ] || fail "versionName '$VERSION' (kutilgan '$WANT_VERSION')"
        [ "$TARGET" = "$TARGET_SDK" ] || fail "targetSdk $TARGET (kutilgan $TARGET_SDK)"
        echo "VERIFY: OK $FILE · versiya $VERSION · targetSdk $TARGET · sertifikat $CERT"
        ;;
    *.aab)
        jarsigner -verify "$FILE" | grep -q '^jar verified\.' || fail "jarsigner: AAB imzosi yaroqsiz"
        CERT=$(keytool -printcert -jarfile "$FILE" | sed -n 's/^[[:space:]]*SHA256: //p' | head -1 | tr -d ': ' | tr 'A-F' 'a-f')
        [ -n "$CERT" ] || fail "AAB sertifikati o'qilmadi"
        check_cert "$CERT"
        echo "VERIFY: OK $FILE · sertifikat $CERT"
        ;;
    *) fail "faqat .apk yoki .aab" ;;
esac
