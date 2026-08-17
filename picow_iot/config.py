# -*- coding: utf-8 -*-
"""Loyiha sozlamalari.

Maxfiy ma'lumotlar (Wi-Fi paroli, MQTT paroli) `secrets.py` da saqlanadi.
`secrets.py.example` faylidan nusxa olib, `secrets.py` deb nomlang.
"""

try:
    import secrets
except ImportError:  # secrets.py hali yaratilmagan
    secrets = None


def _s(name, default=None):
    return getattr(secrets, name, default) if secrets else default


# --- Qurilma identifikatori ---------------------------------------------------
DEVICE_NAME = _s("DEVICE_NAME", "picow-sensor-01")
DEVICE_MODEL = "Raspberry Pi Pico W"
LOCATION = _s("LOCATION", "xona")

# --- Wi-Fi --------------------------------------------------------------------
WIFI_SSID = _s("WIFI_SSID", "")
WIFI_PASSWORD = _s("WIFI_PASSWORD", "")
WIFI_COUNTRY = "UZ"            # RF regulatsiya domeni
WIFI_HOSTNAME = DEVICE_NAME
WIFI_CONNECT_TIMEOUT = 20      # soniya
WIFI_RETRY_BACKOFF = (2, 5, 10, 30, 60)   # qayta ulanish kutish jadvali

# Wi-Fi topilmasa — o'z access point'ini ochib, sozlash sahifasini beradi
AP_FALLBACK = True
AP_SSID = DEVICE_NAME + "-setup"
AP_PASSWORD = "picowsetup"     # kamida 8 belgi

# --- MQTT ---------------------------------------------------------------------
MQTT_HOST = _s("MQTT_HOST", "192.168.1.10")
MQTT_PORT = _s("MQTT_PORT", 1883)
MQTT_USER = _s("MQTT_USER", None)
MQTT_PASSWORD = _s("MQTT_PASSWORD", None)
MQTT_SSL = _s("MQTT_SSL", False)
MQTT_KEEPALIVE = 60
MQTT_BASE_TOPIC = "picow/" + DEVICE_NAME

TOPIC_STATE = MQTT_BASE_TOPIC + "/state"       # sensor qiymatlari (JSON)
TOPIC_AVAIL = MQTT_BASE_TOPIC + "/status"      # online / offline (LWT)
TOPIC_CMD = MQTT_BASE_TOPIC + "/cmd"           # buyruqlar (reboot, interval, ...)

# Home Assistant MQTT Discovery
HA_DISCOVERY = True
HA_PREFIX = "homeassistant"

# --- O'lchash -----------------------------------------------------------------
SAMPLE_INTERVAL = 30           # sensorni necha soniyada bir o'qish
PUBLISH_INTERVAL = 60          # MQTT'ga necha soniyada bir yuborish

# --- Apparat pinlari ----------------------------------------------------------
I2C_ID = 0
PIN_SDA = 4                    # GP4
PIN_SCL = 5                    # GP5
I2C_FREQ = 400_000

PIN_DHT = 15                   # GP15 (DHT22 ixtiyoriy)
PIN_BUTTON = 14                # GP14 — bosib turilsa sozlamalar tozalanadi
USE_DHT = False                # BME280 bo'lmasa True qiling

# --- Offline buffer -----------------------------------------------------------
BUFFER_FILE = "buffer.jsonl"
BUFFER_MAX_RECORDS = 200       # 2 MB flash — ehtiyot bo'ling

# --- Web dashboard ------------------------------------------------------------
WEB_ENABLED = True
WEB_PORT = 80
HISTORY_POINTS = 60            # RAM'dagi grafik uchun nuqtalar soni

# --- Tizim --------------------------------------------------------------------
WDT_TIMEOUT = 8000             # ms (RP2040 maksimumi ~8.3 s)
NTP_SYNC = True
NTP_HOST = "pool.ntp.org"
TZ_OFFSET = 5 * 3600           # O'zbekiston UTC+5
LOG_LEVEL = "INFO"             # DEBUG | INFO | WARN | ERROR
