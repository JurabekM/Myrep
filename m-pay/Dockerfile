# syntax=docker/dockerfile:1.7
# M-Pay monolit binari (2-faza P2.5, ADR-0020). Bitta image: `mpay-server serve | shield | bootstrap`,
# virtual SMS shlyuzi `mpay-smsgw`. `loadgen` bosqichi — yuk generatori (faqat sinov).
#
#   docker build -t mpay-server .
#   docker build --target loadgen -t mpay-loadgen .

FROM rust:1.97.1-bookworm AS build
WORKDIR /src
COPY . .
# Kesh: cargo registry va target BuildKit hajmlarida (repo papkasiga yozilmaydi).
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/cargo-target \
    CARGO_TARGET_DIR=/cargo-target CARGO_INCREMENTAL=0 \
    cargo build --locked --release \
      -p mpay-server --features mpay-server/pkcs11 -p mpay-smsgw -p mpay-e2e \
      --bin mpay-server --bin mpay-smsgw --bin mpay-load \
 && mkdir /out \
 && cp /cargo-target/release/mpay-server /cargo-target/release/mpay-smsgw /cargo-target/release/mpay-load /out/

FROM debian:bookworm-slim AS runtime
RUN apt-get update \
 && apt-get install -y --no-install-recommends softhsm2 ca-certificates curl openssl age \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --system --uid 10001 --home-dir /var/lib/mpay --shell /usr/sbin/nologin mpay \
 && mkdir -p /var/lib/mpay/state /var/lib/mpay/hsm \
 && chown -R mpay:mpay /var/lib/mpay
COPY --from=build /out/mpay-server /out/mpay-smsgw /usr/local/bin/
COPY deploy/docker/mpay-entrypoint.sh /usr/local/bin/mpay-entrypoint
COPY deploy/docker/bootstrap.sh /usr/local/bin/mpay-bootstrap
RUN chmod 0755 /usr/local/bin/mpay-entrypoint /usr/local/bin/mpay-bootstrap
ENV SOFTHSM2_CONF=/var/lib/mpay/hsm/softhsm2.conf \
    MPAY_PKCS11_LIB=/usr/lib/softhsm/libsofthsm2.so \
    MPAY_PKCS11_TOKEN_LABEL=mpay \
    RUST_LOG=info
USER mpay
WORKDIR /var/lib/mpay
ENTRYPOINT ["mpay-entrypoint"]
CMD ["mpay-server", "serve", "--config", "/var/lib/mpay/state/mpay.toml"]

FROM runtime AS loadgen
COPY --from=build /out/mpay-load /usr/local/bin/
