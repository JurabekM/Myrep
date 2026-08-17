# -*- coding: utf-8 -*-
"""Wi-Fi boshqaruvi: ulanish, avtomatik qayta ulanish, AP fallback, NTP."""

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

import network
import time
import config
import logger

# network.STAT_* kodlari
_ERRS = {
    -3: "noto'g'ri parol (AUTH FAIL)",
    -2: "tarmoq topilmadi (NO AP FOUND)",
    -1: "ulanish muvaffaqiyatsiz (CONNECT FAIL)",
    0: "idle",
    1: "ulanmoqda",
}


class WiFi:
    def __init__(self):
        self.sta = network.WLAN(network.STA_IF)
        self.ap = None
        self.ap_mode = False
        self._fail_count = 0

    # -- holat ----------------------------------------------------------------
    def is_connected(self):
        return self.sta.isconnected()

    def ip(self):
        if self.ap_mode and self.ap:
            return self.ap.ifconfig()[0]
        return self.sta.ifconfig()[0] if self.sta.isconnected() else None

    def rssi(self):
        try:
            return self.sta.status("rssi")
        except Exception:
            return None

    def mac(self):
        m = self.sta.config("mac")
        return ":".join("%02x" % b for b in m)

    # -- ulanish --------------------------------------------------------------
    async def connect(self, timeout=None):
        timeout = timeout or config.WIFI_CONNECT_TIMEOUT

        if not config.WIFI_SSID:
            logger.warn("WIFI_SSID bo'sh — secrets.py ni to'ldiring")
            return False

        try:
            network.country(config.WIFI_COUNTRY)
        except Exception:
            pass

        self.sta.active(True)
        try:
            # DHCP so'rovida ko'rinadigan nom
            self.sta.config(hostname=config.WIFI_HOSTNAME)
        except Exception:
            pass
        # Wi-Fi quvvat tejash rejimi latency'ni oshiradi — o'chiramiz
        try:
            self.sta.config(pm=network.WLAN.PM_NONE)
        except Exception:
            pass

        if self.sta.isconnected():
            return True

        logger.info("Wi-Fi: '%s' ga ulanmoqda..." % config.WIFI_SSID)
        self.sta.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

        deadline = time.ticks_add(time.ticks_ms(), timeout * 1000)
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            st = self.sta.status()
            if st == network.STAT_GOT_IP:
                self._fail_count = 0
                logger.info("Wi-Fi OK  IP=%s  RSSI=%s dBm" % (self.ip(), self.rssi()))
                return True
            if st < 0:
                logger.error("Wi-Fi xato: %s" % _ERRS.get(st, st))
                break
            await asyncio.sleep_ms(250)

        self._fail_count += 1
        logger.warn("Wi-Fi ulanmadi (%d-urinish)" % self._fail_count)
        self.sta.disconnect()
        return False

    async def ensure(self):
        """Uzilgan bo'lsa backoff bilan qayta ulanadi."""
        if self.sta.isconnected():
            return True
        backoff = config.WIFI_RETRY_BACKOFF
        wait = backoff[min(self._fail_count, len(backoff) - 1)]
        ok = await self.connect()
        if not ok:
            logger.info("Wi-Fi: %d s dan keyin qayta urinish" % wait)
            await asyncio.sleep(wait)
        return ok

    # -- AP rejimi (sozlash uchun) -------------------------------------------
    def start_ap(self):
        if not config.AP_FALLBACK:
            return None
        self.sta.active(False)
        self.ap = network.WLAN(network.AP_IF)
        self.ap.config(essid=config.AP_SSID, password=config.AP_PASSWORD)
        self.ap.active(True)
        self.ap_mode = True
        logger.warn("AP rejimi: SSID=%s  IP=%s" % (config.AP_SSID, self.ap.ifconfig()[0]))
        return self.ap.ifconfig()[0]

    def stop_ap(self):
        if self.ap:
            self.ap.active(False)
        self.ap_mode = False


async def sync_time():
    """NTP orqali RTC ni sozlaydi. UTC saqlanadi, TZ faqat ko'rsatishda qo'llanadi."""
    if not config.NTP_SYNC:
        return False
    import ntptime
    ntptime.host = config.NTP_HOST
    for attempt in range(3):
        try:
            ntptime.settime()
            t = time.localtime(time.time() + config.TZ_OFFSET)
            logger.info("NTP OK: %04d-%02d-%02d %02d:%02d:%02d (mahalliy)"
                        % (t[0], t[1], t[2], t[3], t[4], t[5]))
            return True
        except Exception as e:
            logger.warn("NTP urinish %d muvaffaqiyatsiz: %r" % (attempt + 1, e))
            await asyncio.sleep(2)
    return False
