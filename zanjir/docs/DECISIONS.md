# ZANJIR — Arxitektura qarorlari (ADR)

Format: kontekst → qaror → oqibat. Qabul qilingan ADR o'zgartirilmaydi; o'rniga yangi ADR yoziladi.

---

## ADR-0001: Myrep monorepo ichida `zanjir/` papkasi

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan (foydalanuvchi, S8)
- **Kontekst:** Prompt bo'sh repozitoriyni nazarda tutadi, lekin foydalanuvchining loyihalari `Myrep` monorepo'sida yashaydi.
- **Qaror:** Barcha ZANJIR fayllari `zanjir/` ostida; promptdagi yo'llar (`app/`, `server/`, …) `zanjir/` ga nisbatan. CI — `.github/workflows/zanjir.yml`, faqat `zanjir/**` o'zgarganda ishlaydi. Release teglari: `zanjir-v*`.
- **Oqibat:** Boshqa loyihalar CI'si ZANJIR'ga ta'sir qilmaydi. Keyinchalik alohida repoga ko'chirish `git subtree split` bilan mumkin.

## ADR-0002: Baholash semantikasini aniqlashtirish (S1–S7)

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan (foydalanuvchi tasdig'i). Normalar muhandis tekshiruvigacha `needs_verification`.
- **Kontekst:** Promptdagi baholash qoidalarida bir nechta noaniqlik bor edi (6-bo'lim, 10-qoida).
- **Qaror:**
  1. **S1.** Sirtmoq uchun `node.attrs.circuit_role: final | distribution` (tugunda yoki yuqoridagi apparatda). Yo'q bo'lsa → NEEDS_REVIEW.
  2. **S2.** Zs_max uchun Ia har doim elektromagnit ajratgich zonasi: `Ia = trip_multiplier[curve] · In`. Koeffitsientlar (B=5, C=10, D=20) `norms/*.yaml` da (`trip_multipliers`), kodda emas. 5 s normasi uchun ham shu (konservativ).
  3. **S3.** Zs ≤ Zs_max → PASS; Zs > Zs_max va yuqorida UZO/RCBO yo'q → FAIL; bor → NEEDS_REVIEW.
  4. **S4.** UZO: `multiplier < 1` → norma yo'q → NEEDS_REVIEW. `tripped = false` → FAIL faqat `multiplier ≥ 1` da.
  5. **S5.** Qo'shimcha normalar `needs_verification` bilan: `RCD-2X` (≤ 150 ms), `RCD-2X-S` (60–200 ms), `RCD-5X-S` (50–150 ms), manba — ГОСТ IEC 61008-1.
  6. **S6.** `EARTH_ELECTRODE.attrs.role: neutral | repeat | tt`; EARTH-REPEAT uchun `values.scope: total | single` (jami ≤ 10 Ω, alohida ≤ 30 Ω). Yo'q bo'lsa → NEEDS_REVIEW.
  7. **S7.** EARTH-TT: `Ra · Ia ≤ 50 V`, Ia = yuqoridagi UZO'ning IΔn (graf orqali); UZO topilmasa → NEEDS_REVIEW. Yangi qoida turi `max_product`.
- **Oqibat:** `norms/schema.json` `min | max | range | max_time_ms | max_product` qoidalarini va `trip_multipliers` blokini qo'llab-quvvatlaydi. Tugun atributlari UI'da majburiy maydon sifatida ko'rsatiladi.

## ADR-0003: Asboblar versiyalari

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan
- **Kontekst:** Takrorlanadigan build'lar kerak (lokal ↔ CI).
- **Qaror:** Flutter 3.47.8 (stable, Dart 3.13.7) — CI'da `subosito/flutter-action` bilan aynan shu versiya; `zanjir_core` ham shu Dart bilan tekshiriladi. Python 3.12, bog'liqliklar `uv` bilan (`server/uv.lock`, `tools/norms/uv.lock`).
- **Oqibat:** Flutter yangilanishi — alohida commit va CHANGELOG yozuvi.

## ADR-0004: Normalarni tekshirish va release darvozasi

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan
- **Kontekst:** Normalar JSON Schema bo'yicha tekshirilishi va tekshirilmagan normalar bilan release chiqmasligi kerak (prompt 5.1).
- **Qaror:** `tools/norms/check_norms.py` — schema validatsiyasi, ID takrorlanmasligi, `--release` rejimida `reviewed_by` / `reviewed_at` bo'shligi va `needs_verification` normalar uchun xato. CI'da har push'da oddiy rejim, `zanjir-v*` teglarida `--release`. Ilova ichida `zanjir_core` normalarni yuklashda ham tekshiradi (ikkinchi himoya qatlami).
- **Oqibat:** Muhandis imzosisiz release build'i yiqiladi; Claude `reviewed_by` ni hech qachon to'ldirmaydi.

## ADR-0005: `evaluate()` ni amalga oshirish tafsilotlari

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan (1-faza). Muhandis savollari — `docs/NORMS_REVIEW.md` (M1–M10).
- **Kontekst:** Prompt 5.2 va ADR-0002 umumiy qoidalarni beradi; kodda aniq va tekshiriladigan semantika kerak.
- **Qaror:**
  1. **Qo'llanish uch holatli:** `match` / `noMatch` / `unknown`. Aniq mos kelmaslik ma'lumot yetishmasligidan ustun.
     Biror mos norma `unknown` bo'lsa (masalan, `node.attrs.selective` yo'q), boshqa normalar mos kelsa ham natija
     NEEDS_REVIEW (`norm_applicability_unknown`). Hech biri mos kelmasa — NEEDS_REVIEW (`no_matching_norm`).
  2. **NOT_APPLICABLE** faqat aniq belgilanganda: `values.not_applicable_reason` bo'sh bo'lmagan satr. "Normasi yo'q" hech qachon NOT_APPLICABLE emas.
  3. **Eng qat'iy norma:** barcha mos normalar tekshiriladi. Hal qiluvchi = eng og'ir natija (FAIL > NEEDS_REVIEW > PASS),
     teng bo'lsa — eng kichik nisbiy zaxira (`slack`). U `normId` va `eval_detail.strictest_norm_id` ga yoziladi.
  4. **Old shartlar** (harorat, asbob kuchlanishi, ψ) bajarilmasa — qiymatlar baholanmaydi, NEEDS_REVIEW (prompt 5.2 so'zma-so'z).
     Juftliklar/tekshiruvlar ichida esa FAIL NEEDS_REVIEW dan ustun.
  5. **Suzuvchi nuqta:** chegarani solishtirishda 1e-9 nisbiy tolerantlik (`2.5 · 1.6` = 4,0 Ω PASS). Bu norma qiymati emas.
     Qat'iy tengsizlikda (`RCD-RAMP` pastki chegarasi) aynan chegaradagi qiymat FAIL.
  6. **`margin_pct`:** `min` → `min·(1+m)`, `max`/`max_time_ms`/`max_product` → `max·(1−m)`, `range` ikkala tomondan toraytiriladi;
     sirtmoqda `Zs_max·(1−m)`.
  7. **Sirtmoq:** tugundan himoya apparatlarigacha (BREAKER/RCBO/FUSE) hudud olinadi; hududga qaytmasdan manbaga yetadigan
     chegaradagi apparatlar — "yuqoridagi". Himoyasiz yo'l → NEEDS_REVIEW; bir nechta kirish → har birining Zs_max i,
     hammasidan kichik → PASS, ba'zisidan katta → NEEDS_REVIEW (`zs_ambiguous_multiple_feeds`), hammasidan katta →
     UZO/RCBO **barcha** ta'minot yo'llarida bo'lsa NEEDS_REVIEW, aks holda FAIL. Faqat `L1..3-PE` / `L1..3-PEN` juftliklari.
     `circuit_role` o'lchangan tugunning o'zida bo'lishi kerak.
  8. **`k_corr`** faqat (0; 1] — 1 dan katta qiymat chegarani yumshatadi, `ArgumentError`.
  9. **UZO:** `multiplier < 1` → NEEDS_REVIEW (`rcd_multiplier_below_1`); `tripped` yo'q → NEEDS_REVIEW; `false` → FAIL.
     `range` + `relative_to: idn_ma` — o'chish toki (`trip_current_ma`), qolganlari — o'chish vaqti (`trip_time_ms`).
  10. **Yerga ulash:** ψ (`season_coeff`) majburiy va ≥ 1. TT: Ia = elektrod komponentidagi UZO/RCBO'larning eng katta IΔn;
      UZO yo'q yoki biror UZO'da `idn_ma` yo'q → NEEDS_REVIEW.
  11. **Izolyatsiya normasini tanlash:** `CABLE.attrs.circuit_class: wiring | power | secondary`
      (INS-WIRING / INS-CABLE-LV / INS-SECONDARY); PANEL/BUSBAR — INS-SWGR.
  12. **Sirtmoq U0:** jadval qiymatlari aniq olinadi (oxirgi zanjirlar uchun 127 / 220 / 380 / >380 V). 230 V → normasi yo'q (M1).
  13. **Normalarni Dart'da tekshirish:** JSON Schema kutubxonasi o'rniga qat'iy yuklovchi (`norm_loader.dart`): noma'lum maydon,
      tur, enum, chegaralar rad etiladi. Schema'ga moslik CI'da Python `jsonschema` bilan tekshiriladi (ikki qatlam).
  14. **Nol qiymatlar:** Zs = 0 Ω, yerga ulash R = 0 Ω, UZO t = 0 ms yoki tok 0 mA, asbob kuchlanishi 0 V fizik jihatdan
      mumkin emas (asbob xatosi) → NEEDS_REVIEW (`invalid_value`), PASS emas. Bog'lanish 0,00 Ω va izolyatsiya 0 MΩ — haqiqiy natija.
- **Oqibat:** `eval_detail` da `matched_norms`, `unknown_norms`, `checks[]` (formula, chegara, qiymat, zaxira), `strictest_norm_id`,
  `reason`, kirish qiymatlari, `norm_set_version`, `margin_pct`, `k_corr` saqlanadi. Sabab kodlari inglizcha, UI ularni l10n orqali ko'rsatadi.

## ADR-0006: Ajratish solveri (`planIsolation`) tafsilotlari

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan (2-faza). Ochiq savollar — `docs/PROGRESS.md` (S11–S14).
- **Kontekst:** Prompt 5.3 algoritmni beradi; chekka holatlar va natija formati aniqlashtirilishi kerak.
- **Qaror:**
  1. **Kesim:** tugun `v_in → v_out` (narx — `cut_costs.dart`, ro'yxatda yo'q tugun va zona — ∞), qirralar ∞, super-manba → S_r,
     zona → super-oqim. Edmonds–Karp; ∞ = barcha chekli narxlar yig'indisi + 1. Teng narxli kesimlardan **zonaga eng yaqini**:
     qoldiq tarmoqda super-oqimga yetadigan uchlar to'plami bo'yicha kesim (yagona, maksimal oqim tanloviga bog'liq emas).
  2. **Determinizm:** qo'shnilar ID bo'yicha saralanadi — tugun/qirra tartibi natijaga ta'sir qilmaydi (property test tekshiradi).
  3. **Zona ichidagi manba** (kondensatordan tashqari) → `Blocked(source_in_zone)`: reja avtomatik tuzilmaydi (S11).
     Zona ichidagi kondensator manba hisoblanmaydi, `CAPACITOR_IN_ZONE` ogohlantirishi beriladi.
  4. **S_r bo'sh** (graf bo'yicha zonaga hech qaysi manba yetmaydi) → kesimsiz reja + `NO_SOURCE_REACHABLE`; kuchlanish
     yo'qligini tekshirish va yerga ulash har bir zona tugunida baribir majburiy.
  5. **Kirish nuqtalari:** zonaga qo'shni va manbadan zonaga kirmasdan yetib boriladigan tugunlar (kesimdan oldingi graf bo'yicha).
     Manbaga ulanmagan "pastki" qo'shnilar kirish hisoblanmaydi (S13). Har bir kirish uchun bitta tekshirish va bitta yerga ulash qadami.
  6. **Teskari manbalar** (1-qadam): S_r dagi PV (AC, keyin DC), generator, UPS, akkumulyator. Tarmoq/transformator — kesim orqali.
  7. **Ogohlantirishlar:** zona komponentidagi `verified = false` tugunlar; zonadagi **har bir** kabel (uzunlik chegarasi yo'q —
     konservativ, `length_m` parametr sifatida, S12); S_r dagi PV — DC tomoni; TN-C yoki zonaga tegadigan PEN o'tkazgich;
     kesimdagi CONTACTOR/ATS; yerga ulash tizimi noma'lum.
  8. **Mustaqil tekshiruv:** kesimni olib tashlab BFS; yo'l topilsa `Blocked(verification_failed)` va `isolation_cut_verification_failed`
     log hodisasi (faqat tugun ID'lari).
  9. **`graph_snapshot_hash`:** kanonik graf (`zanjir.graph/1`: tugunlar — id, kind, label, attrs, verified, panel_id; qirralar —
     id, tartiblangan uchlar, conductors; earthing_system) → RFC 8785 kanonik JSON → SHA-256. `state` kirmaydi: rejani bajarish
     apparat holatini o'zgartiradi va reja STALE bo'lib qolmasligi kerak. Shu uchun kanonik JSON'ning Dart qismi 3-fazadan oldinroq qilindi.
  10. Ilova "ishlash xavfsiz" demaydi: natija — **tavsiya** (`IsolationPlan`), tasdiqlash LEAD/ish rahbari zimmasida (9-faza).
- **Oqibat:** `IsolationResult.toJson()` → `isolation_plan.steps` / `warnings` JSON. Qadam/ogohlantirish kodlari inglizcha,
  matnlari l10n'da. Unumdorlik: 2000 tugun — desktop AOT'da ~22 ms (`benchmark/solver_bench.dart`).

## ADR-0007: Kanonik JSON, hash-zanjir va imzo formati

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan (3-faza).
- **Kontekst:** Prompt 5.4: Dart (qurilma) va Python (server) bir xil baytlarni hosil qilishi va tekshirishi shart.
- **Qaror:**
  1. **Kanonik JSON** — RFC 8785 (JCS): kalitlar UTF-16 kod birliklari bo'yicha, sonlar ECMAScript formatida,
     butun sonlar |n| ≤ 2^53 − 1, NaN/∞ va yolg'iz surrogatlar rad etiladi. Vaqt faqat UTC, `YYYY-MM-DDTHH:MM:SS.sssZ`
     (mikrosekundlar tashlanadi); mahalliy vaqt — xato.
  2. **Kodlash:** hash, ochiq kalit va imzo — kichik harfli hex. Imzo xom baytlar ustida: hodisa — `event_hash` ning 32 bayti,
     protokol — `payload_sha256 ‖ pdf_sha256` (32 + 32 bayt).
  3. **Zanjir:** qurilma bo'yicha alohida; `seq` 1 dan; birinchi `prev_hash` = 64 ta nol (`genesis`). Davom ettirish — server
     saqlagan oxirgi hodisa (`anchor`) dan. Tekshiruv tartibi va sabab kodlari ikkala tomonda bir xil:
     `invalid_format` → `unsupported_sig_alg` → `seq_gap` → `prev_hash_mismatch` → `event_hash_mismatch` → `bad_signature`.
     Server `push` da birinchi xatoda butun paketni rad etadi (7-faza).
  4. **`sig_alg`:** hozircha faqat `Ed25519`; noma'lum algoritm — rad. ML-DSA gibrid yoki E-IMZO — yangi qiymat qo'shish orqali.
     O'zgaruvchan (S ≥ L) imzolar va egri chiziqda yotmaydigan kalitlar ikkala kutubxonada rad etiladi (vektor bilan qotirilgan).
  5. **Vektorlar:** `tools/vectors/generate.py` Python implementatsiyasini RFC 8785 / RFC 8032 rasmiy natijalari bilan tekshirib,
     vektorlarni yozadi; Dart ularni mustaqil tekshiradi va zanjir/imzoni **qayta quradi** (baytma-bayt tenglik). CI `--check`.
  6. **Kalitlar:** `Signer` interfeysi; ilovada maxfiy kalit Android Keystore himoyasida (4/6-faza). Serverda maxfiy kalit yo'q —
     Python `Ed25519Signer` faqat testlar va generator uchun. Dart kutubxonasi (`cryptography`) — sof Dart, API asinxron.
- **Oqibat:** Format o'zgarishi — yangi ADR va vektorlarni ikkala tomonda bir vaqtda yangilash.
