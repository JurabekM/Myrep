# ADR 0003 — Broker ma'lumotlar ombori emas; retained taqiqlanadi

**Holat:** qabul qilingan · **Sana:** 2026-08-23

## Qaror

Biznes ma'lumot kanallarida (`events`, `acks`, `snapshot-chunks`,
`sync-responses`) MQTT **retained bayrog'i ishlatilmaydi**. Buni transport
qatlamining o'zi majburlaydi — publish API `retain` parametrini biznes
kanallar uchun qabul qilmaydi.

Istisno: `device-status` kanalida qurilma **presence** holati (online/offline,
oxirgi ko'rilgan vaqt) retained + QoS 0. Bu biznes ma'lumot emas, hajmi
qat'iy chegaralangan va DES-1 bilan muhrlangan.

## Nega

DistribOS Mesh loyihasida «retained-per-row» yondashuvi ishlatilgan edi —
har jadval qatori alohida retained xabar. Bu **ishlaydi**, lekin:

* broker de-fakto ma'lumotlar bazasiga aylanadi;
* `broker.hivemq.com` da bu HiveMQ shartlarini buzadi (maxfiy ma'lumot
  brokerda **saqlanadi**, faqat uzatilmaydi);
* broker tozalansa yoki ban bo'lsa — ma'lumot yo'qoladi;
* retained to'plami o'sib ketadi va uni kim tozalashi noaniq.

Yangi qurilma ma'lumotni **retained'dan emas**, tirik peer'dan
role-scoped snapshot orqali oladi (§11). Yo'qolgan hodisalar
anti-entropy digest almashuvi orqali tiklanadi (§10).

## Natija — nimaga TAYANMAYMIZ

* broker tarixi;
* MQTT session'ning saqlanishi;
* reconnect'da broker eski xabarlarni qaytarishi;
* broker ACK = biznes operatsiya qo'llandi.

MQTT 5 `Session Expiry` va `Message Expiry` **qulaylik** sifatida
ishlatiladi (tez reconnect'da qayta-yuborishni kamaytiradi), lekin
korrektlik ularga bog'liq emas: session butunlay yo'qolsa ham anti-entropy
bir xil yakuniy holatga olib keladi. Buni `tests/sync-chaos/` qulflaydi.
