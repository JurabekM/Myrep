# nginx yonidagi keepalived (ADR-0027): VRRP bilan umumiy virtual IP — nginx tushsa VIP ikkinchi lb'ga.
FROM alpine:3.20.3
RUN apk add --no-cache keepalived netcat-openbsd
COPY keepalived-entrypoint.sh /usr/local/bin/keepalived-entrypoint
RUN chmod 0755 /usr/local/bin/keepalived-entrypoint
ENTRYPOINT ["keepalived-entrypoint"]
