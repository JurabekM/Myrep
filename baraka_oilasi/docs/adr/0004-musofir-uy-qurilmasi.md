# ADR-0004. Musofir: uydagi oila qurilmasi (M2)

- **Holat:** QABUL QILINDI (mahsulot egasining qarori, OQ-MF2: «oila ko'rmasin»)
- **Sana:** 2026-10-18
- **Bog'liq:** ADR-0003 (rollar — shu ADR uni kengaytiradi, o'zgartirmaydi), `docs/musofir/SPEC.md` 5, 8, `BARAKA_OILASI.md` 6.6, 8.3–8.5

## Kontekst
- «Ikki qirg'oq» (M2): musofir pul yuboradi, uydagi oila uni qabul qiladi va maqsad bo'yicha sarflaydi. Buning uchun oilaning qurilmasi musofir bilan bitta xonadon bazasini bo'lishadi (U14).
- Mahsulot egasi qarori: musofirning chet eldagi maoshi, xarajatlari, qaytish jamg'armasi, sozlamalari va kurslari **oilaga ko'rinmaydi**.
- U14 da barcha rolsiz qurilmalar hamma ma'lumotni oladi. Ekranni yashirish yetarli emas (ADR-0003, kontekst): ma'lumot qurilmada bo'lsa, o'qish mumkin.

## Qaror
1. **Yangi rol `HOME`** — «uydagi oila qurilmasi». ADR-0003 dagi kabi qurilmaga beriladi, egasining qurilmasi ulash taklifida beradi (`device_access`), bitta Musofir makoniga bog'lanadi (qaysi musofirning oilasi).
2. **Kamaytirilgan eksport.** `HOME` qurilmasiga xonadonning **hamma** yozuvlari boradi (Uy, Kasb-kor, kelishuvlar, jurnal), faqat **barcha Musofir makonlarining** shaxsiy yozuvlari bundan mustasno:
   - yuboriladi: makon yozuvi (`spaces`), uyga yuborilganlar (`mf_moves`, `SENT_HOME`; **komissiya 0 qilib**), ularning maqsadlarga bo'linishi, qabul va maqsad bo'yicha xarajat yozuvlari;
   - yuborilmaydi: maosh va boshqa daromad, chet eldagi xarajatlar va kategoriyalar, jamg'arma harakatlari va boshlang'ich qoldiqlar, sozlamalar (ish valyutasi, ulush, maqsad, qaytish sanasi), kurslar, «Ikki qirg'oq» shartlari jadvali va shu makondagi boshqa har qanday yozuv.
   - «Ikki qirg'oq» kelishuvining **matni** — Uy makonidagi oilaviy kelishuv (U13), oila uni ko'radi va tasdiqlaydi.
3. **Yozish filtri — egasining qurilmasida.** `HOME` dan kelgan faylda:
   - Musofir makonlaridagi yozuvlar: shu qurilma yaratgan **qabul** va **maqsad bo'yicha xarajat** — qabul qilinadi; boshqa jadval — rad etiladi (`ROLE_FORBIDDEN`); egasining o'z yozuvlari qaytib kelsa (kamaytirilgan nusxa) — e'tiborsiz.
   - Qolgan hamma yozuvlar (Uy va boshqalar) — oddiy qurilmadagi kabi birlashtiriladi (uch tomonlama, ziddiyat tanlovi); jurnal ham (hisob yurituvchi qoidasi 6.6 bilan).
   - `device_access` — rad etiladi (rolni faqat egasi yozadi).
4. **`HOME` qurilmasida:** Musofir makoni use-case'lari (`mf_*`, sozlash, kurs, yozuvlar) — `ROLE_FORBIDDEN`; uy tomoni use-case'lari (qabul, maqsad bo'yicha xarajat, maqsadlar qoldig'i) — ochiq. Yangi qurilma ulay olmaydi (ADR-0003, 7). Uy makonida hamma amal ochiq.
5. **Shart:** maxfiylik musofirning qurilmasi **egasi** (rolsiz) bo'lganda ishlaydi — rolni u beradi va filtrni u qo'llaydi. Xonadon uydagi qurilmada yaratilgan bo'lsa, musofir ma'lumoti u qurilmaga ham boradi; ilova buni ulash ekranida ochiq aytadi (OQ-MF6).

## Ko'rib chiqilgan muqobillar
| Variant | Nega tanlanmadi |
|---|---|
| Faqat UI'da yashirish | Ma'lumot oila qurilmasida qoladi — qarorga zid |
| Musofir makonini umuman sinxronlamaslik | Uy tomoniga yuborilgan pul va maqsadlar kerak; musofirning boshqa (o'z) qurilmalari ham ma'lumotni olishi kerak |
| `visibility = PRIVATE` ustuni bilan yozuv darajasida | Har bir jadvalga ustun va har use-case'da belgilash; filtr baribir qurilmaga bog'liq (kim ko'radi) — rol kerak |
| `HOME` rolini faqat bitta Musofir makoni bo'yicha filtrlash | Xonadonda ikki musofir bo'lsa, ikkinchisining ma'lumoti oilaga ketadi; barcha Musofir makonlari filtrlanadi |

## Oqibatlar
**Ijobiy**
- Oila qurilmasida musofirning shaxsiy ma'lumoti fizik jihatdan yo'q (test: eksport tarkibi va oila bazasi tekshiriladi).
- Uy makoni ikkala tomonda to'liq ishlaydi; U14 formati va birlashtirish dvigateli o'zgarmaydi.

**Salbiy va cheklovlar**
- Oila qurilmasi yangi qurilma ulay olmaydi; ikkinchi oila qurilmasini ham musofir ulaydi.
- Oila uyga yuborilgan summani ish valyutasida ko'radi (komissiyasiz) — qabul qilish uchun zarur.
- Xonadon egasi uydagi qurilma bo'lsa, maxfiylik ta'minlanmaydi (5-band).
