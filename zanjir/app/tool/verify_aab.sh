#!/usr/bin/env bash
# AAB tekshiruvi (12-faza, ADR-0016): imzo, manifest xavfsizlik sozlamalari, SDK, ruxsatlar, obfuskatsiya.
#   verify_aab.sh <fayl.aab> [--version-code N] [--version-name X.Y.Z] [--expect-cn "<sertifikat CN>"]
# Har band — ✅/❌; birorta ❌ bo'lsa chiqish kodi 1. Talab: JDK (jarsigner, keytool), ANDROID_HOME (build-tools, NDK).
set -euo pipefail

aab="${1:?AAB fayli}"; shift
code="" name="" cn=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --version-code) code="$2"; shift 2 ;;
    --version-name) name="$2"; shift 2 ;;
    --expect-cn) cn="$2"; shift 2 ;;
    *) echo "noma'lum parametr: $1" >&2; exit 2 ;;
  esac
done
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:?ANDROID_HOME kerak}}"
aapt2="$(find "$SDK/build-tools" -name aapt2 -type f | sort -V | tail -1)"
readelf="$(find "$SDK/ndk" -name llvm-readelf 2>/dev/null | sort -V | tail -1)"  # symlink ham bo'lishi mumkin
[[ -n "$aapt2" && -n "$readelf" ]] || { echo "aapt2 yoki llvm-readelf topilmadi (build-tools, NDK)" >&2; exit 2; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0
ok() { echo "✅ $*"; }
bad() { echo "❌ $*"; fail=1; }
check() { local msg="$1"; shift; if "$@"; then ok "$msg"; else bad "$msg"; fi; }

echo "AAB: $(basename "$aab") ($(wc -c < "$aab") bayt), sha256 $(sha256sum "$aab" | cut -d' ' -f1)"

# --- imzo ---
if jarsigner -verify "$aab" 2>/dev/null | grep -q "jar verified"; then ok "imzo to'g'ri (jarsigner)"; else bad "imzo"; fi
cert="$(keytool -printcert -jarfile "$aab" 2>/dev/null)"
owner="$(grep -m1 'Owner:' <<<"$cert" | sed 's/^ *Owner: //')"
echo "   sertifikat: $owner"
echo "   SHA-256: $(grep -m1 'SHA256:' <<<"$cert" | sed -E 's/^[[:space:]]*SHA256:[[:space:]]*//')"
check "debug sertifikat emas" bash -c '! grep -q "CN=Android Debug" <<<"$1"' _ "$owner"
[[ -z "$cn" ]] || check "sertifikat CN = $cn" bash -c 'grep -q "CN=$2" <<<"$1"' _ "$owner" "$cn"

# --- manifest ---
# aapt2 AAB ni o'qimaydi: proto manifest + resources.pb dan vaqtinchalik "proto APK".
mkdir -p "$TMP/p"
unzip -q -j -o "$aab" base/manifest/AndroidManifest.xml base/resources.pb -d "$TMP/p"
(cd "$TMP/p" && zip -q ../proto.apk AndroidManifest.xml resources.pb)
m="$("$aapt2" dump xmltree "$TMP/proto.apk" --file AndroidManifest.xml)"
has() { grep -qE "$1" <<<"$m"; }
check "package = uz.zanjir.app" has 'A: package="uz.zanjir.app"'
check "minSdk = 24" has 'minSdkVersion\(0x[0-9a-f]+\)=24'
check "targetSdk = 36" has 'targetSdkVersion\(0x[0-9a-f]+\)=36'
[[ -z "$code" ]] || check "versionCode = $code" has "versionCode\(0x[0-9a-f]+\)=$code\b"
[[ -z "$name" ]] || check "versionName = $name" has "versionName\(0x[0-9a-f]+\)=\"$name\""
check "debuggable yo'q" bash -c '! grep -qE "debuggable\(0x[0-9a-f]+\)=(true|0xffffffff)" <<<"$1"' _ "$m"
check "allowBackup = false" has 'allowBackup\(0x[0-9a-f]+\)=(false|0x0)'
check "usesCleartextTraffic = false" has 'usesCleartextTraffic\(0x[0-9a-f]+\)=(false|0x0)'
check "networkSecurityConfig bor" has 'networkSecurityConfig\(0x[0-9a-f]+\)=@'
# Har bir `uses-permission*` elementining nomi (formatidan qat'i nazar — hech biri o'tkazib yuborilmaydi).
perms="$(grep -A1 -E 'E: uses-permission' <<<"$m" | grep -oE 'android:name\(0x[0-9a-f]+\)="[^"]+"' \
  | sed -E 's/.*="([^"]+)"/\1/' | sort -u)"
nperm="$(grep -cE 'E: uses-permission' <<<"$m" || true)"
check "har bir ruxsat nomi o'qildi ($nperm)" test "$(grep -c . <<<"$perms")" -eq "$nperm"
echo "   ruxsatlar: $(tr '\n' ' ' <<<"$perms")"
# Ruxsat etilganlar: tarmoq va kutubxonalarning zararsiz ruxsatlari (AndroidX ilova ichidagi broadcast himoyasi).
allowed='^(android\.permission\.(INTERNET|ACCESS_NETWORK_STATE)|uz\.zanjir\.app\.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION)$'
extra="$(grep -vE "$allowed" <<<"$perms" || true)"
check "ruxsatlar faqat ruxsat etilgan ro'yxatdan${extra:+ (ortiqcha: $extra)}" test -z "$extra"

# --- obfuskatsiya ---
unzip -l "$aab" > "$TMP/list"
check "R8 mapping AAB ichida" grep -q "BUNDLE-METADATA/com.android.tools.build.obfuscation/proguard.map" "$TMP/list"
for abi in arm64-v8a armeabi-v7a x86_64; do
  check "libapp.so ($abi)" grep -q "base/lib/$abi/libapp.so" "$TMP/list"
done
unzip -q -o "$aab" base/lib/arm64-v8a/libapp.so -d "$TMP"
so="$TMP/base/lib/arm64-v8a/libapp.so"
check "libapp.so da DWARF yo'q (simbollar alohida)" bash -c '"$1" -S "$2" >/dev/null && ! "$1" -S "$2" | grep -q "\.debug_"' _ "$readelf" "$so"
check "Dart nomlari obfuskatsiya qilingan" bash -c '! grep -aqE "IsolationPlanRepository|ProtocolRepository|SyncEngine" "$1"' _ "$so"

echo
if [[ $fail -eq 0 ]]; then echo "AAB TEKSHIRUVI: OK"; else echo "AAB TEKSHIRUVI: XATO"; exit 1; fi
