# ZANJIR — Normalarni tekshirish varag'i (ixtiyoriy; 1-darvoza olib tashlangan, ADR-0019)

> **Holat (2026-10-30):** foydalanuvchi qarori bilan muhandis imzosi **majburiy emas** (ADR-0019) — imzolash va release
> to'xtamaydi, protokol PDF'ida "muhandis tekshiruvidan o'tmagan" deb yoziladi. Varaq laboratoriya xohlasa tekshiruv uchun
> qoladi. **Kim to'ldiradi:** faqat haqiqiy tekshiruvchi (litsenziyali muhandis); Claude `reviewed_by` / `reviewed_at` ni
> **hech qachon** to'ldirmaydi (CLAUDE.md, 11-qoida).
>
> **Tekshiriladigan fayl:** `norms/v0.yaml`, versiya `0.3.0`. Quyidagi jadval shu fayldan generatsiya qilingan
> (2026-10-30). YAML o'zgarsa, jadval qayta generatsiya qilinadi va tekshiruv yangidan o'tkaziladi.

## 0.1.0 ko'rigi natijasi (mustaqil AI ko'rigi, 2026-10-30)

`0.1.0` bo'yicha **mustaqil AI ko'rigi** hisoboti olindi (foydalanuvchi ma'lumoti: hisobotni litsenziyali muhandis emas,
AI tayyorlagan; imzo bloki bo'sh). U faqat texnik kirish ma'lumoti — **litsenziyali muhandis tekshiruvi o'rnini bosmaydi**,
(keyinroq foydalanuvchi 1-darvozani butunlay olib tashladi — ADR-0019): `reviewed_by`/`reviewed_at` bo'sh, normalar
holati (`status`) o'zgartirilmadi.

AI ko'rigi xulosasi: **21 normaning va 3 `trip_multipliers` ning chegaraviy qiymatlari to'g'ri** — birorta qiymat
o'zgartirilmadi. AI ko'rigi bo'yicha `0.2.0` ga kiritilgan tuzatishlar (muhandis alohida tasdiqlashi yoki rad etishi kerak):

| O'zgarish | Normalar | Baholashga ta'siri |
|---|---|---|
| U0 = **220–230 V** (IEC 60038 / ГОСТ 29322; ГОСТ Р 50571.3-2009 jadval 41.1), javob M1 | `LOOP-TN-FINAL`, `EARTH-NEUTRAL-380`, `EARTH-REPEAT-380-TOTAL`, `EARTH-REPEAT-380-SINGLE` | U0 = 221–230 V obyektlar endi `NEEDS_REVIEW` emas: sirtmoq `Zs_max = k_corr · U0 / Ia` (230 V da 4,5 % kattaroq), yerga ulash 4 / 10 / 30 Ω |
| U0 = **380–400 V** → t ≤ 0,2 s; **401–1000 V** → t ≤ 0,1 s | `LOOP-TN-OTHER-U0-380`, `LOOP-TN-OTHER-U0-GT380` | faqat norma ID si o'zgaradi: `Ia = k · In` (oniy zona, t < 0,1 s) bo'lgani uchun `Zs_max` bir xil |
| Manba: ГОСТ IEC 61009-1 (RCBO) | `RCD-*` | yo'q (vaqt va tok qiymatlari bir xil) |
| Manba: ПТЭЭП 3-ilova, jadval 37; ПУЭ 1.8.39; ГОСТ IEC 60898-1 jadval 7 | izolyatsiya, `BOND-CONTACT`, `trip_multipliers` | yo'q (protokolda manba matni) |
| Izoh: "Sinusoidal (AC) sinov toki uchun" | `RCD-RAMP` | yo'q |

Diapazonlar orasidagi U0 (128–219, 231–379, 400 < U0 < 401 V) — normasi yo'q → `NEEDS_REVIEW` (golden testlar).

### Ochiq savollar (litsenziyali muhandis javobi kerak)

| # | Savol | Hozirgi xatti-harakat | Javob |
|---|---|---|---|
| K1 | **INS-SWGR (shitlar).** AI ko'rigining o'zi: yangi ishga tushirishda (ПУЭ 1.8.34) **≥ 1,0 MΩ**, ekspluatatsiyada (ПТЭЭП) ≥ 0,5 MΩ. Ilova normani sessiya turiga bog'lamaydi — `qabul-topshirish` sessiyasida ham 0,5 MΩ qo'llanadi, ya'ni 0,5–1,0 MΩ shit qabulda **PASS** chiqadi. Bundan tashqari, ПТЭЭП jadval 37 da ham shitlar uchun 1 MΩ ko'rsatilgan bo'lishi mumkin — rasmiy matndan tekshiring. Qaysi variant: (a) hamma sessiyada ≥ 1,0 MΩ (konservativ); (b) qabul-topshirishda 1,0, davriy/navbatdan tashqarida 0,5 (dasturga sessiya turi sharti qo'shiladi); (c) 0,5 qoladi (asos bilan)? | — | ✅ **1,0 MΩ** hamma sessiyada (foydalanuvchi qarori, 2026-10-30; normalar 0.3.0) |
| K2 | **ПУЭ jadval raqami.** AI ko'rigi jadval 1.8.34 ni kuch transformatorlariga tegishli deydi va 1.8.38 ni taklif qiladi. Bizning manbamizda (ПУЭ 7-nashr, 1.8-bob) jadval 1.8.34 — "≤ 1 kV apparatlar, ikkilamchi zanjirlar va elektr simlari izolyatsiyasining eng kichik qarshiligi", 1.8.37 ham shu jadvalga havola qiladi. Rasmiy matndan tekshirib, to'g'ri raqamni yozing. | 1.8.34 qoldirildi (`INS-WIRING`, `INS-SWGR`, `INS-SECONDARY`) | |
| K3 | **RCD-RAMP, UZO turi.** A turi UZO pulsatsiyalanuvchi tok bilan sinalganda chegaralar boshqacha (ГОСТ IEC 61008-1: 0,35–1,4·IΔn, tok burchagiga qarab). Ilova UZO turini (AC/A/B) va sinov to'lqin shaklini so'ramaydi — hamma o'lchov 0,5–1,0·IΔn bilan baholanadi (qat'iyroq: soz A turi FAIL chiqishi mumkin, xavfli PASS yo'q). Yetarlimi yoki tur/to'lqin shakli atributi qo'shilsinmi? | AC chegaralari hamma UZO uchun | |
| K4 | **Huquqiy asos.** Protokolda ПТЭЭП (2003) va ГОСТ Р 50571.3-2009 (Rossiya milliy standarti) chiqadi. O'zbekistonda aynan qaysi tahrir amalda (ПУЭ/ПТЭ ning O'zbekiston tahriri, O'z DSt, ГОСТ 29322-2014 qabul qilinganmi)? Rossiyada ПТЭЭП 2003 yangi qoidalar bilan almashtirilgan bo'lishi mumkin. | hisobotdagi manbalar | |
| K5 | **M10 matni.** AI ko'rigidagi tavsiya izohi ("…ПУЭ 1.7.79 ga muvofiq me'yoriy o'chish vaqti yuqorida o'rnatilgan soz UZO orqali ta'minlanadi") LEAD izohi uchun tayyor shablon sifatida qo'shilsinmi? Shart: shu UZO ning o'zi sinovdan o'tgan bo'lishi. | izohni LEAD o'zi yozadi | |

