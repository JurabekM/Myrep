# esp32_aesgcm — ESP32 uchun AES-256-GCM

ESP32 da ma'lumotni haqiqiy shifrlash: maxfiylik va butunlik (paket o'zgartirilsa, rad etiladi).
ESP32 ichidagi mbedTLS ishlatiladi, qo'shimcha kutubxona kerak emas.

Paket formati: `nonce (12 bayt) | shifrmatn | teg (16 bayt)` — ochiq matndan 28 bayt uzun.

## Tarkibi

| Fayl | Vazifasi |
|---|---|
| `lib/aesgcm/aesgcm.h`, `aesgcm.c` | Modulning o'zi (C; Arduino-ESP32 da yig'ib tekshirilgan) |
| `src/main.cpp` | Demo: Serial'dan kelgan satrni shifrlaydi va qayta ochadi |
| `include/secrets.example.h` | Kalit namunasi — `secrets.h` deb nusxalanadi |
| `tools/aesgcm_peer.py` | PC/server tomoni: kalit yaratish, shifrlash, ochish |
| `tools/host_test.c` | Modul testlari (PC da, ESP32 siz) |

## Ishga tushirish (PlatformIO)

```bash
cp include/secrets.example.h include/secrets.h
```

```bash
python3 tools/aesgcm_peer.py keygen
```

Chiqqan baytlarni `include/secrets.h` dagi `AES_KEY` ga qo'ying, so'ng:

```bash
pio run -t upload
```

```bash
pio device monitor
```

Monitor'da matn yozib Enter bosing — paket hex ko'rinishda chiqadi.

**Arduino IDE:** `aesgcm.h`, `aesgcm.c`, `secrets.h` ni sketch papkasiga, `main.cpp` mazmunini `.ino` fayliga ko'chiring.

## O'z kodingizda ishlatish

```cpp
#include "aesgcm.h"

uint8_t packet[64 + AESGCM_OVERHEAD];
size_t packetLen;
const char *msg = "HARORAT=25.4";

int rc = aesgcm_encrypt(AES_KEY, (const uint8_t *)msg, strlen(msg),
                        (const uint8_t *)DEVICE_ID, strlen(DEVICE_ID),
                        packet, sizeof packet, &packetLen);
// rc == AESGCM_OK bo'lsa, packet[0..packetLen) ni yuboring (UART, MQTT, LoRa, BLE...)

uint8_t plain[64];
size_t plainLen;
rc = aesgcm_decrypt(AES_KEY, packet, packetLen,
                    (const uint8_t *)DEVICE_ID, strlen(DEVICE_ID),
                    plain, sizeof plain, &plainLen);
// rc == AESGCM_ERR_AUTH bo'lsa, paketni tashlab yuboring
```

Paket ikkilik ma'lumot: ichida `0x00` bo'lishi mumkin. Uzunlikni doim alohida olib yuring, matnli kanalda hex yoki Base64 ga o'giring.

## PC tomoni

```bash
pip install cryptography
```

```bash
python3 tools/aesgcm_peer.py decrypt --key <kalit_hex> --aad esp32-01 <paket_hex>
```

```bash
python3 tools/aesgcm_peer.py encrypt --key <kalit_hex> --aad esp32-01 "LED=1"
```

## Muhim

- **Kalit.** `secrets.h` git'ga tushmaydi, lekin kalit proshivka ichida ochiq yotadi: flash'ni o'qigan odam uni oladi. Jiddiy loyihada ESP32 **Flash Encryption** ni yoqing.
- **Tasodifiy sonlar.** Nonce `esp_fill_random` dan olinadi. WiFi/BLE o'chiq bo'lsa, u haqiqiy tasodifiy emas — shuning uchun demo `bootloader_random_enable()` ni chaqiradi. WiFi/BLE ishlatadigan loyihada bu chaqiruvni olib tashlang (radio yoqilgach generator o'zi to'g'ri ishlaydi).
- **Nonce takrorlanmasin.** Bitta kalit bilan bir xil nonce ikki marta ishlatilsa, GCM himoyasi butunlay yo'qoladi. Bitta kalit bilan 2^32 dan ortiq xabar shifrlamang.
- **Qayta yuborish (replay).** GCM eski paketni qayta yuborishdan himoyalamaydi. Kerak bo'lsa, xabarga hisoblagich qo'shing va qabul qiluvchida oxirgi qiymatdan kichigini rad eting.

## Testlar

`tools/host_test.c` — NIST test vektori, aylanma shifrlash, har baytda bit buzish, noto'g'ri kalit/AAD, bufer chegaralari. PC da mbedTLS o'rnatilgan bo'lsa:

```bash
cc -I lib/aesgcm tools/host_test.c lib/aesgcm/aesgcm.c -lmbedcrypto -o tools/host_test && tools/host_test
```

Demo proshivka yuklanganda ham NIST test vektorini qurilmaning o'zida tekshiradi (`O'z-o'zini tekshirish: o'tdi`).
