# DistribOS AI — administrator qo'llanmasi

## 1. Arxitektura, qisqacha

Markaziy server **yo'q**. Har qurilma to'liq huquqli tugun:

```
Desktop (SQLite)              Telefon (Room)
   │  outbox                     │  outbox
   │  AETHER-Q muhri             │  AETHER-Q muhri
   └──────── MQTT broker ────────┘
              (faqat transport)
```

Broker shifrlangan baytlarni tashiydi. U **ma'lumot ombori emas**: broker
tozalansa ham ma'lumot qurilmalarda qoladi va ular o'zaro tiklanadi.

---

## 2. Broker profillari

### `PUBLIC_PILOT` (sukut bo'yicha)

```
DISTRIBOS_MQTT_PROFILE=PUBLIC_PILOT
DISTRIBOS_MQTT_HOST=broker.hivemq.com
DISTRIBOS_MQTT_PORT=8883
```

Faqat **sinov va namoyish** uchun. HiveMQ o'z shartlarida bu brokerni
ishlab chiqarish muhitida ishlatishni man qiladi.

### `PRIVATE_PRODUCTION`

```
DISTRIBOS_MQTT_PROFILE=PRIVATE_PRODUCTION
DISTRIBOS_MQTT_HOST=mqtt.korxona.uz
DISTRIBOS_MQTT_PORT=8883
DISTRIBOS_MQTT_USERNAME=distribos
DISTRIBOS_MQTT_PASSWORD=...
DISTRIBOS_ENVIRONMENT=production
```

Talablar:

* MQTT **5** qo'llab-quvvatlashi;
* TLS (o'chirib bo'lmaydi — kod rad etadi);
* klient autentifikatsiyasi;
* ACL: har tenant faqat o'z topiklariga;
* rate limiting.

Broker o'rnini almashtirish uchun **kodni o'zgartirish kerak emas**.

> `broker.hivemq.com` bilan `PRIVATE_PRODUCTION` ni birga ishlatib
> bo'lmaydi — dastur ishga tushishni rad etadi.

---

## 3. Yangi qurilma qo'shish

1. Desktop → **Xavfsizlik** → «Yangi qurilma qo'shish».
2. Qurilma nomi va rolni tanlang.
3. QR kod chiqadi. U **10 daqiqa** amal qiladi va **bir marta** ishlaydi.
4. Telefonda QR ni skanerlang.
5. Desktop → **Xavfsizlik** da qurilma «Tasdiq kutmoqda» bo'lib turadi —
   uni tasdiqlang.

QR kodda **uzoq muddatli kalit yo'q** — faqat bir martalik taklif tegi.
Haqiqiy kalit himoyalangan sessiya ichida uzatiladi.

> ⚠ **Hozircha:** QR skanerlash ekrani Android tomonida tugallanmagan
> (`docs/HOLAT.md` §5.1). Protokol tayyor, ulash oqimi emas.

---

## 4. Rollar

| Rol | Nima qila oladi | Telefonga nima yuboriladi |
|---|---|---|
| Egasi | Hammasi | Hammasi |
| Rahbar | Narx, buyurtma, ombor, to'lov | Moliya bilan birga |
| Savdo agenti | Buyurtma, mijoz, to'lov, tashrif | Katalog, o'z mijozlari |
| Omborchi | Ombor harakati, buyurtma holati | Katalog, ombor |
| Kassir | To'lov | Mijoz, buyurtma, to'lov |
| Kuzatuvchi | Hech narsa yozmaydi | Faqat katalog |

Agentga **butun korxonaning moliyaviy bazasi yuborilmaydi**. Telefon
yo'qolsa, undagi zarar chegaralangan bo'ladi.

Vakolat tekshiruvi **fail-closed**: ro'yxatda bo'lmagan rol yoki amal
rad etiladi.

---

## 5. Qurilmani bekor qilish

Telefon yo'qolsa yoki xodim ishdan ketsa:

