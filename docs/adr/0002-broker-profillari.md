# ADR 0002 — Broker profillari va public broker chegarasi

**Holat:** qabul qilingan · **Sana:** 2026-08-23

## Rasmiy manbadan tekshirilgan ma'lumot

`broker.hivemq.com` (mqtt-dashboard.com, 2026-08-23 da tekshirildi):

| Parametr | Qiymat |
|---|---|
| Host | `broker.hivemq.com` |
| TCP | `1883` |
| **TLS TCP** | **`8883`** |
| WebSocket | `8000` |
| TLS WebSocket | `8884` |
| Autentifikatsiya | talab qilinmaydi (anonim) |

## KRITIK: HiveMQ ning o'z shartlari

Rasmiy sahifa **so'zma-so'z** quyidagilarni aytadi:

* broker «Production, Dev, Staging or UAT» muhitlarida ishlatilishi **mumkin emas**;
* **maxfiy ma'lumot va shaxsiy ma'lumot uzatilmasin**;
* uptime kafolati **yo'q**, klientlar istalgan vaqtda uzilishi mumkin;
* yangilanish paytida **xabar yo'qolishi** mumkin;
* foydalanuvchi **ban** qilinishi mumkin;
* unumdorlik, kanal kengligi, kechikish bo'yicha **hech qanday kafolat yo'q**.

Bu topshiriqdagi qoidalarni shunchaki takrorlamaydi — undan **qattiqroq**.
Ya'ni: agar payload AETHER-Q bilan himoyalangan bo'lsa ham, HiveMQ ning o'z
shartlari bo'yicha bu broker haqiqiy mijoz ma'lumoti bilan ishlaydigan
tizimda ishlatilmaydi.

## Qaror

Ikki profil, kod o'zgartirmasdan almashadi (`DISTRIBOS_MQTT_PROFILE`):

### `PUBLIC_PILOT` (default)

```
MQTT_PROFILE=PUBLIC_PILOT
MQTT_HOST=broker.hivemq.com
MQTT_PORT=8883
MQTT_TLS_REQUIRED=true
MQTT_PROTOCOL=MQTT_5
MQTT_CLEAN_START=false
```

Majburiy cheklovlar, kodda **qulflanadi** (fail-closed):

1. `production_secure` bayrog'i **hech qachon** true bo'lolmaydi;
2. ishga tushganda foydalanuvchiga ogohlantirish ko'rsatiladi va u
   **tasdiqlanishi** shart (bir marta, sozlamada saqlanadi);
3. xabar hajmi qat'iy limit (`MQTT_MAX_PAYLOAD_BYTES`, default 256 KiB);
4. retained xabarlar **o'chirilgan** — hech qanday biznes ma'lumot retained
   bo'lib qolmaydi (ADR-0003);
5. `session_expiry` broker CONNACK'dagi haqiqiy qiymatdan olinadi, taxmin
   qilinmaydi — broker kamaytirsa biz shuni ishlatamiz.

### `PRIVATE_PRODUCTION`

Xususiy MQTT 5 broker: TLS, klient sertifikati yoki username/password, ACL,
tenant topic izolyatsiyasi, rate limiting. Kod bazasi **o'zgarmaydi** —
faqat konfiguratsiya.

## Fail-closed qoida (testda qulflangan)

`MQTT_HOST` `broker.hivemq.com` bo'lsa, profil avtomatik `PUBLIC_PILOT`
ga majburlanadi. Konfiguratsiyada `PRIVATE_PRODUCTION` yozilgan bo'lsa ham
— **ishga tushish rad etiladi**, jim tuzatilmaydi.

Buni `tests/security/test_broker_profile.py` qulflaydi.

## CI

CI testlari `broker.hivemq.com` ga **ulanmaydi**. Integratsion testlar
lokal konteynerli broker (Mosquitto/HiveMQ CE) ustida ishlaydi; konteyner
yo'q bo'lsa test `skip` bo'ladi, **soxta o'tmaydi**.