## Qanday tekshiriladi

1. Har bir qatorda qiymat, sinov kuchlanishi, qo'llanish sharti va manba bandini hujjatning amaldagi tahriri bilan solishtiring.
   "0.1.0 ko'rigi" ustuni — AI ko'rigidan keyin nima o'zgargani.
2. "Muhandis xulosasi" ustunida ☑ **tasdiq** yoki ☑ **tuzatish** belgilang (tuzatish bo'lsa — to'g'ri qiymat va band).
3. Yuqoridagi **ochiq savollar** (K1–K5) va pastdagi M1–M10 javoblarini tasdiqlang yoki tuzating.
4. Oxirida imzo bloki to'ldiriladi (F.I.Sh., guruh, guvohnoma, sana, imzo). Shundan keyin dasturchi:
   - tasdiqlangan normalarning `status` ini `source_seen` ga o'zgartiradi, tuzatishlarni kiritadi;
   - `reviewed_by` / `reviewed_at` ga **muhandis bergan** ma'lumotni yozadi;
   - `version` ni oshiradi; `check_norms.py --release` ogohlantirishlari yo'qolganini tekshiradi.

`reviewed_by`/`reviewed_at` bo'sh yoki `needs_verification` normalar bo'lsa — `check_norms.py --release` **ogohlantiradi**,
release build to'xtamaydi (ADR-0019; avval ADR-0004 bo'yicha yiqilardi). Protokol PDF'ida tekshiruv holati ko'rinadi.

