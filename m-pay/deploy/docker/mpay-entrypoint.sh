#!/bin/sh
# M-Pay konteyner kirish nuqtasi (2-faza P2.5, ADR-0020).
#
# Sirlar muhit o'zgaruvchisida emas, fayl sifatida keladi (Docker secrets: /run/secrets/...):
# `MPAY_X_FILE=/run/secrets/x` bo'lsa `MPAY_X` shu fayl mazmuni bilan eksport qilinadi. Allaqachon
# berilgan `MPAY_X` ustun (masalan `docker compose exec -e MPAY_DATABASE_URL=...` bilan tiklash
# tekshiruvi). Qiymatlar hech qachon chop etilmaydi.
set -eu

for var in $(env | sed -n 's/^\(MPAY_[A-Z0-9_]*\)_FILE=.*/\1/p'); do
  file="$(printenv "${var}_FILE")"
  if [ -z "$(printenv "$var" 2>/dev/null || true)" ]; then
    if [ ! -r "$file" ]; then
      echo "mpay-entrypoint: ${var}_FILE o'qib bo'lmadi: $file" >&2
      exit 1
    fi
    value="$(cat "$file")"
    export "$var=$value"
  fi
  unset "${var}_FILE"
done

exec "$@"
