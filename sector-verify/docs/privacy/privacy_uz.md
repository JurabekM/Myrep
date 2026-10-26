# Maxfiylik siyosati — Sector Verify

**Qisqasi: ilova hech qanday ma'lumot to'plamaydi va hech kimga yubormaydi.**

- **Joylashuv (GPS) va uyali tarmoq o'lchovlari** (RSRP, PCI, ARFCN, TA) faqat siz boshlagan o'lchov davomida yig'iladi
  va **faqat telefoningizda**, shifrlangan bazada (SQLCipher) saqlanadi. Fon rejimidagi joylashuv ishlatilmaydi.
- **SIM ma'lumoti** (MCC/MNC) faqat rejaga mos SIM'ni tanlash uchun o'qiladi; IMSI, telefon raqami, IMEI o'qilmaydi.
- **Tarmoq:** ilova faqat siz Sozlamalarda ko'rsatgan ixtiyoriy HTTPS manzilga bo'sh `HEAD` so'rov yuboradi (telefon tarmoqqa
  ulangan holda qolishi uchun). So'rovda hech qanday shaxsiy yoki o'lchov ma'lumoti yo'q.
- **Telemetriya, analitika, reklama, Firebase, Google Play Services — yo'q.**
- **Zaxira nusxa:** ilova ma'lumotlari bulutga yoki boshqa qurilmaga ko'chirilmaydi.
- **Ulashish:** PDF hisobot va sessiya ZIP faylini faqat siz «Ulashish» tugmasi bilan o'zingiz tanlagan joyga yuborasiz.
- **Crash log:** ilova yiqilsa, faqat xato izi (stack trace) telefonda saqlanadi; uni faqat siz eksport qilasiz.
- **O'chirish:** ilovani o'chirsangiz yoki uning ma'lumotlarini tozalasangiz, hamma narsa o'chadi.

Savollar: ilovani tarqatgan tashkilotning RF bo'limi.
