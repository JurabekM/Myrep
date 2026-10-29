# `pg` — PostgreSQL yetakchisiga yo'naltiruvchi L4 proksi (ADR-0027): HAProxy + psql (rol tekshiruvi).
FROM haproxy:3.0.5-alpine
USER root
RUN apk add --no-cache postgresql16-client
COPY haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg
COPY pg-primary-check.sh /usr/local/bin/pg-primary-check
RUN chmod 0755 /usr/local/bin/pg-primary-check
USER haproxy
