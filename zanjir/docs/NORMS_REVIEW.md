# ZANJIR — Normalarni tekshirish varag'i (🛑 1-inson darvozasi)

> **Kim to'ldiradi:** faqat litsenziyali muhandis (elektr xavfsizligi bo'yicha guruhi V bo'lgan, elektrolaboratoriya
> rahbari yoki shunga teng). Claude `reviewed_by` / `reviewed_at` ni **hech qachon** to'ldirmaydi (CLAUDE.md, 11-qoida).
>
> **Tekshiriladigan fayl:** `norms/v0.yaml`, versiya `0.1.0`. Quyidagi jadval shu fayldan generatsiya qilingan
> (2026-10-26). YAML o'zgarsa, jadval qayta generatsiya qilinadi va tekshiruv yangidan o'tkaziladi.

## Qanday tekshiriladi

1. Har bir qatorda qiymat, sinov kuchlanishi, qo'llanish sharti va manba bandini hujjatning amaldagi tahriri bilan solishtiring.
2. "Muhandis xulosasi" ustunida ☑ **tasdiq** yoki ☑ **tuzatish** belgilang (tuzatish bo'lsa — to'g'ri qiymat va band).
3. Pastdagi **savollar** bo'limiga javob bering — ular baholash mantig'iga ta'sir qiladi.
4. Oxirida imzo bloki to'ldiriladi. Shundan keyin dasturchi:
   - tasdiqlangan normalarning `status` ini `source_seen` ga o'zgartiradi, tuzatishlarni kiritadi;
   - `reviewed_by` / `reviewed_at` ga **muhandis bergan** ma'lumotni yozadi;
   - `version` ni oshiradi va CI'dagi release darvozasi (`check_norms.py --release`) o'tishini tekshiradi.

Release darvozasi: `reviewed_by`/`reviewed_at` bo'sh bo'lsa **yoki** biror norma (`trip_multipliers` ham) `needs_verification`
holatida qolsa — release build yiqiladi (ADR-0004).

## Normalar

| # | ID | Norma | Qiymat | Sinov kuchl. | Qo'llanish sharti | Manba | Holat | Muhandis xulosasi |
|---|---|---|---|---|---|---|---|---|
| 1 | `INS-WIRING` | Elektr simlari izolyatsiyasi, ≤1 kV | ≥ 0.5 MOhm | 1000 V | CABLE; U0 0–1000 V; `circuit_class` ∈ ['wiring'] | ПУЭ 1.8.37, jadval 1.8.34 | `source_seen` | ☐ tasdiq ☐ tuzatish: |
| 2 | `INS-SWGR` | Shitlar va taqsimlash qurilmalari (har seksiya) | ≥ 0.5 MOhm | 1000 V | PANEL, BUSBAR; U0 0–1000 V | ПУЭ jadval 1.8.34 — _Megaommetr 1000–2500 V; pastki chegara 1000 V olingan_ | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 3 | `INS-SECONDARY` | Ikkilamchi zanjirlar | ≥ 1.0 MOhm | 1000 V | CABLE; `circuit_class` ∈ ['secondary'] | ПУЭ jadval 1.8.34 | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 4 | `INS-CABLE-LV` | Kuch kabellari, ≤1 kV | ≥ 0.5 MOhm | 2500 V | CABLE; U0 0–1000 V; `circuit_class` ∈ ['power'] | ПУЭ 1.8.40 | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 5 | `LOOP-TN-FINAL` | TN, oxirgi zanjirlar, U0 = 220 V: t ≤ 0,4 s | t ≤ 400 ms | — | CABLE, SOCKET_GROUP, LOAD, BREAKER, RCBO, FUSE; TN-C/TN-S/TN-C-S; U0 = 220 V; `circuit_role` ∈ ['final'] | ПУЭ 1.7.79, jadval 1.7.1 | `source_seen` | ☐ tasdiq ☐ tuzatish: |
| 6 | `LOOP-TN-DIST` | TN, taqsimlovchi zanjirlar: t ≤ 5 s | t ≤ 5000 ms | — | CABLE, PANEL, BUSBAR, BREAKER, RCBO, FUSE; TN-C/TN-S/TN-C-S; U0 0–1000 V; `circuit_role` ∈ ['distribution'] | ПУЭ 1.7.79 | `source_seen` | ☐ tasdiq ☐ tuzatish: |
| 7 | `LOOP-TN-OTHER-U0-127` | TN, oxirgi zanjirlar, U0 = 127 V: t ≤ 0,8 s | t ≤ 800 ms | — | CABLE, SOCKET_GROUP, LOAD, BREAKER, RCBO, FUSE; TN-C/TN-S/TN-C-S; U0 = 127 V; `circuit_role` ∈ ['final'] | ПУЭ jadval 1.7.1 | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 8 | `LOOP-TN-OTHER-U0-380` | TN, oxirgi zanjirlar, U0 = 380 V: t ≤ 0,2 s | t ≤ 200 ms | — | CABLE, SOCKET_GROUP, LOAD, BREAKER, RCBO, FUSE; TN-C/TN-S/TN-C-S; U0 = 380 V; `circuit_role` ∈ ['final'] | ПУЭ jadval 1.7.1 | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 9 | `LOOP-TN-OTHER-U0-GT380` | TN, oxirgi zanjirlar, U0 > 380 V: t ≤ 0,1 s | t ≤ 100 ms | — | CABLE, SOCKET_GROUP, LOAD, BREAKER, RCBO, FUSE; TN-C/TN-S/TN-C-S; U0 381–1000 V; `circuit_role` ∈ ['final'] | ПУЭ jadval 1.7.1 | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 10 | `RCD-1X` | Umumiy turdagi UZO, IΔn da: ≤ 300 ms | t ≤ 300 ms | — | RCD, RCBO; `selective` ∈ [False]; `multiplier` ∈ [1.0] | ГОСТ IEC 61008-1 o'chish vaqti jadvali | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 11 | `RCD-1X-S` | Selektiv UZO, IΔn da: 130–500 ms | 130 ≤ x ≤ 500 ms | — | RCD, RCBO; `selective` ∈ [True]; `multiplier` ∈ [1.0] | ГОСТ IEC 61008-1 o'chish vaqti jadvali | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 12 | `RCD-2X` | Umumiy turdagi UZO, 2·IΔn da: ≤ 150 ms | t ≤ 150 ms | — | RCD, RCBO; `selective` ∈ [False]; `multiplier` ∈ [2.0] | ГОСТ IEC 61008-1 o'chish vaqti jadvali — _ADR-0002 S5 bo'yicha qo'shilgan_ | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 13 | `RCD-2X-S` | Selektiv UZO, 2·IΔn da: 60–200 ms | 60 ≤ x ≤ 200 ms | — | RCD, RCBO; `selective` ∈ [True]; `multiplier` ∈ [2.0] | ГОСТ IEC 61008-1 o'chish vaqti jadvali — _ADR-0002 S5 bo'yicha qo'shilgan_ | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 14 | `RCD-5X` | Umumiy turdagi UZO, 5·IΔn da: ≤ 40 ms | t ≤ 40 ms | — | RCD, RCBO; `selective` ∈ [False]; `multiplier` ∈ [5.0] | ГОСТ IEC 61008-1 o'chish vaqti jadvali | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 15 | `RCD-5X-S` | Selektiv UZO, 5·IΔn da: 50–150 ms | 50 ≤ x ≤ 150 ms | — | RCD, RCBO; `selective` ∈ [True]; `multiplier` ∈ [5.0] | ГОСТ IEC 61008-1 o'chish vaqti jadvali — _ADR-0002 S5 bo'yicha qo'shilgan_ | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 16 | `RCD-RAMP` | Differensial o'chish toki: 0,5·IΔn < I ≤ IΔn | 0.5 · IΔn < x ≤ 1.0 · IΔn mA | — | RCD, RCBO; `multiplier` ∈ [1.0] | ГОСТ IEC 61008-1 differensial o'chish toki | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 17 | `EARTH-NEUTRAL-380` | Neytral yerga ulash qurilmasi, 380/220 V: ≤ 4 Ω | ≤ 4.0 Ohm | — | EARTH_ELECTRODE; U0 = 220 V; `role` ∈ ['neutral'] | ПУЭ 1.7.101 — _Grunt solishtirma qarshiligi ρ > 100 Ω·m bo'lganda oshirish ruxsati qo'llanmagan (konservativ)_ | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 18 | `EARTH-REPEAT-380-TOTAL` | Takroriy yerga ulash, 380/220 V, jami: ≤ 10 Ω | ≤ 10.0 Ohm | — | EARTH_ELECTRODE; U0 = 220 V; `role` ∈ ['repeat']; `scope` ∈ ['total'] | ПУЭ 1.7.103 — _ρ > 100 Ω·m bo'lganda oshirish ruxsati qo'llanmagan (konservativ)_ | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 19 | `EARTH-REPEAT-380-SINGLE` | Takroriy yerga ulash, 380/220 V, har biri: ≤ 30 Ω | ≤ 30.0 Ohm | — | EARTH_ELECTRODE; U0 = 220 V; `role` ∈ ['repeat']; `scope` ∈ ['single'] | ПУЭ 1.7.103 — _ρ > 100 Ω·m bo'lganda oshirish ruxsati qo'llanmagan (konservativ)_ | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 20 | `EARTH-TT` | TT tizimi: Ra · Ia ≤ 50 V (Ia — yuqoridagi UZO IΔn) | R · Ia ≤ 50.0 V | — | EARTH_ELECTRODE; TT; `role` ∈ ['tt'] | ПУЭ 1.7.59 | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| 21 | `BOND-CONTACT` | Ulanish (kontakt) qarshiligi: ≤ 0,05 Ω | ≤ 0.05 Ohm | — | PE_BAR, EARTH_ELECTRODE, PANEL, BUSBAR, CABLE, LOAD, SOCKET_GROUP | ПТЭЭП 3-ilova, 26-band | `source_seen` | ☐ tasdiq ☐ tuzatish: |

## Avtomat elektromagnit ajratgich koeffitsientlari (`trip_multipliers`)

Sirtmoq chegarasi: `Zs_max = k_corr · U0 / Ia`, `Ia = k · In` (ADR-0002, S2). Koeffitsientlar har bir egri chiziq uchun
**yuqori** chegara olingan (konservativ).

| Egri chiziq | k | Manba | Holat | Muhandis xulosasi |
|---|---|---|---|---|
| B | 5 | ПУЭ 1.7.79; ГОСТ IEC 60898-1 (B: 3–5·In) | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| C | 10 | ГОСТ IEC 60898-1 (C: 5–10·In) | `needs_verification` | ☐ tasdiq ☐ tuzatish: |
| D | 20 | ГОСТ IEC 60898-1 (D: 10–20·In) | `needs_verification` | ☐ tasdiq ☐ tuzatish: |

`margin_pct` = 0 (standart). `k_corr` — laboratoriya sozlamasi, (0; 1] oralig'ida, standart 1,0.

## Muhandis uchun savollar

Ilova bu savollarga javob kelguncha **konservativ** ishlaydi (javob — NEEDS_REVIEW yoki qat'iyroq chegara).

| # | Savol | Hozirgi xatti-harakat | Javob |
|---|---|---|---|
| M1 | U0 = 230 V bo'lgan obyektlar (IEC 60038) uchun qaysi sirtmoq normasi qo'llanadi? | 220 V dan boshqa U0 → normasi yo'q → NEEDS_REVIEW | |
| M2 | Grunt solishtirma qarshiligi ρ > 100 Ω·m bo'lganda (ПУЭ 1.7.101/1.7.103) yerga ulash normasini oshirishga ruxsat ilovada hisobga olinsinmi? | Hisobga olinmaydi (qat'iyroq) | |
| M3 | INS-SWGR: megaommetr 1000–2500 V. Pastki chegara 1000 V olingan — to'g'rimi? | 1000 V dan past → NEEDS_REVIEW | |
| M4 | INS-SECONDARY: sinov kuchlanishi 1000 V qilib olingan (jadvalda 500–1000 V bo'lishi mumkin). To'g'ri qiymat? | 1000 V dan past → NEEDS_REVIEW | |
| M5 | IΔn da sinov o'tkazilganda o'chish toki (RCD-RAMP) ham majburiymi? | Tok kiritilmasa → NEEDS_REVIEW | |
| M6 | TT tizimi: Ia sifatida yerga ulagichga bog'langan barcha UZO'larning **eng kattasi** olinadi. To'g'rimi? | Eng katta IΔn (eng qat'iy) | |
| M7 | Mavsumiy koeffitsient ψ < 1 kiritilsa, bu xato deb hisoblansinmi? | ψ < 1 → NEEDS_REVIEW | |
| M8 | Sirtmoq: Ia sifatida elektromagnit ajratgich zonasining yuqori chegarasi olinadi, 5 s normasi uchun ham. Taqsimlovchi zanjirlar uchun vaqt-tok xarakteristikasi bo'yicha yumshoqroq chegara kerakmi? | Oniy zona (qat'iyroq) | |
| M9 | Sirtmoq: faqat L–PE (TN-C da L–PEN) juftliklari baholanadi. L–N o'lchovlari uchun alohida norma kerakmi? | L–N → NEEDS_REVIEW | |
| M10 | Yuqorida UZO bo'lsa va Zs > Zs_max bo'lsa — NEEDS_REVIEW (ADR-0002 S3). Protokolda qanday xulosa yozilishi kerak? | NEEDS_REVIEW, LEAD izohi bilan imzolanadi | |

## Imzo

| | |
|---|---|
| Muhandis F.I.Sh. | |
| Lavozimi, tashkilot | |
| Elektr xavfsizligi guruhi, guvohnoma raqami | |
| Laboratoriya akkreditatsiya/litsenziya raqami | |
| Tekshirilgan fayl va versiya | `norms/v0.yaml`, `0.1.0` |
| Sana | |
| Imzo | |
