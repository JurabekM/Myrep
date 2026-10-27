#!/bin/sh
# keepalived (ADR-0027): nginx bilan bitta tarmoq nomlar fazosida (`network_mode: service:lb`).
# VRRP unicast (Docker ko'prigida multicast'ga tayanmaslik uchun), `nopreempt` — qaytgan lb VIP'ni
# tortib olmaydi (keraksiz almashinuv yo'q). nginx 8443 portda javob bermasa — VIP ikkinchisiga.
# Muhit: VIP, SELF_IP, PEER_IP, PRIORITY.
set -eu
: "${VIP:?}" "${SELF_IP:?}" "${PEER_IP:?}" "${PRIORITY:?}"
mkdir -p /etc/keepalived
cat > /etc/keepalived/keepalived.conf <<CONF
global_defs {
  enable_script_security
  script_user root
}
vrrp_script nginx_up {
  script "/usr/bin/nc -z 127.0.0.1 8443"
  interval 1
  fall 2
  rise 2
}
vrrp_instance mpay_lb {
  state BACKUP
  interface eth0
  virtual_router_id 51
  priority $PRIORITY
  advert_int 1
  nopreempt
  unicast_src_ip $SELF_IP
  unicast_peer {
    $PEER_IP
  }
  virtual_ipaddress {
    $VIP/24 dev eth0
  }
  track_script {
    nginx_up
  }
}
CONF
exec keepalived --dont-fork --log-console --log-detail
