# Unumdorlik o'lchovi

Bu raqamlar **o'lchangan**, taxmin qilingan emas.
Qayta ishlab chiqarish: `python tools/benchmark.py`

* Sana: 2026-08-23 16:12
* Rejim: to`liq
* Python: 3.13.5
* Platforma: win32

| O'lchov | Median | 95-foiz | Namuna | Maqsad |
|---|---|---|---|---|
| Mahsulot qidiruvi (100,000 yozuvda) | 246.9 ms | 253.0 ms | 7 | ≤ 300 ms |
| Mahsulot ro'yxati (birinchi 500) | 148.9 ms | 151.2 ms | 7 | ≤ 300 ms |
| Shtrix-kod bo'yicha qidiruv | 20.9 ms | 21.2 ms | 7 | ≤ 100 ms |
| Buyurtmalar ro'yxati (50,000 yozuvda) | 410.5 ms | 412.6 ms | 7 | ≤ 300 ms |
| Anti-entropy digest (1,000,000 hodisada) | 94.1 ms | 105.7 ms | 7 | ≤ 300 ms |
| Yetishmagan oraliq (1,000,000 hodisada) | 1.4 ms | 1.5 ms | 7 | ≤ 300 ms |
| DES-1 muhrlash (1 KB payload) | 1.3 ms | 3.4 ms | 21 | ma'lumot uchun |
| DES-1 ochish + imzo tekshiruvi | 0.4 ms | 0.4 ms | 21 | ma'lumot uchun |
| Zaxira nusxa yaratish | 4,006.6 ms | 3,894.1 ms | 2 | ma'lumot uchun |

## OCHIQ SAVOL: buyurtmalar ro'yxati

«Buyurtmalar ro'yxati» o'lchovi shu stendda **~410 ms** beradi va
300 ms maqsadidan chiqadi. Lekin AYNAN o'sha so'rov, AYNAN o'sha
hajmda (100k mahsulot, 1M hodisa, 50k buyurtma) stenddan tashqarida
qayta o'lchanganda **~6 ms** chiqadi — takroran, har xil tartibda.

Profil vaqt `sqlite3.Cursor.execute` da ekanini ko'rsatadi, ya'ni
bu Python yoki ORM ustamasi emas. Farqning sababi topilmadi.

Bu raqam **yashirilmadi va "tuzatilmadi"**: o'lchov metodikasini
moslashtirib maqsadga sig'dirish — raqamni yaxshilash emas, uni
yashirish bo'lardi. Amaldagi ilovada bu ekran 300 tagacha qator
ko'rsatadi va qo'lda sinovda sezilarli kechikish kuzatilmadi.

**Keyingi qadam:** haqiqiy foydalanuvchi sharoitida (GUI, jonli baza)
o'lchash va kerak bo'lsa sahifalashga (pagination) o'tish.

## Izohlar

* **Mahsulot qidiruvi** `LIKE '%…%'` bilan ishlaydi. Indeks prefiks
  qidiruvida yordam beradi, o'rtadan qidirishda esa to'liq skan bo'ladi —
  agar bu chegaradan chiqsa, FTS5 ga o'tish kerak.
* **DES-1 muhrlash** vaqtining katta qismi ML-DSA-65 imzosiga ketadi.
  Shuning uchun hodisalar batch qilinadi (50 tagacha bitta imzo).
* **Anti-entropy digest** `GROUP BY device_id` — qurilmalar soni kam
  bo'lgani uchun hodisalar sonidan deyarli mustaqil.

Ishga tushish vaqti alohida o'lchanadi (`packaging/build_windows.py`
smoke testi): **1.1 s** (maqsad: 3 s dan kam).

