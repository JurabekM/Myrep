# syntax=docker/dockerfile:1.7
# Zaxira konteyneri (11-faza, ADR-0015): pg_dump 16 + age (ochiq kalit bilan shifrlash) + busybox crond.
ARG REGISTRY=docker.io/library
ARG POSTGRES_DIGEST=sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab
FROM ${REGISTRY}/postgres:16-alpine@${POSTGRES_DIGEST}
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -s /run/secrets/build_ca ]; then export SSL_CERT_FILE=/run/secrets/build_ca; fi; \
    apk add --no-cache age=~1
COPY backup.sh restore.sh entrypoint.sh /usr/local/bin/
RUN chmod 0755 /usr/local/bin/backup.sh /usr/local/bin/restore.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
