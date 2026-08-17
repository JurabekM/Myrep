# -*- coding: utf-8 -*-
"""BME280 / BMP280 drayveri (I2C), Bosch'ning butun sonli kompensatsiya formulalari.

BMP280 da namlik yo'q — u holda humidity None qaytadi.
"""

import time
from micropython import const

_REG_ID = const(0xD0)
_REG_RESET = const(0xE0)
_REG_CTRL_HUM = const(0xF2)
_REG_STATUS = const(0xF3)
_REG_CTRL_MEAS = const(0xF4)
_REG_CONFIG = const(0xF5)
_REG_DATA = const(0xF7)
_REG_CALIB1 = const(0x88)   # 26 bayt
_REG_CALIB2 = const(0xE1)   # 7 bayt

CHIP_BME280 = const(0x60)
CHIP_BMP280 = const(0x58)


def _s16(v):
    return v - 65536 if v > 32767 else v


def _s8(v):
    return v - 256 if v > 127 else v


class BME280:
    def __init__(self, i2c, addr=None):
        self.i2c = i2c
        if addr is None:
            found = i2c.scan()
            for a in (0x76, 0x77):
                if a in found:
                    addr = a
                    break
            if addr is None:
                raise OSError("BME280 I2C shinasida topilmadi (0x76/0x77)")
        self.addr = addr

        self.chip_id = self._r8(_REG_ID)
        if self.chip_id not in (CHIP_BME280, CHIP_BMP280):
            raise OSError("Kutilmagan chip ID: 0x%02x" % self.chip_id)
        self.has_humidity = self.chip_id == CHIP_BME280

        self._reset()
        self._load_calibration()
        self._configure()
        self.t_fine = 0

    # -- registr yordamchilari ------------------------------------------------
    def _r(self, reg, n):
        return self.i2c.readfrom_mem(self.addr, reg, n)

    def _r8(self, reg):
        return self._r(reg, 1)[0]

    def _w8(self, reg, val):
        self.i2c.writeto_mem(self.addr, reg, bytes([val]))

    def _reset(self):
        self._w8(_REG_RESET, 0xB6)
        time.sleep_ms(10)

    def _load_calibration(self):
        c = self._r(_REG_CALIB1, 26)

        def u16(i):
            return c[i] | (c[i + 1] << 8)

        self.dig_T1 = u16(0)
        self.dig_T2 = _s16(u16(2))
        self.dig_T3 = _s16(u16(4))
        self.dig_P1 = u16(6)
        self.dig_P2 = _s16(u16(8))
        self.dig_P3 = _s16(u16(10))
        self.dig_P4 = _s16(u16(12))
        self.dig_P5 = _s16(u16(14))
        self.dig_P6 = _s16(u16(16))
        self.dig_P7 = _s16(u16(18))
        self.dig_P8 = _s16(u16(20))
        self.dig_P9 = _s16(u16(22))

        if self.has_humidity:
            self.dig_H1 = c[25]
            h = self._r(_REG_CALIB2, 7)
            self.dig_H2 = _s16(h[0] | (h[1] << 8))
            self.dig_H3 = h[2]
            # H4/H5 — 12-bitli, 0xE5 baytini bo'lishadi
            self.dig_H4 = _s16(((h[3] << 4) | (h[4] & 0x0F)) << 4) >> 4
            self.dig_H5 = _s16(((h[5] << 4) | (h[4] >> 4)) << 4) >> 4
            self.dig_H6 = _s8(h[6])

    def _configure(self):
        # osrs_h = x1  (ctrl_hum ctrl_meas dan OLDIN yozilishi shart)
        if self.has_humidity:
            self._w8(_REG_CTRL_HUM, 0x01)
        # t_sb=500ms, filter=x4
        self._w8(_REG_CONFIG, (0x04 << 5) | (0x02 << 2))
        # osrs_t=x2, osrs_p=x16, mode=normal
        self._w8(_REG_CTRL_MEAS, (0x02 << 5) | (0x05 << 2) | 0x03)
        time.sleep_ms(100)

    # -- o'qish ---------------------------------------------------------------
    def read(self):
        """(temperature °C, pressure hPa, humidity %RH|None) qaytaradi."""
        d = self._r(_REG_DATA, 8)
        adc_p = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        adc_t = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)
        adc_h = (d[6] << 8) | d[7]

        # --- harorat (t_fine boshqa hisoblar uchun ham kerak) ---
        v1 = ((adc_t >> 3) - (self.dig_T1 << 1)) * self.dig_T2 >> 11
        v2 = (((((adc_t >> 4) - self.dig_T1)
                * ((adc_t >> 4) - self.dig_T1)) >> 12) * self.dig_T3) >> 14
        self.t_fine = v1 + v2
        temp = ((self.t_fine * 5 + 128) >> 8) / 100.0

        # --- bosim (64-bitli algoritm) ---
        v1 = self.t_fine - 128000
        v2 = v1 * v1 * self.dig_P6
        v2 += (v1 * self.dig_P5) << 17
        v2 += self.dig_P4 << 35
        v1 = ((v1 * v1 * self.dig_P3) >> 8) + ((v1 * self.dig_P2) << 12)
        v1 = (((1 << 47) + v1) * self.dig_P1) >> 33
        if v1 == 0:
            press = None
        else:
            p = 1048576 - adc_p
            p = (((p << 31) - v2) * 3125) // v1
            v1 = (self.dig_P9 * (p >> 13) * (p >> 13)) >> 25
            v2 = (self.dig_P8 * p) >> 19
            p = ((p + v1 + v2) >> 8) + (self.dig_P7 << 4)
            press = (p / 256.0) / 100.0        # Pa -> hPa

        # --- namlik ---
        hum = None
        if self.has_humidity:
            v = self.t_fine - 76800
            v = ((((adc_h << 14) - (self.dig_H4 << 20) - (self.dig_H5 * v)) + 16384) >> 15) * (
                (((((v * self.dig_H6) >> 10)
                   * (((v * self.dig_H3) >> 11) + 32768)) >> 10) + 2097152)
                * self.dig_H2 + 8192) >> 14
            v -= (((((v >> 15) * (v >> 15)) >> 7) * self.dig_H1) >> 4)
            v = min(max(v, 0), 419430400)
            hum = (v >> 12) / 1024.0

        return temp, press, hum

    def altitude(self, sea_level_hpa=1013.25):
        _, p, _ = self.read()
        if p is None:
            return None
        return 44330.0 * (1.0 - (p / sea_level_hpa) ** 0.1903)
