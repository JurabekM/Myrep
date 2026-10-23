#!/usr/bin/env bash
# SoftHSM2 (PKCS#11) integratsion testlarini Docker konteynerida ishga tushiradi.
# Windows'da SoftHSM2 yo'q (ADR-0003) — shuning uchun Linux konteyner.
#
#   bash scripts/softhsm-test.sh
#
# Token har safar yangidan yaratiladi, PIN tasodifiy va hech qayerga yozilmaydi.
# Cargo registry va target keshlari Docker volume'larida saqlanadi.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${MPAY_RUST_IMAGE:-rust:1.97.1-bookworm}"

# Git Bash yo'llarini Docker uchun o'zgartirishiga yo'l qo'ymaymiz.
export MSYS_NO_PATHCONV=1

docker run --rm \
  -v "$ROOT:/src:ro" \
  -v mpay-cargo-registry:/usr/local/cargo/registry \
  -v mpay-softhsm-target:/target \
  -e CARGO_TARGET_DIR=/target \
  -e MPAY_TEST_ARGS="${MPAY_TEST_ARGS:-}" \
  -w /src \
  "$IMAGE" bash -euo pipefail -c '
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null
    apt-get install -y -qq softhsm2 openssl >/dev/null
    softhsm2-util --version
    mkdir -p /tmp/softhsm/tokens
    echo "directories.tokendir = /tmp/softhsm/tokens" > /tmp/softhsm/softhsm2.conf
    export SOFTHSM2_CONF=/tmp/softhsm/softhsm2.conf
    export MPAY_PKCS11_PIN="$(openssl rand -hex 8)"
    softhsm2-util --init-token --free --label mpay-docker \
      --so-pin "$(openssl rand -hex 8)" --pin "$MPAY_PKCS11_PIN" >/dev/null
    export MPAY_PKCS11_LIB=/usr/lib/softhsm/libsofthsm2.so
    export MPAY_PKCS11_TOKEN_LABEL=mpay-docker
    cargo test --locked -p mpay-crypto --features pkcs11 -- --include-ignored pkcs11 ${MPAY_TEST_ARGS:-}
  '
