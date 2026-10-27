#!/usr/bin/env bash
# `TODO(spec):` belgilari va `docs/production-checklist.md` dagi belgilar indeksini solishtiradi:
#   * belgisi bor har fayl indeksda bo'lishi kerak (yangi ochiq savol ro'yxatdan chetda qolmasin);
#   * indeksdagi har faylda belgi qolgan bo'lishi kerak (yopilgan ish ro'yxatda osilib qolmasin).
#   bash scripts/check-todo-spec.sh
# Faqat git kuzatayotgan fayllar tekshiriladi (`git grep`).
set -euo pipefail
cd "$(dirname "$0")/.."

list=docs/production-checklist.md
self=scripts/check-todo-spec.sh

indexed=$(sed -n '/<!-- todo-index:start -->/,/<!-- todo-index:end -->/p' "$list" |
  sed -n 's/^\* `\([^`]*\)`.*/\1/p' | sort -u)
actual=$(git grep -l 'TODO(spec)' -- . ":!$list" ":!$self" | sort -u)

fail=0
for f in $(comm -23 <(echo "$actual") <(echo "$indexed")); do
  echo "indeksda yo'q (docs/production-checklist.md ga band qo'shing): $f" >&2
  fail=1
done
for f in $(comm -13 <(echo "$actual") <(echo "$indexed")); do
  echo "belgi qolmagan (indeksdan olib tashlang): $f" >&2
  fail=1
done

if [ "$fail" -ne 0 ]; then
  exit 1
fi
echo "TODO(spec): $(echo "$actual" | wc -l | tr -d ' ') fayl, hammasi indeksda"
