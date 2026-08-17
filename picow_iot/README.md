# Pico W IoT Sensor Node

Raspberry Pi Pico W uchun to'liq MicroPython IoT loyihasi: BME280 sensor →
Wi-Fi → MQTT (Home Assistant avtomatik discovery) + lokal web dashboard.

Tarmoq uzilganda o'lchovlar flash'ga yoziladi va ulanish tiklangach avtomatik
yuboriladi — bitta ham o'lchov yo'qolmaydi.

## Imkoniyatlar

| | |
|---|---|
| **Sensorlar** | BME280/BMP280 (I2C), DHT22 zaxira, RP2040 ichki harorat, shudring nuqtasi |
| **Tarmoq** | Wi-Fi avtomatik qayta ulanish (backoff), NTP, AP fallback |
| **MQTT** | To'liq async klient, QoS 0/1, LWT, keepalive, buyruq qabul qilish |
| **Home Assistant** | MQTT Discovery — qurilma o'zi paydo bo'ladi, sozlash shart emas |
| **Offline** | JSONL bufer, avtomatik qayta yuborish, hajm cheklovi |
| **Web UI** | Dark-tema dashboard + JSON API, brauzerdan boshqarish |
| **Ishonchlilik** | Watchdog, crash.log, xavfsiz rejim (GP14), holat LED'i |

Hammasi bitta `asyncio` event loop'da — hech bir qism boshqasini bloklamaydi.

## Ulanish sxemasi

```
BME280        Pico W
------        ------
VCC   ------  3V3 (pin 36)
GND   ------  GND (pin 38)
SDA   ------  GP4 (pin 6)
SCL   ------  GP5 (pin 7)

Tugma (ixtiyoriy):  GP14 (pin 19) <-> GND
```

BME280 I2C manzili odatda `0x76` (ba'zi modullarda `0x77`) — drayver ikkisini
ham avtomatik topadi.

## O'rnatish

**1. MicroPython proshivkasi.** [Rasmiy Pico W UF2](https://micropython.org/download/RPI_PICO_W/)
faylini yuklab oling. BOOTSEL tugmasini bosib turib USB ga ulang → `RPI-RP2`
diski paydo bo'ladi → `.uf2` ni ko'chiring.

> Diqqat: Pico W uchun **RPI_PICO_W** buildini oling, oddiy `RPI_PICO` emas —
> aks holda Wi-Fi va onboard LED ishlamaydi.

**2. Sozlamalar.**

```bash
copy secrets.py.example secrets.py
```

`secrets.py` da Wi-Fi va MQTT ma'lumotlaringizni yozing.

**3. Platani yuklash.**

```bash
pip install mpremote
```

```bash
powershell -ExecutionPolicy Bypass -File tools\deploy.ps1
```

Yoki qo'lda:

```bash
mpremote mkdir :lib
mpremote cp boot.py main.py config.py secrets.py :
mpremote cp lib/*.py :lib/
mpremote reset
```

## Ishlatish

Ishga tushgach REPL'da IP manzil chiqadi. Brauzerda oching:

```
http://<pico-ip>/
```

**Holat LED'i:**

| Namuna | Ma'nosi |
|---|---|
| 1 marta chaqnash (3 s da bir) | Hammasi joyida |
| 2 marta chaqnash | Wi-Fi bor, MQTT yo'q |
| Uzluksiz miltillash | Wi-Fi yo'q |

**MQTT topiclari:**

| Topic | Yo'nalish | Mazmun |
|---|---|---|
| `picow/<nom>/state` | chiqish | O'lchovlar (JSON) |
| `picow/<nom>/status` | chiqish | `online` / `offline` (LWT, retained) |
| `picow/<nom>/cmd` | kirish | Buyruqlar |

Buyruq yuborish:

```bash
mosquitto_pub -h 192.168.1.10 -t picow/picow-sensor-01/cmd -m '{"cmd":"set_interval","value":15}'
```

Qo'llab-quvvatlanadigan buyruqlar: `reboot`, `clear_buffer`, `resync`,
`publish_now`, `set_interval`.

## Home Assistant

`HA_DISCOVERY = True` bo'lsa boshqa hech narsa kerak emas — qurilma
**Settings → Devices** da o'zi paydo bo'ladi. HA'ning MQTT integratsiyasi
yoqilgan bo'lishi kifoya.

## Muammolarni hal qilish

**Cheksiz reboot loop.** GP14 ni GND ga ulang va qayta yoqing — `main.py`
ishga tushmaydi, REPL ochiq qoladi. Sabab uchun `crash.log` ni o'qing:

```bash
mpremote cat crash.log
```

**LED ishlamayapti.** Pico W da LED GP25 emas, CYW43 chipining WL_GPIO0 pinida.
Kodda `Pin("LED", Pin.OUT)` ishlatilgan — `Pin(25)` **ishlamaydi**.

**BME280 topilmadi.** I2C skanini tekshiring:

```bash
mpremote exec "from machine import I2C,Pin; print([hex(x) for x in I2C(0,sda=Pin(4),scl=Pin(5)).scan()])"
```

Bo'sh ro'yxat → simlar yoki tortuvchi rezistorlar muammosi.

**Xotira tugayapti.** `HISTORY_POINTS` va `BUFFER_MAX_RECORDS` ni kamaytiring.
`.py` fayllarni `.mpy` ga kompilyatsiya qilish ham ~40% RAM tejaydi:

```bash
mpy-cross lib/bme280.py
```

## Fayl tuzilishi

```
picow_iot/
├── boot.py              xavfsiz rejim, sys.path
├── main.py              orkestrator, 5 ta async vazifa
├── config.py            barcha sozlamalar
├── secrets.py           parollar (git'ga qo'shilmaydi)
└── lib/
    ├── wifi.py          ulanish, backoff, AP fallback, NTP
    ├── mqtt.py          async MQTT 3.1.1 klienti
    ├── bme280.py        BME280/BMP280 drayveri
    ├── sensors.py       sensor abstraksiyasi
    ├── buffer.py        offline JSONL bufer
    ├── ha_discovery.py  Home Assistant discovery
    ├── web.py           HTTP server + dashboard
    └── logger.py        loglar (RAM ring buffer bilan)
```

## Sinovdan o'tkazish

Kod apparatsiz, CPython'da sinaldi:

- MQTT paket kodlash — MQTT 3.1.1 spetsifikatsiyasining bayt-darajasidagi
  kutilgan natijalariga solishtirildi (varint chegara qiymatlari, CONNECT
  bayroqlari, PUBLISH/SUBSCRIBE/PUBACK)
- BME280 kompensatsiya — Bosch ma'lumotnomasidagi float algoritmning mustaqil
  implementatsiyasi bilan 6 ta holatda solishtirildi (farq < 0.005 °C / 0.001 hPa)
- Web server — haqiqiy TCP so'rovlar bilan (GET/POST/404/ketma-ket so'rovlar)
- Bufer, HA discovery payload'lari, shudring nuqtasi formulasi

## Litsenziya

MIT
