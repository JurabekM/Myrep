# -*- coding: utf-8 -*-
"""boot.py — main.py dan oldin ishlaydi.

Vazifasi:
  1. /lib ni sys.path ga qo'shish
  2. GP14 bosib turilgan bo'lsa — "xavfsiz rejim": main.py ishga tushmaydi
     (kod cheksiz reboot loop'ga tushib qolganda qutqaruvchi)
"""

import sys
import gc

if "/lib" not in sys.path:
    sys.path.insert(0, "/lib")

from machine import Pin
import time

# Xavfsiz rejim tekshiruvi
try:
    btn = Pin(14, Pin.IN, Pin.PULL_UP)
    time.sleep_ms(50)
    if btn.value() == 0:            # tugma bosilgan (GND ga tortilgan)
        led = Pin("LED", Pin.OUT)
        for _ in range(6):
            led.toggle()
            time.sleep_ms(120)
        led.off()
        print("!!! XAVFSIZ REJIM — main.py o'tkazib yuborildi")
        print("REPL ochiq. Davom etish uchun: import main")
        import sys as _s
        _s.exit()
except SystemExit:
    raise
except Exception as e:
    print("boot.py ogohlantirish:", e)

gc.collect()
print("boot.py OK — bo'sh RAM:", gc.mem_free())
