# -*- coding: utf-8 -*-
"""Sensorlar qatlami — BME280, DHT22 va RP2040 ichki harorat sensori.

Sensor topilmasa dastur qulamaydi: mavjud manbalardan o'qiydi.
"""

from machine import I2C, Pin, ADC
import time
import config
import logger

_ADC_CONV = 3.3 / 65535


class Sensors:
    def __init__(self):
        self.bme = None
        self.dht = None
        self.adc_core = ADC(4)          # RP2040 ichki harorat sensori
        self._last_read = 0
        self._cache = None

    def init(self):
        # --- BME280 ---
        try:
            i2c = I2C(config.I2C_ID, sda=Pin(config.PIN_SDA),
                      scl=Pin(config.PIN_SCL), freq=config.I2C_FREQ)
            devs = i2c.scan()
            logger.info("I2C skan: %s" % [hex(d) for d in devs])
            if devs:
                import bme280
                self.bme = bme280.BME280(i2c)
                logger.info("BME280 topildi @0x%02x (chip 0x%02x)"
                            % (self.bme.addr, self.bme.chip_id))
        except Exception as e:
            logger.warn("BME280 yo'q: %r" % e)

        # --- DHT22 (ixtiyoriy zaxira) ---
        if config.USE_DHT and self.bme is None:
            try:
                import dht
                self.dht = dht.DHT22(Pin(config.PIN_DHT))
                self.dht.measure()
                logger.info("DHT22 GP%d da topildi" % config.PIN_DHT)
            except Exception as e:
                logger.warn("DHT22 yo'q: %r" % e)
                self.dht = None

        if not self.bme and not self.dht:
            logger.warn("Tashqi sensor yo'q — faqat ichki harorat o'qiladi")

    def core_temp(self):
        """RP2040 kristal harorati (datasheet 4.9.5 formulasi)."""
        v = self.adc_core.read_u16() * _ADC_CONV
        return 27.0 - (v - 0.706) / 0.001721

    def read(self):
        """Barcha sensorlardan o'qib, dict qaytaradi. Xatolar yutiladi."""
        data = {"core_temp": round(self.core_temp(), 2)}

        if self.bme:
            try:
                t, p, h = self.bme.read()
                data["temperature"] = round(t, 2)
                if p is not None:
                    data["pressure"] = round(p, 2)
                    # dengiz sathiga keltirilgan bosim (taxminiy, 0 m uchun)
                    data["altitude"] = round(self.bme.altitude(), 1)
                if h is not None:
                    data["humidity"] = round(h, 2)
            except Exception as e:
                logger.error("BME280 o'qish xatosi: %r" % e)

        elif self.dht:
            try:
                self.dht.measure()
                data["temperature"] = round(self.dht.temperature(), 1)
                data["humidity"] = round(self.dht.humidity(), 1)
            except Exception as e:
                logger.error("DHT22 o'qish xatosi: %r" % e)

        if "temperature" in data and "humidity" in data:
            data["dew_point"] = round(dew_point(data["temperature"], data["humidity"]), 2)

        data["ts"] = time.time()
        self._cache = data
        self._last_read = time.ticks_ms()
        return data

    @property
    def last(self):
        return self._cache


def dew_point(t, rh):
    """Magnus-Tetens taqribi."""
    import math
    if rh <= 0:
        return float("-inf")
    a, b = 17.62, 243.12
    g = (a * t) / (b + t) + math.log(rh / 100.0)
    return (b * g) / (a - g)


# Har bir o'lchov uchun metama'lumot — HA discovery va web UI shu yerdan oladi
FIELDS = {
    "temperature": ("Harorat", "°C", "temperature", "mdi:thermometer"),
    "humidity": ("Namlik", "%", "humidity", "mdi:water-percent"),
    "pressure": ("Bosim", "hPa", "pressure", "mdi:gauge"),
    "dew_point": ("Shudring nuqtasi", "°C", "temperature", "mdi:weather-fog"),
    "altitude": ("Balandlik", "m", None, "mdi:image-filter-hdr"),
    "core_temp": ("Chip harorati", "°C", "temperature", "mdi:chip"),
    "rssi": ("Wi-Fi signal", "dBm", "signal_strength", "mdi:wifi"),
    "uptime": ("Ishlash vaqti", "s", "duration", "mdi:clock-outline"),
    "free_mem": ("Bo'sh RAM", "B", "data_size", "mdi:memory"),
}
