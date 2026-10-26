#!/usr/bin/env bash
# Zaxira nusxa (2-faza P2.5, ADR-0020): ishlab turgan compose muhitidan, to'xtatmasdan.
#
#   bash deploy/backup.sh [CHIQISH_PAPKASI]      # standart: deploy/backups/<UTC vaqt>/
#
# Tarkib:
#   mpay.dump        — PostgreSQL (`pg_dump -Fc`, bitta izchil snapshot). Karta ma'lumoti DB'da faqat
#                      KEK/DEK bilan shifrlangan — kalitlarsiz foydasiz.
#   state-hsm.tar.gz — konfiguratsiya holati va SoftHSM tokeni (PIN bilan himoyalangan).
#   SHA256SUMS
#
# Ehtiyot: `state` da sandbox sirlari bor (dev-credentials.env, mTLS kalitlari) — zaxira papkasi
# git'ga tushmaydi, lekin uni shifrlangan joyda saqlang.
# TODO(spec): zaxirani oflayn kalit bilan shifrlash (age/GPG) va bank HSM'ining o'z zaxira tartibi —
# production'da HSM kalitlari bu skript bilan nusxalanmaydi.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && (pwd -W 2>/dev/null || pwd))"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${1:-$HERE/backups}/$TS"
DC=(docker compose -f "$HERE/docker-compose.yml")
export MSYS_NO_PATHCONV=1
mkdir -p "$OUT"

echo "== PostgreSQL → $OUT/mpay.dump"
"${DC[@]}" exec -T postgres pg_dump -U mpay -d mpay -Fc > "$OUT/mpay.dump"
# Arxiv o'qiladimi (buzilgan dump'ni darhol aniqlash).
"${DC[@]}" exec -T postgres pg_restore --list < "$OUT/mpay.dump" > /dev/null

echo "== holat va HSM tokeni → $OUT/state-hsm.tar.gz"
"${DC[@]}" run --rm --no-deps -T --entrypoint tar bootstrap \
  -C /var/lib/mpay -czf - state hsm > "$OUT/state-hsm.tar.gz"

(cd "$OUT" && sha256sum mpay.dump state-hsm.tar.gz > SHA256SUMS)
echo "zaxira tayyor: $OUT"
du -h "$OUT"/* | sed 's/^/  /'