**Xavfsizlik** → qurilmani tanlang → «Qurilmani bekor qilish».

Shundan keyin o'sha qurilmadan kelgan **barcha** yozuvlar rad etiladi —
imzosi matematik jihatdan to'g'ri bo'lsa ham.

**Nimani bekor qilish HAL QILMAYDI:** qurilmadagi mavjud nusxa uning
qo'lida qoladi. Shuning uchun telefonga rolga mos ma'lumotgina beriladi.

Bekor qilingandan keyin **kalitlarni yangilash** tavsiya etiladi:
**Xavfsizlik** → «Kalitlarni yangilash».

---

## 6. Kalit rotatsiyasi

Yangi epoch ochiladi. Eski kalit **o'chirilmaydi** — uzoq vaqt ulanmagan
qurilma qaytganda uning eski yozuvlari baribir o'qilishi kerak.

Qachon qilish kerak:

* qurilma bekor qilingandan keyin;
* xodim ishdan ketganda;
* xavfsizlik siyosati talab qilsa (masalan chorakda bir marta).

---

## 7. Zaxira nusxa siyosati

Server yo'q, ya'ni nusxa **yagona himoya**.

Tavsiya:

| Nima | Qanchalik tez-tez | Qayerga |
|---|---|---|
| Nusxa yaratish | Har kuni | Lokal papka |
| Tashqi diskka ko'chirish | Haftasiga | Flesh yoki tashqi disk |
| **Nusxani tekshirish** | Oyiga | «Nusxani tekshirish» tugmasi |
| Tiklash mashqi | Choragiga | Sinov kompyuterida |

Nusxa paroli **parol menejerida** saqlansin. Uni yo'qotish — nusxani
yo'qotish demak.

Nusxa joylashuvi: `%LOCALAPPDATA%\DistribOS\backups`.

---

## 8. Diagnostika

**Sozlamalar** bo'limida: broker holati, sessiya muddati (brokerdan
olingan haqiqiy qiymat), protokol versiyasi, kalit avlodi, navbat va
xatolar soni, papkalar.

«Yordam to'plamini yaratish» — texnik holatni faylga yozadi. Unda
**maxfiy ma'lumot, kalit va mijoz ma'lumotlari yo'q**; foydalanuvchi
yuborishdan oldin ko'radi.

Jurnal: `%LOCALAPPDATA%\DistribOS\logs\distribos.log` (5 MB × 5 fayl).

### Yuborilmagan yozuvlar

**Sinxronizatsiya** → «Yuborilmaganlar» tab'i. Har birida sabab
ko'rsatiladi. «Xatolarni qayta urinish» ularni navbatga qaytaradi.

### Konfliktlar

**Tekshiruv navbati**. Bu yerdagi holatlar avtomatik hal qilinmagan —
odam qaror qabul qilishi kerak.

---

## 9. Tiklash tartibi

1. **Zaxira nusxa** → «Nusxadan tiklash».
2. Nusxani va parolni ko'rsating.
3. Dastur nusxani tekshiradi, keyin tiklaydi.
4. Eski baza `.replaced-<vaqt>` nomi bilan chetga olinadi — o'chirilmaydi.
5. Dasturni yopib qaytadan oching.
6. Boshqa qurilmalar bilan sinxronizatsiya avtomatik tiklanadi
   (dublikat yozuvlar ikkinchi marta qo'llanmaydi).

---

## 10. Nima qilib bo'lmaydi

* Ma'lumotlar bazasini qo'lda tahrirlash — audit va hodisa jurnali
  trigger bilan qulflangan.
* To'lov yoki ombor harakatini o'chirish — faqat teskari yozuv.
* Ochiq brokerni «production» deb belgilash.
* TLS'ni o'chirish.
* Reliz APK'ni imzo kalitisiz yig'ish.

Bularning har biri **ataylab** taqiqlangan va kod darajasida majburlanadi.
