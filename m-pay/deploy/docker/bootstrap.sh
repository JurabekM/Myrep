#!/bin/sh
# Bir martalik tayyorgarlik konteyneri (2-faza P2.5, ADR-0020) — API va Shield instansiyalaridan oldin.
#
# 1. SoftHSM tokeni (bo'sh bo'lsa) — PIN Docker secret'dan, SO PIN tasodifiy va saqlanmaydi.
# 2. `mpay-server init --tls --keystore pkcs11` (holat hajmi bo'sh bo'lsa): kalitlar HSM'da,
#    sertifikatlar va konfiguratsiya `state` hajmida.
# 3. Konfiguratsiyani compose muhitiga moslash: PostgreSQL, PROXY protocol (faqat nginx IP'sidan),
#    metrikalar porti, Shield roli (mTLS), OTP virtual SMS shlyuzi orqali.
# 4. `mpay-server bootstrap`: DB migratsiyalari va barcha kalitlar (`ensure_key`) — bir marta.
#
# Yuk sinovi uchun (faqat sinov compose fayli): MPAY_LOAD_CARDS=N — `mpay-load prepare`, so'rovlar
# chegarasi o'chiriladi.
set -eu

STATE=/var/lib/mpay/state
CFG="$STATE/mpay.toml"
LB_IP="${MPAY_LB_IP:?MPAY_LB_IP kerak}"

mkdir -p "$(dirname "$SOFTHSM2_CONF")" /var/lib/mpay/hsm/tokens
[ -f "$SOFTHSM2_CONF" ] || echo "directories.tokendir = /var/lib/mpay/hsm/tokens" > "$SOFTHSM2_CONF"
if ! softhsm2-util --show-slots 2>/dev/null | grep -q "Label:.*$MPAY_PKCS11_TOKEN_LABEL"; then
  so_pin="$(openssl rand -hex 16)"
  softhsm2-util --init-token --free --label "$MPAY_PKCS11_TOKEN_LABEL" \
    --so-pin "$so_pin" --pin "$MPAY_PKCS11_PIN" >/dev/null
  unset so_pin
  echo "bootstrap: SoftHSM tokeni yaratildi ($MPAY_PKCS11_TOKEN_LABEL)"
fi

if [ ! -f "$CFG" ]; then
  mpay-server init --dir "$STATE" --listen 0.0.0.0:8443 --tls --keystore pkcs11 \
    --tls-san lb --tls-san api-1 --tls-san api-2 --tls-san shield >/dev/null
  # Konsolga chiqqan API kalitlari yuqorida yutildi; ular faqat state/dev-credentials.env da (sandbox).

  # PostgreSQL: parolli URL faqat muhitda (secret).
  sed -i 's|^path = "mpay.db"$|url_env = "MPAY_DATABASE_URL"|' "$CFG"
  # PROXY protocol: sarlavha faqat nginx'dan (statik IP) qabul qilinadi.
  sed -i "s|^trusted_proxies = \[\]$|trusted_proxies = [\"$LB_IP/32\"]|" "$CFG"
  sed -i 's|^proxy_protocol = false$|proxy_protocol = true|' "$CFG"
  # Metrikalar: ichki tarmoqda (Prometheus), host'ga ochilmaydi.
  sed -i 's|^# listen = "127.0.0.1:9464"$|listen = "0.0.0.0:9464"|' "$CFG"
  # OTP: virtual SMS shlyuzi (ichki tarmoq, shifrsiz — faqat izolyatsiyalangan sinov tarmog'i).
  sed -i 's|^channel = "sandbox"$|channel = "webhook"|' "$CFG"
  sed -i 's|^# \[otp.webhook\]$|[otp.webhook]|' "$CFG"
  sed -i 's|^# url = "http://127.0.0.1:47700/send"$|url = "http://smsgw:47700/send"\ninsecure_http = true|' "$CFG"
  sed -i 's|^# token_env = "MPAY_SMS_TOKEN"$|token_env = "MPAY_SMS_TOKEN"|' "$CFG"

  if [ -n "${MPAY_LOAD_CARDS:-}" ]; then
    mpay-load prepare --dir "$STATE" --cards "$MPAY_LOAD_CARDS"
    sed -i '/^\[rate_limit\]$/,/^enabled = /s/^enabled = true/enabled = false/' "$CFG"
  fi

  # Shield roli: o'sha konfiguratsiya, boshqa port; kirish — `shield` rolidagi kalit + mTLS.
  key_hash="$(printf '%s' "$MPAY_SHIELD_KEY" | sha256sum | cut -d' ' -f1)"
  sed 's|^listen = "0.0.0.0:8443"$|listen = "0.0.0.0:8600"|' "$CFG" > "$STATE/shield.toml"
  printf '\n[[auth.keys]]\nid = "api-shield"\nrole = "shield"\nsha256 = "%s"\n' "$key_hash" >> "$STATE/shield.toml"
  # Shield rolida PROXY protocol yo'q (to'g'ridan-to'g'ri ichki ulanishlar).
  sed -i 's|^proxy_protocol = true$|proxy_protocol = false|' "$STATE/shield.toml"

  # API instansiyalari Shield roliga murojaat qiladi.
  sed -i 's|^engine = "engine"$|engine = "engine"\nmode = "remote"|' "$CFG"
  cat >> "$CFG" <<EOF

[shield.remote]
url = "https://shield:8600"
key_env = "MPAY_SHIELD_KEY"
ca_file = "tls-cert.pem"
client_cert = "api-shield.crt.pem"
client_key = "api-shield.key.pem"
timeout_ms = 300
EOF
  echo "bootstrap: konfiguratsiya yaratildi ($CFG, $STATE/shield.toml)"
fi

mpay-server bootstrap --config "$CFG"