## Normalar

| # | ID | Norma | Qiymat | Sinov kuchl. | Qo'llanish sharti | Manba | Holat | 0.1.0 ko'rigi | Muhandis xulosasi |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `INS-WIRING` | Elektr simlari izolyatsiyasi, ≤1 kV | ≥ 0.5 MOhm | 1000 V | CABLE; U0 0–1000 V; `circuit_class` ∈ ['wiring'] | ПУЭ 1.8.37, jadval 1.8.34; ПТЭЭП 3-ilova, jadval 37 | `source_seen` | tuzatish: ПТЭЭП qo'shildi; ПУЭ jadval raqami — ❓ K2 | ☐ tasdiq ☐ tuzatish: |
| 2 | `INS-SWGR` | Shitlar va taqsimlash qurilmalari (har seksiya) | ≥ 1.0 MOhm | 1000 V | PANEL, BUSBAR; U0 0–1000 V | ПУЭ jadval 1.8.34 — _Megaommetr 1000–2500 V; pastki chegara 1000 V olingan. 1,0 MOhm — qabul va ekspluatatsiya uchun bir xil (foydalanuvchi qarori K1, 2026-10-30, ADR-0019)_ | `needs_verification` | K1 → **1,0 MΩ** (foydalanuvchi qarori, 0.3.0) | ☐ tasdiq ☐ tuzatish: |
| 3 | `INS-SECONDARY` | Ikkilamchi zanjirlar | ≥ 1.0 MOhm | 1000 V | CABLE; `circuit_class` ∈ ['secondary'] | ПУЭ 1.8.37, jadval 1.8.34; ПТЭЭП 3-ilova, jadval 37 | `needs_verification` | tuzatish: ПТЭЭП qo'shildi; ❓ K2 | ☐ tasdiq ☐ tuzatish: |
| 4 | `INS-CABLE-LV` | Kuch kabellari, ≤1 kV | ≥ 0.5 MOhm | 2500 V | CABLE; U0 0–1000 V; `circuit_class` ∈ ['power'] | ПУЭ 1.8.40; ПТЭЭП 3-ilova, jadval 37 | `needs_verification` | tasdiq; ПТЭЭП qo'shildi | ☐ tasdiq ☐ tuzatish: |
| 5 | `LOOP-TN-FINAL` | TN, oxirgi zanjirlar, U0 = 220–230 V: t ≤ 0,4 s | t ≤ 400 ms | — | CABLE, SOCKET_GROUP, LOAD, BREAKER, RCBO, FUSE; TN-C/TN-S/TN-C-S; U0 220–230 V; `circuit_role` ∈ ['final'] | ПУЭ 1.7.79, jadval 1.7.1; ГОСТ Р 50571.3-2009, jadval 41.1 | `source_seen` | tuzatish kiritildi: U0 220–230 V (M1) | ☐ tasdiq ☐ tuzatish: |
| 6 | `LOOP-TN-DIST` | TN, taqsimlovchi zanjirlar: t ≤ 5 s | t ≤ 5000 ms | — | CABLE, PANEL, BUSBAR, BREAKER, RCBO, FUSE; TN-C/TN-S/TN-C-S; U0 0–1000 V; `circuit_role` ∈ ['distribution'] | ПУЭ 1.7.79 | `source_seen` | tasdiq | ☐ tasdiq ☐ tuzatish: |
| 7 | `LOOP-TN-OTHER-U0-127` | TN, oxirgi zanjirlar, U0 = 127 V: t ≤ 0,8 s | t ≤ 800 ms | — | CABLE, SOCKET_GROUP, LOAD, BREAKER, RCBO, FUSE; TN-C/TN-S/TN-C-S; U0 = 127 V; `circuit_role` ∈ ['final'] | ПУЭ jadval 1.7.1 | `needs_verification` | tasdiq | ☐ tasdiq ☐ tuzatish: |
| 8 | `LOOP-TN-OTHER-U0-380` | TN, oxirgi zanjirlar, U0 = 380–400 V: t ≤ 0,2 s | t ≤ 200 ms | — | CABLE, SOCKET_GROUP, LOAD, BREAKER, RCBO, FUSE; TN-C/TN-S/TN-C-S; U0 380–400 V; `circuit_role` ∈ ['final'] | ПУЭ jadval 1.7.1 | `needs_verification` | tuzatish kiritildi: U0 380–400 V | ☐ tasdiq ☐ tuzatish: |
| 9 | `LOOP-TN-OTHER-U0-GT380` | TN, oxirgi zanjirlar, U0 > 400 V: t ≤ 0,1 s | t ≤ 100 ms | — | CABLE, SOCKET_GROUP, LOAD, BREAKER, RCBO, FUSE; TN-C/TN-S/TN-C-S; U0 401–1000 V; `circuit_role` ∈ ['final'] | ПУЭ jadval 1.7.1 | `needs_verification` | tuzatish kiritildi: U0 401–1000 V | ☐ tasdiq ☐ tuzatish: |
| 10 | `RCD-1X` | Umumiy turdagi UZO, IΔn da: ≤ 300 ms | t ≤ 300 ms | — | RCD, RCBO; `selective` ∈ [False]; `multiplier` ∈ [1.0] | ГОСТ IEC 61008-1; ГОСТ IEC 61009-1 jadval 1 (o'chish vaqti) | `needs_verification` | tuzatish kiritildi: ГОСТ IEC 61009-1 | ☐ tasdiq ☐ tuzatish: |
| 11 | `RCD-1X-S` | Selektiv UZO, IΔn da: 130–500 ms | 130 ≤ x ≤ 500 ms | — | RCD, RCBO; `selective` ∈ [True]; `multiplier` ∈ [1.0] | ГОСТ IEC 61008-1; ГОСТ IEC 61009-1 jadval 1 (o'chish vaqti) | `needs_verification` | tuzatish kiritildi: ГОСТ IEC 61009-1 | ☐ tasdiq ☐ tuzatish: |
| 12 | `RCD-2X` | Umumiy turdagi UZO, 2·IΔn da: ≤ 150 ms | t ≤ 150 ms | — | RCD, RCBO; `selective` ∈ [False]; `multiplier` ∈ [2.0] | ГОСТ IEC 61008-1; ГОСТ IEC 61009-1 jadval 1 (o'chish vaqti) — _ADR-0002 S5 bo'yicha qo'shilgan_ | `needs_verification` | tuzatish kiritildi: ГОСТ IEC 61009-1 | ☐ tasdiq ☐ tuzatish: |
| 13 | `RCD-2X-S` | Selektiv UZO, 2·IΔn da: 60–200 ms | 60 ≤ x ≤ 200 ms | — | RCD, RCBO; `selective` ∈ [True]; `multiplier` ∈ [2.0] | ГОСТ IEC 61008-1; ГОСТ IEC 61009-1 jadval 1 (o'chish vaqti) — _ADR-0002 S5 bo'yicha qo'shilgan_ | `needs_verification` | tuzatish kiritildi: ГОСТ IEC 61009-1 | ☐ tasdiq ☐ tuzatish: |
| 14 | `RCD-5X` | Umumiy turdagi UZO, 5·IΔn da: ≤ 40 ms | t ≤ 40 ms | — | RCD, RCBO; `selective` ∈ [False]; `multiplier` ∈ [5.0] | ГОСТ IEC 61008-1; ГОСТ IEC 61009-1 jadval 1 (o'chish vaqti) | `needs_verification` | tuzatish kiritildi: ГОСТ IEC 61009-1 | ☐ tasdiq ☐ tuzatish: |
| 15 | `RCD-5X-S` | Selektiv UZO, 5·IΔn da: 50–150 ms | 50 ≤ x ≤ 150 ms | — | RCD, RCBO; `selective` ∈ [True]; `multiplier` ∈ [5.0] | ГОСТ IEC 61008-1; ГОСТ IEC 61009-1 jadval 1 (o'chish vaqti) — _ADR-0002 S5 bo'yicha qo'shilgan_ | `needs_verification` | tuzatish kiritildi: ГОСТ IEC 61009-1 | ☐ tasdiq ☐ tuzatish: |
| 16 | `RCD-RAMP` | Differensial o'chish toki: 0,5·IΔn < I ≤ IΔn | 0.5 · IΔn < x ≤ 1.0 · IΔn mA | — | RCD, RCBO; `multiplier` ∈ [1.0] | ГОСТ IEC 61008-1; ГОСТ IEC 61009-1 5.3.3-band (differensial o'chish toki) — _Sinusoidal (AC) sinov toki uchun_ | `needs_verification` | tuzatish kiritildi: 61009-1, AC izohi; ❓ K3 | ☐ tasdiq ☐ tuzatish: |
| 17 | `EARTH-NEUTRAL-380` | Neytral yerga ulash qurilmasi, 380/220 V (400/230 V): ≤ 4 Ω | ≤ 4.0 Ohm | — | EARTH_ELECTRODE; U0 220–230 V; `role` ∈ ['neutral'] | ПУЭ 1.7.101 — _Grunt solishtirma qarshiligi ρ > 100 Ω·m bo'lganda oshirish ruxsati qo'llanmagan (konservativ)_ | `needs_verification` | tuzatish kiritildi: U0 220–230 V | ☐ tasdiq ☐ tuzatish: |
| 18 | `EARTH-REPEAT-380-TOTAL` | Takroriy yerga ulash, 380/220 V (400/230 V), jami: ≤ 10 Ω | ≤ 10.0 Ohm | — | EARTH_ELECTRODE; U0 220–230 V; `role` ∈ ['repeat']; `scope` ∈ ['total'] | ПУЭ 1.7.103 — _ρ > 100 Ω·m bo'lganda oshirish ruxsati qo'llanmagan (konservativ)_ | `needs_verification` | tuzatish kiritildi: U0 220–230 V | ☐ tasdiq ☐ tuzatish: |
| 19 | `EARTH-REPEAT-380-SINGLE` | Takroriy yerga ulash, 380/220 V (400/230 V), har biri: ≤ 30 Ω | ≤ 30.0 Ohm | — | EARTH_ELECTRODE; U0 220–230 V; `role` ∈ ['repeat']; `scope` ∈ ['single'] | ПУЭ 1.7.103 — _ρ > 100 Ω·m bo'lganda oshirish ruxsati qo'llanmagan (konservativ)_ | `needs_verification` | tuzatish kiritildi: U0 220–230 V | ☐ tasdiq ☐ tuzatish: |
| 20 | `EARTH-TT` | TT tizimi: Ra · Ia ≤ 50 V (Ia — yuqoridagi UZO IΔn) | R · Ia ≤ 50.0 V | — | EARTH_ELECTRODE; TT; `role` ∈ ['tt'] | ПУЭ 1.7.59 | `needs_verification` | tasdiq | ☐ tasdiq ☐ tuzatish: |
| 21 | `BOND-CONTACT` | Ulanish (kontakt) qarshiligi: ≤ 0,05 Ω | ≤ 0.05 Ohm | — | PE_BAR, EARTH_ELECTRODE, PANEL, BUSBAR, CABLE, LOAD, SOCKET_GROUP | ПТЭЭП 3-ilova, 26-band; ПУЭ 1.8.39 | `source_seen` | tasdiq; ПУЭ 1.8.39 qo'shildi | ☐ tasdiq ☐ tuzatish: |

## Avtomat elektromagnit ajratgich koeffitsientlari (`trip_multipliers`)

Sirtmoq chegarasi: `Zs_max = k_corr · U0 / Ia`, `Ia = k · In` (ADR-0002, S2). Koeffitsientlar har bir egri chiziq uchun
**yuqori** chegara olingan (konservativ).

| Egri chiziq | k | Manba | Holat | 0.1.0 ko'rigi | Muhandis xulosasi |
|---|---|---|---|---|---|
| B | 5 | ПУЭ 1.7.79; ГОСТ IEC 60898-1, jadval 7 (B: 3–5·In) | `needs_verification` | tasdiq | ☐ tasdiq ☐ tuzatish: |
| C | 10 | ГОСТ IEC 60898-1, jadval 7 (C: 5–10·In) | `needs_verification` | tasdiq | ☐ tasdiq ☐ tuzatish: |
| D | 20 | ГОСТ IEC 60898-1, jadval 7 (D: 10–20·In) | `needs_verification` | tasdiq | ☐ tasdiq ☐ tuzatish: |

`margin_pct` = 0 (standart). `k_corr` — laboratoriya sozlamasi, (0; 1] oralig'ida, standart 1,0.

## Muhandis uchun savollar (M1–M10)

Ilova javob kelguncha **konservativ** ishlaydi (javob — NEEDS_REVIEW yoki qat'iyroq chegara). "Javob" — 0.1.0 AI ko'rigidan
(muhandis javobi emas); litsenziyali muhandis tasdiqlaydi yoki tuzatadi.

| # | Savol | Hozirgi xatti-harakat | AI ko'rigi javobi (2026-10-30) — muhandis tasdiqlashi kerak |
|---|---|---|---|
| M1 | U0 = 230 V bo'lgan obyektlar (IEC 60038) uchun qaysi sirtmoq normasi qo'llanadi? | 220–230 V → `LOOP-TN-FINAL` (0.2.0 da kiritildi) | `LOOP-TN-FINAL` (0,4 s) va `EARTH-*-380`; `u0_volts` 220–230 V |
| M2 | Grunt solishtirma qarshiligi ρ > 100 Ω·m bo'lganda (ПУЭ 1.7.101/1.7.103) yerga ulash normasini oshirishga ruxsat ilovada hisobga olinsinmi? | Hisobga olinmaydi (qat'iyroq) | Hisobga olinmasin: oshirish faqat ρ rasman o'lchanib hujjatlashtirilganda; `NEEDS_REVIEW` orqali bosh muhandis |
| M3 | INS-SWGR: megaommetr 1000–2500 V. Pastki chegara 1000 V olingan — to'g'rimi? | 1000 V dan past → NEEDS_REVIEW | To'g'ri (1000 V); 500 V megaommetr yetarli emas |
| M4 | INS-SECONDARY: sinov kuchlanishi 1000 V qilib olingan (jadvalda 500–1000 V bo'lishi mumkin). To'g'ri qiymat? | 1000 V dan past → NEEDS_REVIEW | 1000 V qolsin; ≤ 60 V zanjirlar 500 V bilan — `NEEDS_REVIEW` muhandisga kuchlanish sinfini tekshirtiradi |
| M5 | IΔn da sinov o'tkazilganda o'chish toki (RCD-RAMP) ham majburiymi? | Tok kiritilmasa → NEEDS_REVIEW | Ha, majburiy (ПТЭЭП 3-ilova, 28.7) |
| M6 | TT tizimi: Ia sifatida yerga ulagichga bog'langan barcha UZO'larning **eng kattasi** olinadi. To'g'rimi? | Eng katta IΔn (eng qat'iy) | To'g'ri (`Ia = max(IΔn)`) |
| M7 | Mavsumiy koeffitsient ψ < 1 kiritilsa, bu xato deb hisoblansinmi? | ψ < 1 → NEEDS_REVIEW | Ha, xato (ψ ≥ 1,0 bo'lishi shart); hozirgi `NEEDS_REVIEW` qabul qilinadi |
| M8 | Sirtmoq: Ia sifatida elektromagnit ajratgich zonasining yuqori chegarasi olinadi, 5 s normasi uchun ham. Taqsimlovchi zanjirlar uchun vaqt-tok xarakteristikasi bo'yicha yumshoqroq chegara kerakmi? | Oniy zona (qat'iyroq) | Oniy zona qolsin; Zs > Zs_max bo'lsa — pasport TCC bo'yicha qo'lda |
| M9 | Sirtmoq: faqat L–PE (TN-C da L–PEN) juftliklari baholanadi. L–N o'lchovlari uchun alohida norma kerakmi? | L–N → NEEDS_REVIEW | Alohida norma yo'q; L–N — qo'shimcha ma'lumot |
| M10 | Yuqorida UZO bo'lsa va Zs > Zs_max bo'lsa — NEEDS_REVIEW (ADR-0002 S3). Protokolda qanday xulosa yozilishi kerak? | NEEDS_REVIEW, LEAD izohi bilan imzolanadi | Hozirgi xatti-harakat to'g'ri; izoh namunasi — K5 |

## Imzo

| | |
|---|---|
| Muhandis F.I.Sh. | |
| Lavozimi, tashkilot | |
| Elektr xavfsizligi guruhi, guvohnoma raqami | |
| Laboratoriya akkreditatsiya/litsenziya raqami | |
| Tekshirilgan fayl va versiya | `norms/v0.yaml`, `0.3.0` |
| Sana | |
| Imzo | |
