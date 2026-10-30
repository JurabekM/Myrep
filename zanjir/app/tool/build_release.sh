#!/usr/bin/env bash
# ZANJIR release AAB (12-faza, ADR-0016). Faqat foydalanuvchi kaliti bilan (`android/key.properties`, 3-darvoza) va
# barcha darvozalardan o'tgandan keyin. Play Console'ga yuklashni foydalanuvchi bajaradi.
#
#   app/tool/build_release.sh
#
# Tekshiruvlar (birortasi o'tmasa — to'xtaydi, chetlab o'tish parametri yo'q):
#   1. git ishchi daraxti toza; HEAD da `zanjir-v*` teg bo'lsa — pubspec versiyasiga teng
#   2. normalar release darvozasi (`check_norms.py --release`: reviewed_by/reviewed_at, needs_verification yo'q)
#   3. ilovadagi normalar nusxasi = `norms/` (asset testi), `flutter analyze`, `flutter test`
#   4. AAB'da INTERNET ruxsati yo'q — ilova to'liq oflayn (ADR-0017, `verify_aab.sh`)
# Natija: app/build/release/<versiya>/ — AAB, R8 mapping, Dart simbollari (maxfiy saqlanadi), SHA-256, hisobot.
set -euo pipefail

APP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$APP/.." && pwd)"
die() { echo "RELEASE TO'XTATILDI: $*" >&2; exit 1; }

[[ -f "$APP/android/key.properties" ]] || die "android/key.properties yo'q (3-darvoza, docs/RELEASE.md)"
store="$(grep -E '^storeFile=' "$APP/android/key.properties" | cut -d= -f2-)"
[[ -f "$store" ]] || die "keystore topilmadi: $store"

version="$(grep -E '^version: ' "$APP/pubspec.yaml" | cut -d' ' -f2)"
name="${version%+*}"; code="${version#*+}"
[[ "$name" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ && "$code" =~ ^[0-9]+$ ]] || die "pubspec version X.Y.Z+N bo'lishi kerak: $version"

cd "$ROOT"
[[ -z "$(git status --porcelain)" ]] || die "git ishchi daraxti toza emas"
tag="$(git tag --points-at HEAD | grep -E '^zanjir-v' | head -1 || true)"
[[ -z "$tag" || "$tag" == "zanjir-v$name" ]] || die "teg $tag ≠ pubspec $name"

echo "== normalar release darvozasi"
(cd "$ROOT/tools/norms" && uv run python -I check_norms.py --release ../../norms) || die "normalar tekshirilmagan (1-darvoza)"

echo "== analyze va testlar"
cd "$APP"
flutter analyze --fatal-infos
flutter test

echo "== AAB ($name+$code)"
OUT="$APP/build/release/$name+$code"
rm -rf "$OUT" && mkdir -p "$OUT"
flutter build appbundle --release --obfuscate --split-debug-info="$OUT/symbols"
aab="$OUT/zanjir-$name+$code.aab"
cp build/app/outputs/bundle/release/app-release.aab "$aab"
cp build/app/outputs/mapping/release/mapping.txt "$OUT/mapping.txt"
"$APP/tool/verify_aab.sh" "$aab" --version-code "$code" --version-name "$name" | tee "$OUT/report.txt"
(cd "$OUT/symbols" && tar czf "../dart-symbols-$name+$code.tar.gz" .) && rm -rf "$OUT/symbols"
{
  echo "versiya: $name+$code"
  echo "git: $(git -C "$ROOT" rev-parse HEAD)"
  echo "flutter: $(flutter --version --machine 2>/dev/null | grep -o '"frameworkVersion": *"[^"]*"' | cut -d'"' -f4)"
  (cd "$OUT" && sha256sum ./*.aab ./*.tar.gz mapping.txt)
} | tee "$OUT/release-info.txt"
echo
echo "TAYYOR: $aab — Play Console → Internal testing (docs/RELEASE.md). Simbollar va mapping maxfiy saqlanadi."
