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

## ADR-0008: Ilova ma'lumot qatlami — `packages/zanjir_data` (Drift)

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan (4-faza).
- **Kontekst:** Lokal baza — qurilmadagi asosiy manba (offline-first). Testlar tez va Flutter'siz bo'lishi kerak.
- **Qaror:**
  1. **Alohida sof Dart paket** `packages/zanjir_data` (Drift 2.35 + `sqlite3` 3.x — SQLite build hook orqali olinadi;
     `sqlite3_flutter_libs` EOL). Ilova 5-fazada shu paketga ulanadi. Repo tuzilmasiga qo'shimcha (stek o'zgarmagan).
  2. **Sxema** — prompt 4-bo'lim. Qo'shimchalar: `audit_event.sig_alg` va `event_at` (hash hisoblanadigan kanonik vaqt satri);
     `app_user` da `password_hash` **yo'q** (faqat serverda); CHECK: `role`, `safety_group`, `isolation_plan.status`;
     UNIQUE: `protocol (org_id, number)`, `protocol.qr_token`, `audit_event (device_id, seq)`, `audit_event.event_hash`,
     `norm_set (org_id, version)`, `measurement.supersedes_id` (o'lchov ko'pi bilan bir marta almashtiriladi). `PRAGMA foreign_keys = ON`.
     Vaqtlar ISO matn, doim UTC; JSON ustunlari kanonik JSON (RFC 8785).
  3. **Append-only** (`measurement`, `protocol`, `audit_event`): repozitoriylarda UPDATE/DELETE metodlari yo'q (asosiy himoya)
     + SQLite triggerlari `RAISE(ABORT, 'append_only: …')` (ikkinchi qatlam). `rev` qo'shilganda 1; server reviziyasi bu
     jadvallarni o'zgartirmaslik uchun 8-fazada alohida jadvalda saqlanadi.
  4. **Migratsiyalar:** `drift_dev make-migrations`, eksport — `drift_schemas/`. Testlar: `schemaVersion` = oxirgi eksport;
     yangi baza eksport qilingan sxemaga (jadval, trigger, indeks) aynan mos; har bir eksport versiyasidan joriygacha migratsiya;
     yangiroq versiyadagi bazani ochish (pastga tushirish) rad etiladi. Sxema o'zgarsa: `schemaVersion` + `make-migrations` + qadam.
  5. **Tashkilotlar ajratilgan:** `DataContext.orgId` — har bir so'rovda filtr; boshqa tashkilot yozuvi "topilmadi" (farq ko'rsatilmaydi).
  6. **Repozitoriy qoidalari:** o'lchov yozish = `evaluate()` + `measurement` + `MEASUREMENT_ADDED` audit — bitta tranzaksiya;
     yopilgan sessiyaga yozilmaydi; tugun sessiya obyektida bo'lishi shart; almashtirish faqat shu sessiya, tugun va turdagi
     o'lchov uchun va bir marta. Protokol bekor qilinishi — faqat `PROTOCOL_REVOKED` hodisasi. Audit: bekor qilingan qurilma
     yoki ro'yxatdagi kalitga mos kelmaydigan imzolovchi yozolmaydi.
  7. **Ajratish rejasi:** DRAFT → APPROVED (faqat LEAD/ADMIN) → EXECUTED, DRAFT/APPROVED → CANCELLED. Saqlash, tasdiqlash va
     bajarishdan oldin graf hash'i (yerga ulash tizimi bilan) tekshiriladi — farq bo'lsa STALE va xato. Apparat holati hash'ga kirmaydi.
  8. **Normalar to'plami:** YAML o'zgarishsiz saqlanadi, `sha256` bilan; yuklashda hash mos kelmasa `norm_set_tampered`;
     bir xil versiya boshqa mazmun bilan — `norm_set_version_conflict`.
  9. **Nusxalangan apparat** (QF1 → QF2) `verified = false` — dalada tekshirilmaguncha solver ogohlantiradi.
- **Oqibat:** `k_corr` hozircha `EvalSettings` parametri; laboratoriya sozlamalarini saqlash — 5-fazada. Muddati o'tgan asbob bilan
  o'lchov yoziladi, lekin imzolash 6-fazada bloklanadi (CLAUDE.md, 6-qoida; `InstrumentRepository.isVerificationValid`).

## ADR-0009: Ilova UI (5-faza) — sozlamalar, oflayn profil, kiritish qoidalari

- **Sana:** 2026-10-26 · **Holat:** qabul qilingan (5-faza).
- **Kontekst:** Prompt 8-bo'lim (ekranlar, ≤ 10 s kiritish, dala sharoiti) va 5.2 (`margin_pct` normalar to'plami darajasida),
  shu bilan birga sozlamalarda `k_corr` va `margin_pct` — faqat LEAD. Server (auth) 7-fazada.
- **Qaror:**
  1. **Laboratoriya zaxirasi:** effektiv `margin_pct = max(norm_set.margin_pct, lab.margin_pct)` — sozlama chegarani faqat
     qat'iylashtiradi. `k_corr` ∈ (0; 1]. Ikkalasi `org_setting` jadvalida, faqat LEAD/ADMIN o'zgartiradi, har o'zgarish —
     `SETTINGS_CHANGED` audit hodisasi. O'lchov yozilganda repozitoriy sozlamani o'zi o'qiydi (UI uzatishni unutolmaydi).
     `eval_detail` da `margin_pct` (effektiv), `norm_set_margin_pct`, `lab_margin_pct`, `k_corr`.
  2. **Sxema v2:** `org_setting` (sinxronlanadi) va `local_pref` (qurilmaga xos: profil, til, katta shrift). v1 → v2 migratsiyasi
     ma'lumot bilan testlangan (append-only triggerlar saqlanadi).
  3. **Kirish:** `AuthGateway` interfeysi; server 7-fazada. Hozir "server mavjud emas" va **oflayn laboratoriya profili**:
     tashkilot + foydalanuvchi (faqat LEAD/ADMIN — laboratoriyani yaratuvchi) + qurilma kaliti (32 bayt `Random.secure`,
     `flutter_secure_storage`/Android Keystore; avval kalit, keyin baza) + ilova bilan kelgan normalar to'plami (faol versiya).
     Muhandislar 7-fazada taklif kodi bilan qo'shiladi.
  4. **Kiritish qoidalari (PASS hech qachon standart emas):** UZO "O'chdi/O'chmadi" va mavsumiy koeffitsient ψ oldindan
     to'ldirilmaydi; bo'sh maydon qiymatlarga qo'shilmaydi (→ `value_missing`); tugun atributlari (masalan, `selective`)
     uch holatli — "Kiritilmagan" tanlansa atribut yozilmaydi. Vergul va nuqta qabul qilinadi. Saqlangach natija rangi, sabab
     va chegara ko'rsatiladi, keyingi nuqtaga avtomatik o'tiladi. Xato o'lchov — uzoq bosish → "Qayta o'lchash" (`supersedes_id`).
  5. **Rang:** Myrep dark tokenlari + `success #7DBE8A` (paper 6,9:1, surface 6,1:1, ustida accentInk 7,6:1). Natija belgisi
     rang + ikonka + matn (faqat rangga tayanmaydi, TalkBack uchun `Semantics`). Tugmalar ≥ 48 dp, katta shrift ×1,3.
     Noto Sans ilova ichida (OFL).
  6. **QR:** tugun QR kodi `zanjir://app/n/<id>` (Android intent-filter, go_router `/n/:id`); kodni qo'lda kiritish mavjud.
     Kamera bilan skanerlash — keyingi fazalarda (native plagin, qurilmada sinov talab qiladi).
  7. **Ajratish rejasi** ekrani hozircha faqat ko'rib chiqish (tavsiya, qadamlar, ogohlantirishlar); tasdiqlash va checklist — 9-faza.
     Protokol ekrani — 6-faza.
  8. **Testlar:** widget testlari + asosiy oqim (`test/flow/main_flow.dart`) — xuddi shu oqim `integration_test` da qurilmada
     (`.github/workflows/zanjir-emulator.yml`). `assets/norms/v0.yaml` = `norms/v0.yaml` test bilan nazorat qilinadi.
- **Oqibat:** Testlar uchta haqiqiy UI xatosini topdi va tuzatildi (tor ekranda dropdown va natija belgisining sig'masligi,
  dialog yopilayotganda dispose qilingan controller). Android build va emulyator jobi bu muhitda tekshirilmagan (SDK yo'q).

## ADR-0010: Deterministik PDF, protokol payload'i va imzolashni bloklash shartlari (6-faza)

- **Sana:** 2026-10-27 · **Holat:** qabul qilingan (6-faza).
- **Kontekst:** Prompt 5.4 (`signature = Ed25519(payload_sha256 ‖ pdf_sha256)`), 6-faza mezoni "bir xil payload → baytma-bayt
  bir xil PDF; imzolashni bloklash testlari", CLAUDE.md 1- va 6-qoidalar, 8-bo'lim ("ekranshotdan himoya faqat imzolash ekranida").
- **Qaror:**
  1. **Paket:** `packages/zanjir_protocol` — sof Dart (`pdf`, `barcode`), Flutter'ga bog'liq emas: payload → PDF.
     `zanjir_data` unga bog'liq (imzolashda PDF repozitoriy ichida render qilinadi — imzolangan PDF aynan imzolangan payload'dan).
  2. **Determinizm:** `pdf` paketi faqat ikki joyda tasodifiy/vaqtga bog'liq: `/ID` (tasodifiy) va metama'lumot (`/CreationDate`).
     Metama'lumot umuman berilmaydi; render qilingan fayldagi yagona `/ID[<a><b>]` bir xil uzunlikdagi `<sha><sha>` bilan
     almashtiriladi (`sha = payload_sha256`, xref ofsetlari o'zgarmaydi; `/ID` aynan bitta bo'lmasa — xato). Shriftlar —
     ilova ichidagi Noto Sans (+ `NotoSansMath` ≤ ≥ uchun zaxira), subset qilinadi. QR — `BarcodeWidget(drawText: false)`
     (aks holda Courier qo'shiladi). Testlar: ikki render, boshqa isolate, kalitlar tartibi teskari payload, 250 o'lchovli
     ko'p sahifali protokol — baytma-bayt teng; `/ID` = payload hash; metama'lumot va Courier yo'q; yetishmagan glif haqida
     ogohlantirish yo'q (uz/ru); `pdftotext` bilan mazmun (ogohlantirish matni bor, "ishlash xavfsiz" yo'q).
     Kafolat chegarasi: bir xil `pdf` paketi versiyasi, shriftlar va zlib — boshqa ilova versiyasi boshqa bayt berishi mumkin.
     Shuning uchun imzolangan PDF **saqlanadi** (`protocol_document`), qayta render qilinmaydi.
  3. **Payload `zanjir.protocol/1`** (kanonik JSON, RFC 8785): `protocol{number, qr_token, verify_url, language}`,
     `lab{org_id, name, license_no, license_valid_until}`, `site{...}`, `session{id, kind, started_at, closed_at, harorat, namlik}`,
     `engineer{id, full_name, safety_group}`, `signer{id, full_name, role, device_id, public_key}`, `signed_at`, `lead_comment`,
     `norm_set{version, sha256, reviewed_by, reviewed_at}`, `instruments[]` (guvohnoma raqami va muddati),
     `measurements[]` (amaldagilari, yaratilish tartibida: qiymatlar, verdikt, `norm_id`, sabab, hal qiluvchi chegara va formula,
     `margin_pct`, `k_corr`, `supersedes_id`), `summary` (barcha verdikt kalitlari, PASS standart emas). PDF faqat payload'dan
     chiziladi — PDF dagi har bir ma'lumot imzolangan. Matnlar ilova ARB fayllaridan generatsiya qilinadi
     (`tool/gen_strings.py`, CI `--check`) — ilova va PDF bir xil tarjimadan foydalanadi.
  4. **Raqam:** `YYYY-XXXXXX-NNN` — yil, qurilma ID sining oxirgi 6 hex belgisi, shu prefiks bo'yicha keyingi tartib raqami
     (oflayn qurilmalar to'qnashmaydi; `(org_id, number)` yagona). `qr_token` — 128 bit `Random.secure`.
     QR: `<verify_base><qr_token>`; asos `--dart-define=ZANJIR_VERIFY_BASE_URL` (domen 2-darvozada), berilmasa
     `zanjir://app/v/<token>` (ilova ichida `/v/:token` — shu qurilmadagi protokol holati va tekshiruvi).
  5. **Bloklash shartlari** (`ProtocolRepository.prepare` → `ProtocolBlocker`; imzolashda qayta tekshiriladi):
     `session_open`, `no_measurements`, `forbidden_role` (imzolaydi faqat LEAD va ENGINEER), `device_not_trusted`
     (bekor qilingan yoki kalit mos emas), `license_missing` / `license_expired` (oxirgi kun amal qiladi), `already_signed`
     (amaldagi protokol bor — avval sabab bilan bekor qilinadi), `instrument_expired` (o'lchov kuni guvohnoma amal qilmagan
     yoki muddati yo'q; o'chirilgan asbob ham hisobga olinadi), `mixed_norm_sets`, `norms_not_reviewed` (muhandis
     tekshirmagan normalar bilan **imzolanmaydi** — 1-darvoza yopilmaguncha ilovada imzolash bloklangan),
     `needs_review_requires_lead`, `lead_comment_required` (NEEDS_REVIEW — faqat LEAD va izoh bilan).
     FAIL natija bloklamaydi — protokol uni qayd etadi.
  6. **Imzolash:** `prepare` (qoralama, `signed_at` = tayyorlash vaqti) → `sign(draft, fonts)`: PDF render → tranzaksiyada
     payload qayta quriladi va kanonik tengligi tekshiriladi (aks holda `draft_stale`; 15 daqiqadan eski qoralama ham),
     imzo, `protocol` + `protocol_document` + `PROTOCOL_SIGNED` audit — birga. `verify(id)`: `/ID`, payload hash, PDF hash,
     protokolni yaratgan qurilma kaliti bilan imzo. Bekor qilish — faqat LEAD/ADMIN, sabab majburiy (`PROTOCOL_REVOKED`).
  7. **Sxema v3:** `protocol_document(protocol_id, payload_json, pdf)` — append-only (trigger), v2 → v3 migratsiyasi
     ma'lumot bilan testlangan.
  8. **Ilova:** protokol ekrani — shartlar ro'yxati (l10n), til (uz/ru), ish rahbari izohi, tasdiqlash dialogi, imzolangan
     protokol kartasi (QR, hash'lar, tekshiruv natijasi, ulashish/chop etish — `printing`, bekor qilish). Ekran ochiq
     turganda `FLAG_SECURE` (`MethodChannel('zanjir/secure_screen')`, `MainActivity`). Sozlamalarda laboratoriya rekvizitlari
     (litsenziya) — LEAD/ADMIN.
- **Oqibat:** 1-darvoza (muhandis tekshiruvi) yopilmaguncha haqiqiy protokol imzolanmaydi — testlar faqat test uchun
  nusxalangan, "TEST FIXTURE" deb belgilangan normalar bilan ishlaydi (`norms/v0.yaml` o'zgarmaydi). ADMIN imzolamaydi
  (tashkilot boshqaruvchisi; kerak bo'lsa — foydalanuvchi qarori bilan o'zgartiriladi). Android'da `printing` va FLAG_SECURE
  bu muhitda tekshirilmagan (SDK yo'q) — emulyator jobi va 12-fazada.

## ADR-0011: Server (7-faza) — auth, RBAC, RLS, sinxronlash, ochiq tekshirish sahifasi

- **Sana:** 2026-10-27 · **Holat:** qabul qilingan (7-faza).
- **Kontekst:** Prompt 7-bo'lim (auth, RBAC, sync, `/v/{qr_token}`, himoya, kuzatuv), 6-qoida (protokol), 7-qoida (RLS),
  8-qoida (log). Mezon: pytest + testcontainers; RBAC matritsasi to'liq qoplangan.
- **Qaror:**
  1. **Sxema:** ilovadagi Drift jadvallari bilan bir xil ustunlar (sim formati = ustun nomlari) + faqat serverdagi
     `refresh_token`, `invite`, `sync_op`, `org_sync_rev`. Bitta Alembic migratsiyasi (`0001`); modellar bilan mosligi
     testda tekshiriladi (`compare_metadata`), head → base → head ham.
  2. **Tashkilot ajratilishi:** RLS (`org_id = current_setting('app.org_id')`) + kodda `org_id` filtri. Ilova imtiyozsiz
     login roli bilan ulanadi va har tranzaksiyada `SET LOCAL ROLE zanjir_app`. Tashkilot noma'lum yo'llar uchun faqat
     to'rtta `SECURITY DEFINER` funksiya (telefon / refresh hash / taklif hash / `qr_token` → `org_id`). Havolalar
     `(org_id, id)` kompozit FK (DEFERRABLE) — boshqa tashkilot yozuviga bog'lanib bo'lmaydi.
  3. **Append-only:** `measurement`, `protocol`, `protocol_document`, `audit_event` — UPDATE/DELETE/TRUNCATE trigger bilan
     taqiqlangan (egasi uchun ham), ilova roliga UPDATE huquqi berilmagan; boshqa jadvallarda DELETE huquqi yo'q (soft delete).
  4. **Auth:** telefon (`+998XXXXXXXXX`) + parol (argon2id, RFC 9106: t=3, 64 MiB, p=4; eski parametrli hash kirishda
     yangilanadi). Access JWT HS256, 15 daqiqa, muddat ilova soati bilan tekshiriladi; rol har so'rovda bazadan.
     Refresh — 256 bit, bazada SHA-256, 30 kun, rotatsiya; ishlatilgan token qayta kelsa butun oila bekor. Taklif kodi
     16 belgi (~80 bit), bir martalik (shartli UPDATE), ≤ 7 kun; ADMIN — har rolga, LEAD — ENGINEER/VIEWER.
     **Laboratoriyani ro'yxatdan o'tkazish** (`/auth/register`, ixtiyoriy oflayn `org_id`/`user_id` bilan) —
     `ZANJIR_REGISTRATION_OPEN` (prod'da standart yopiq). SMS OTP — interfeys, o'chiq (404).
  5. **Sinxronlash:** `server_rev` — tashkilot hisoblagichi (`org_sync_rev`, trigger; qator qulfi tufayli bir tashkilot
     o'zgarishlari commit tartibida raqamlanadi — pull hech narsani o'tkazib yubormaydi). `GET /sync/pull?since=&limit=`
     (`password_hash`, `phone` chiqmaydi). `POST /sync/push` — bitta tranzaksiya, birorta xato bo'lsa butun paket rad
     (`422 push_rejected {reason, op_id}`); `client_op_id` takrori o'tkazib yuboriladi; metadata — LWW (`updated_at`,
     keyin `rev`), append-only — bir xil qayta yuborish takror, farqli — xato. Qo'shimcha tekshiruvlar:
     audit zanjiri (seq, prev_hash, hash, Ed25519; faqat o'z qurilmasi va o'z nomidan; bekor qilingan qurilma — rad);
     o'lchov va protokol tegishli imzolangan audit hodisasi (`MEASUREMENT_ADDED` / `PROTOCOL_SIGNED`, payload hash) bilan
     bog'langan; protokol — imzo, imzolovchi roli, qurilma egasi, hujjat majburiy; hujjat — payload/PDF hash, `/ID`,
     payload ↔ protokol, 6-qoida (normalar tekshirilgan, asbob guvohnomasi, NEEDS_REVIEW → LEAD izoh bilan, litsenziya),
     payload'dagi natijalar serverdagi o'lchovlar bilan bir xil, sessiya yopilgan; normalar to'plami — `sha256(yaml)` va
     `reviewed_by/at` YAML ichidagisi bilan bir xil (alohida soxtalashtirib bo'lmaydi); sessiyani qayta ochib bo'lmaydi;
     ajratish rejasi APPROVED/EXECUTED — faqat LEAD/ADMIN tasdig'i bilan.
  6. **Ochiq sahifa:** `/v/{qr_token}` (Jinja2, uz/ru, Myrep dark tokenlari, ilova shrifti), holat (bekor qilish — audit
     hodisasi), raqam, laboratoriya, imzolovchi F.I.Sh., vaqt, hash'lar, serverda imzo tekshiruvi; PDF yuklash; faylni
     brauzerda SHA-256 bilan solishtirish (fayl yuborilmaydi). Manzil, buyurtmachi, telefon sahifada yo'q. Qat'iy CSP,
     `no-store`, `noindex`.
  7. **Himoya va kuzatuv:** rate limiting (jarayon xotirasida; `/auth/*` 10/daq, qolganlari 300/daq IP bo'yicha — bir necha
     nusxada Redis), so'rov hajmi 5 MB (chunked ham), CORS faqat ro'yxat, OpenAPI/docs o'chiq, JSON log (faqat marshrut
     shabloni, token/telefon/parol yo'q), Prometheus `/metrics`, `/healthz`, `/readyz`, xato hisobotlari adapteri (o'chiq).
  8. **Testlar:** testcontainers (PostgreSQL 16, image ECR ko'zgusidan — Docker Hub limitlari) yoki
     `ZANJIR_TEST_DATABASE_URL`; API testlari imtiyozsiz login roli bilan; qamrov ≥ 95% (CI darvozasi).
- **Oqibat:** Ilova bilan haqiqiy sinxronlash (Dart → server, bir xil audit va protokol baytlari) — 8-faza (E2E).
  `org_setting` bir tashkilotda bitta: ikki qurilma turli ID bilan yaratsa — `constraint_violation` (8-fazada ilova
  serverdagini oladi). Asbob guvohnomasi muddatini muhandis o'z qurilmasida soxtalashtirsa, server buni payload'dan
  aniqlay olmaydi — protsessual nazorat (audit izi saqlanadi).

## ADR-0012: Ilova ↔ server sinxronlash (8-faza)

- **Sana:** 2026-10-27 · **Holat:** qabul qilingan (8-faza).
- **Kontekst:** Prompt 7–8-bo'limlar (offline-first, fonda va qo'lda sinxronlash) va 8-faza mezoni: "ikki qurilma offline
  ishlaydi → sync → o'lchovlar yo'qolmaydi va takrorlanmaydi; zanjir buzilishi rad etiladi".
- **Qaror:**
  1. **Navbat (outbox):** `sync_outbox(table_name, row_id, op_id)` — SQLite triggerlari (INSERT/UPDATE) to'ldiradi, repozitoriy
     unutolmaydi; qatorning keyingi o'zgarishi yozuvni yangi `op_id` bilan almashtiradi. `app_user`, `device` — faqat API.
     Serverdan kelgan o'zgarish navbatga tushmaydi (`local_pref` `sync.applying` belgisi triggerning `WHEN` shartida).
     Sxema v4; v3 → v4 migratsiyasi mavjud ma'lumotni ham navbatga qo'yadi (audit — `seq` tartibida).
  2. **Push:** paket ≤ 500 op; audit hodisalari (`seq` bo'yicha) birinchi, keyin jadvallar ota-bola tartibida; protokol o'z
     hujjati bilan bir paketda (server talabi). Muvaffaqiyatdan keyin faqat yuborilgan `(id, op_id)` o'chiriladi — oraliqda
     o'zgargan qator navbatda qoladi. Javob yo'qolsa qayta yuborish xavfsiz (server `client_op_id` takrorini o'tkazib
     yuboradi; append-only bir xil qator — takror). Rad etilsa — navbat saqlanadi, sabab foydalanuvchiga ko'rsatiladi.
  3. **Pull:** `server_rev` kursori (`sync.cursor`), **barcha sahifalar bitta tranzaksiyada** (`defer_foreign_keys`):
     ota yozuv keyin o'zgarsa uning `server_rev` i bolalaridan katta — sahifalar alohida commit qilinsa lokal FK buzilardi
     (testda topilgan). Metadata — LWW (`updated_at`, keyin `rev`; server yutsa mahalliy navbat yozuvi olib tashlanadi),
     append-only — faqat qo'shiladi. Serverda yo'q lokal ustunlar (`app_user.phone`) yangi qatorda standart qiymat oladi.
  4. **Sim formati shartnomasi:** `tools/vectors/sync_schema.json` — server testi yaratadi/tekshiradi, Dart testi lokal
     jadvallar (nom, tur, null) bilan solishtiradi.
  5. **Hisob oqimlari (`ServerAccount`):** oflayn laboratoriya o'z ID lari va litsenziyasi bilan ro'yxatdan o'tadi (aks holda
     pull LWW lokal litsenziyani server qiymati bilan almashtirardi) + qurilma ochiq kaliti + to'liq push; taklif kodi bilan
     qo'shilish va yangi qurilmada kirish — yangi kalit, qurilma, to'liq pull, lokal profil. Boshqa foydalanuvchi profili bor
     qurilmada kirish rad etiladi (yangi sessiya serverda yopiladi, oldingisi tiklanadi). Tokenlar `flutter_secure_storage`.
  6. **Ilova:** `--dart-define=ZANJIR_SERVER_URL` (bo'sh — faqat oflayn). Sozlamalarda "Server" bo'limi: ro'yxatdan o'tish
     (LEAD/ADMIN), holat (navbat, oxirgi vaqt, natija, xato), "Sinxronlash", taklif kodi yaratish, chiqish. Fonda: ulangan
     bo'lsa har 5 daqiqada va ilova qayta ochilganda; bir vaqtda bitta sinxronlash. Kirish va taklif bilan qo'shilish ekranlari.
  7. **E2E:** `tools/e2e/run.sh` — PostgreSQL 16 + FastAPI (imtiyozsiz `zanjir_api` roli bilan) + `packages/zanjir_data/test/e2e`
     (Dart). CI `e2e` jobi. Ilova UI testlari — `MockClient` dagi soxta server bilan.
- **Oqibat:** Dart va Python audit hash'i, o'lchov va protokol payload hash'lari, PDF `/ID` va imzo haqiqiy serverda mos keldi.
  Bitta yaroqsiz qator butun navbatni to'xtatadi (server "hammasi yoki hech narsa") — ataylab: audit zanjiri uzilmasin;
  bunday holat foydalanuvchiga sabab bilan ko'rsatiladi. LWW qurilma soatiga tayanadi (soat noto'g'ri bo'lsa, kechroq
  yozilgan o'zgarish yutqazishi mumkin) — 10-fazada server vaqti bilan tuzatish ko'rib chiqiladi.

## ADR-0013: Ajratish rejasi — tasdiqlash, bajarish checklist'i, STALE (9-faza)

- **Sana:** 2026-10-27 · **Holat:** qabul qilingan (9-faza).
- **Kontekst:** Prompt 5.3 (5 ta texnik tadbir, "kuchlanish yo'qligini tekshirish" — majburiy, ko'rsatkichni oldin kuchlanish
  borligi ma'lum joyda sinash), 8-bo'lim (ajratish rejasi — qadamlar checklist'i), CLAUDE.md 1- va 2-qoidalar.
  Mezon: integration test; majburiy qadamni o'tkazib bo'lmasligi testlangan.
- **Qaror:**
  1. **Yadro (`solver/execution.dart`, 100% qamrov):** `StepConfirmation` (barcha maydonlar standart `false`),
     `checkStepCompletion` — qadamlar faqat ketma-ket (`out_of_order`), har biri aniq tasdiq bilan
     (`confirmation_required`); kuchlanish yo'qligini tekshirish — ikki alohida tasdiq: ko'rsatkich oldin sinalgan
     (`indicator_pretest_required`) va kuchlanish yo'q (`no_voltage_confirmation_required`). `PlanStep/PlanWarning.fromJson`;
     JSON'dagi `mandatory: false` e'tiborga olinmaydi.
  2. **Holatlar:** DRAFT → APPROVED (faqat LEAD/ADMIN — joriy foydalanuvchi) → qadamlar → EXECUTED (faqat barcha qadamlar
     bajarilganda); DRAFT/APPROVED → CANCELLED; graf yoki yerga ulash tizimi o'zgarsa → STALE (ro'yxat/reja ochilganda va
     har bir amaldan oldin tekshiriladi; STALE holati tranzaksiya bekor bo'lsa ham saqlanadi). Reja tuzish, qadam va
     bekor qilish — ENGINEER/LEAD/ADMIN; VIEWER — faqat ko'radi.
  3. **Bajarilgan qadam — imzolangan audit hodisasi** `PLAN_STEP_DONE` (`entity_id` = `<reja>#<tartib>`, payload: reja, tartib,
     tur, tasdiq) — alohida jadval va sxema o'zgarishisiz: audit zanjiri bilan himoyalangan, sinxronlash orqali boshqa
     qurilmalarga yetadi (kim, qachon). Boshqa o'tishlar ham hodisa: `PLAN_CREATED`, `PLAN_APPROVED` (serverda ham faqat
     LEAD/ADMIN), `PLAN_EXECUTED`, `PLAN_CANCELLED`.
  4. **UI:** obyekt → "Ajratish rejalari" ro'yxati (holat belgisi), yangi reja (zona → solver → "Qoralama sifatida saqlash"),
     reja ekrani: ogohlantirishlar, qadamlar; faqat navbatdagi qadamda "Belgilash"; tasdiq dialogida hech narsa oldindan
     belgilanmagan, tugma barcha kerakli bandlar belgilangach faol; tasdiqlash va yakunlash dialoglarida javobgarlik matni.
     STALE — ogohlantirish va hech qanday amal yo'q (bajarilgan qadamlar tarixi ko'rinadi). "Ishlash xavfsiz" matni yo'q.
- **Oqibat:** Qadamni bekor qilish (noto'g'ri belgilangan) imkoni yo'q — audit append-only; xato bo'lsa reja bekor qilinib,
  yangisi tuziladi. Apparat holatini (`state`) qadam bilan avtomatik o'zgartirish — yo'q (holat graf hash'iga kirmaydi;
  dalada qo'lda yangilanadi). S11–S14 (solver) hali ochiq — solver konservativ.

## ADR-0014: Mustahkamlash (10-faza) — xavfsizlik ko'rigi, bog'liqliklar auditi, unumdorlik, accessibility

- **Sana:** 2026-10-27 · **Holat:** qabul qilingan (10-faza).
- **Kontekst:** Prompt 9-bo'lim, 10-faza: `docs/SECURITY.md` (tahdid modeli, MASVS checklist, RBAC matritsasi),
  bog'liqliklar auditi, unumdorlik, accessibility; mezon — barcha "yuqori" topilmalar yopilgan.
- **Qaror:**
  1. **Xavfsizlik ko'rigi:** ikki bosqich — o'z ko'rigim va mustaqil ko'rik (alohida agent, kod asosida, xulosalarimsiz).
     Topilmalar `docs/SECURITY.md` reestrida: daraja (Y/O/P), holat; qabul qilingan qoldiq xavflar (R-*) sabab bilan.
  2. **Mobil:** `allowBackup=false` + `dataExtractionRules` (zaxira/ko'chirishda ma'lumot chiqmaydi); faqat HTTPS
     (`isAllowedServerUrl` + `network_security_config`, faqat tizim CA); release imzo faqat `key.properties` dan — kalitsiz
     release build yiqiladi; obfuskatsiya release buyrug'ida (12-faza).
  3. **Server:** `/metrics` standart o'chiq (token bilan); hisob bo'yicha kirish cheklovi (IP dan qat'i nazar); kelajak
     vaqtli yozuvlar rad (`clock_skew`, LWW'ni egallab olmaslik); barcha javoblarga xavfsizlik sarlavhalari va `no-store`.
  4. **Bog'liqliklar:** `tools/audit/osv_audit.py` — barcha `pubspec.lock` va `uv.lock` OSV.dev da (faqat standart
     kutubxona); istisnolar `allowlist.json` da sabab va muddat bilan; CI `zanjir-audit` — haftalik va lock o'zgarganda.
  5. **Unumdorlik byudjetlari (testlar):** 2000 tugunli obyekt: graf yuklash < 1,5 s, o'lchov yozish < 200 ms, reja < 1,5 s
     (o'lchangan: 44 / 45 / 76 ms); 2900 yozuvli push/pull < 15 s (0,65 / 0,17 s); server: 480 op to'liq tekshiruvli push
     < 10 s (~1,1 s); solver 2000 tugun < 500 ms (2-faza); PDF 250 o'lchov (6-faza).
  6. **Accessibility:** barcha asosiy ekranlar va dialoglar Flutter guideline'lari bilan testlanadi (Android tugma ≥ 48 dp,
     yorliqli tugmalar — TalkBack, matn kontrasti); tizim shrifti ×2 da toshib chiqish yo'q; rang juftliklari WCAG AA
     (≥ 4,5:1) hisoblab tekshiriladi.
  7. **Mustaqil ko'rik tuzatishlari (F-09…F-19):**
     - *Ajratish rejasi:* holat o'tishlari server tomonida (DRAFT → APPROVED/EXECUTED/CANCELLED/STALE,
       APPROVED → EXECUTED/CANCELLED/STALE; EXECUTED, CANCELLED, STALE — yakuniy). APPROVED/EXECUTED — LEAD/ADMIN ning
       imzolangan `PLAN_APPROVED` hodisasi bilan (`actor_id = approved_by`, payload `{id, graph_snapshot_hash,
       steps_sha256}`); EXECUTED — barcha `PLAN_STEP_DONE` va `PLAN_EXECUTED` bilan. Mazmun ustunlari (qadamlar,
       maqsad, graf hash'i, `deleted`, tasdiqlovchi) yaratilgandan keyin o'zgarmaydi (`plan_immutable`). Yakuniy holatdan
       chiqish urinishi rad etilmaydi — server versiyasi yutadi (`rev` oshiriladi, pull'da qurilmaga qaytadi): ikki qurilma
       bir vaqtda bajarsa/bekor qilsa, serverga birinchi yetgani qoladi va qurilma to'xtab qolmaydi.
     - *Protokol:* qoidalar serverdagi yozuvlar bo'yicha — payload'dagi o'lchovlar sessiyaning amaldagi (almashtirilmagan)
       o'lchovlariga aynan teng (ID, natija, qiymat, asbob, vaqt); asbob guvohnomasi, litsenziya muddati, norma tekshiruvi
       bazadan; `signed_at` protokol yaratilishidan ≤ 16 daq oldin. QR token = `sha256(qr_sig)[:32]`,
       `qr_sig = Ed25519("zanjir.qr/1\n<org_id>\n<raqam>")` (vektor `protocol_signature.json`): token oldindan
       bilinmaydi va boshqa tashkilot uni band qila olmaydi. Raqam formati qat'iy va qurilma belgisi bilan.
       `PROTOCOL_SIGNED` — imzolovchi va uning qurilmasidan.
     - *Sinxronlash:* `clock_skew` faqat LWW jadvallariga (append-only imzolangan yozuvni rad etish qurilmani abadiy
       to'xtatardi); paket rad etilsa ham pull bajariladi va qotgan yozuv (`SyncRejected`: jadval, ID, sabab) UI'da
       ko'rsatiladi; refresh bitta oqimda (parallel so'rovlar reuse detection'ni ishga tushirmaydi); NaN/Infinity va
       2^53 dan katta son — aniq rad etish (500 emas); laboratoriya rekvizitlari va sozlamalari o'zgarishi imzolangan
       `LAB_UPDATED`/`SETTINGS_CHANGED` hodisasisiz qabul qilinmaydi.
- **Oqibat:** SQLite shifrlanmagan, sertifikat pinning va lokal PIN yo'q — qoldiq xavflar (R-01…R-10), pilotdan keyin
  qayta ko'riladi. Android sozlamalari (zaxira, cleartext, imzo) bu muhitda build qilinmagan — 12-fazada tekshiriladi.
  QR token formati o'zgardi (tasodifiy → imzodan) — ilova va server bir vaqtda yangilanadi (hali production yo'q).

## ADR-0015: Deploy (11-faza) — Docker Compose, Caddy, rollar, shifrlangan zaxira

- **Sana:** 2026-10-27 · **Holat:** qabul qilingan (11-faza).
- **Kontekst:** Prompt 9-bo'lim, 11-faza: Dockerfile'lar, compose (staging + prod), Caddy, deploy'da Alembic, shifrlangan
  kunlik `pg_dump` + tiklash, `DEPLOY.md`, `RUNBOOK.md`; mezon — staging bitta buyruq bilan ko'tariladi, zaxiradan tiklash
  sinovdan o'tgan. 2-inson darvozasi (domen, server, SMTP/SMS) hali yopilmagan — prod faqat tayyorlanadi.
- **Qaror:**
  1. **Bitta `compose.yaml`, muhit — env faylda.** Staging va prod farqi (domen, TLS, portlar, ro'yxatdan o'tish,
     chegaralar, zaxira muddati) `deploy/environments/<muhit>.env` da; har muhit alohida Compose loyihasi. Compose
     "profillari" o'rniga shu: ikki muhitda xizmatlar tarkibi bir xil, prod'ga staging'da sinalmagan narsa kirmaydi.
  2. **`deploy/zanjir` CLI** — `up` (build → `migrate` → `api` → `caddy` → `backup`, `--wait` sog'liq tekshiruvlari bilan),
     `backup`, `restore --confirm`, `keygen`. Staging'da birinchi `up` maxfiy qiymatlarni (`od /dev/urandom`) va sinov age
     kalitini o'zi yaratadi; prod'da `<...>` qolsa ishga tushmaydi.
  3. **Migratsiya deploy'da** — alohida bir martalik `migrate` xizmati `zanjir_owner` bilan (superuser emas); `api` faqat
     u muvaffaqiyatli tugagach. Rollar `db/init/10-roles.sh` da: `zanjir_owner` (egasi), `zanjir_app` (NOLOGIN, RLS),
     `zanjir_api` (login, faqat `zanjir_app` a'zosi); `postgres` superuser'i tarmoqdan yopiq (`peer`).
  4. **Caddy** — TLS (prod: ACME, staging: ichki CA), HSTS, `Server` sarlavhasi yo'q, `/metrics` tashqariga 404, kirish
     logi o'chiq (URL'da QR token; ilovaning JSON logi tokenni yashiradi). `api` faqat ichki tarmoqlarda, bitta jarayon
     (R-02), root emas, faqat o'qiladigan FS, `cap_drop: ALL`, `no-new-privileges`. Baza `internal` tarmoqda (internetsiz).
  5. **Zaxira — `pg_dump -Fc | age -r <ochiq kalit>`**: serverda faqat ochiq kalit (server buzilsa ham zaxira ochilmaydi),
     maxfiy kalit operatorda. O'z kriptografiyamiz yo'q — `age` (X25519 + ChaCha20-Poly1305). Kunlik 21:30 UTC, muddat
     bo'yicha tozalash, `.sha256`. `restore.sh` faqat bo'sh bazaga.
  6. **Image'lar digest bilan qotirilgan**, registry `ZANJIR_REGISTRY` bilan almashtiriladi (ko'zgu boshqa image bera
     olmaydi). TLS'ni tekshiruvchi proksi ortida build — ixtiyoriy BuildKit secret `build_ca` (image'ga kirmaydi).
  7. **Qabul sinovi** — `deploy/check-staging.sh` (CI `zanjir-deploy`): bitta buyruq bilan ko'tarish, HTTPS smoke, Dart E2E
     (7 stsenariy) staging'ga TLS orqali, shifrlangan zaxira (ochiq matn yo'qligi tekshiriladi), yangi PostgreSQL'ga tiklash
     va `zanjir restore` — har jadval soni, mazmun md5 va sxema bir xil.
- **Oqibat:** Bitta server, bitta `api` jarayoni (rate limiting xotirada); gorizontal kengayish — Redis va ko'p nusxa
  (keyingi bosqich). Zaxira tashqi nusxasi va monitoring (Prometheus/alerting) — operator qarori, RUNBOOK'da tavsiya.
  Prod deploy, SMTP/SMS provayderi — 2-darvozadan keyin.

## ADR-0016: Release (12-faza) — AAB, imzo, versiyalash, AAB tekshiruvi, Play internal testing

- **Sana:** 2026-10-27 · **Holat:** qabul qilingan (12-faza).
- **Kontekst:** Prompt 9-bo'lim, 12-faza: Android imzolash konfiguratsiyasi, AAB, versiyalash, Play internal testing
  tayyorgarligi, pilot yo'riqnomasi; mezon — `flutter build appbundle --release` muvaffaqiyatli, release checklist to'liq.
  3-darvoza: keystore'ni foydalanuvchi yaratadi, Play'ga u yuklaydi.
- **Qaror:**
  1. **Ikki skript.** `app/tool/build_release.sh` — haqiqiy release: faqat foydalanuvchi `key.properties` bilan, toza git
     daraxti, teg = pubspec versiyasi, **normalar release darvozasi** (`check_norms.py --release`), analyze + testlar, https
     server; chetlab o'tish parametri yo'q. `app/tool/build_check.sh` — texnik tekshiruv: vaqtinchalik papkada bir martalik
     kalit (`CN=ZANJIR build check - NOT FOR RELEASE`), oxirida o'chiriladi; haqiqiy `key.properties` bo'lsa ishlamaydi;
     natija tarqatilmaydi (Play'ga yuklansa, o'sha kalit upload kaliti bo'lib qolardi — shu sababli CI artefakt saqlamaydi).
  2. **Play App Signing + upload kaliti.** Ilova imzo kalitini Google saqlaydi; foydalanuvchi upload kaliti yo'qolsa ham
     ilova yo'qolmaydi (Play orqali almashtiriladi).
  3. **AAB tekshiruvi** (`verify_aab.sh`, har build'da): imzo va sertifikat (debug emas), manifest (`allowBackup=false`,
     cleartext yo'q, `networkSecurityConfig`, `debuggable` yo'q, SDK 24/36, versiya), ruxsatlar ro'yxati (faqat
     ruxsat etilganlar; har bir `uses-permission` o'qilganini tekshiradi), R8 mapping, uchta ABI, `libapp.so` da DWARF yo'q,
     Dart nomlari ochiq emas. Tekshiruvlarning o'zi salbiy holatda sinalgan (debug sertifikat → ❌).
  4. **Versiyalash:** `X.Y.Z+N` (SemVer + qat'iy oshuvchi `versionCode`), teg `zanjir-vX.Y.Z`; server avval yangilanadi.
  5. **Ikonka** — `app/tool/gen_icons.py` (bitta geometriya → adaptive vector, eski PNG'lar, Play 512 px), Myrep dark
     ranglari, Anthropic brend belgilarisiz.
  6. **CI `zanjir-release`:** har PR'da `build_check.sh` (shellcheck, ikonkalar); `release` — faqat qo'lda, `zanjir-v*` teg
     ustida, himoyalangan `release` muhiti va `ZANJIR_UPLOAD_*` secrets bilan (foydalanuvchi xohlasa; lokal build ham teng).
- **Oqibat:** Birinchi haqiqiy release 1-darvoza (normalar tekshiruvi) va 3-darvoza (kalit) yopilgach mumkin — hozir
  `build_release.sh` normalar darvozasida ataylab to'xtaydi. Play listing va maxfiylik siyosati — qoralama (`docs/PLAY_LISTING.md`,
  `docs/PRIVACY.md`), huquqshunos tekshiradi. Haqiqiy qurilmada qo'lda sinov — checklist'da (emulyator testi CI'da).

## ADR-0017: To'liq oflayn ilova (13-faza) — server, sinxronlash va 2-darvoza olib tashlandi

- **Sana:** 2026-10-30 · **Holat:** qabul qilingan (foydalanuvchi qarori: "2-darvozani umuman olib tashlaymiz! Ilova to'liq
  offlayn bo'lsin!").
- **Kontekst:** 7–11-fazalarda server (FastAPI + PostgreSQL), sinxronlash va deploy qurilgan edi. Foydalanuvchi serverdan
  butunlay voz kechdi. Variantlar so'raldi; tanlov: server va deploy kodini **butunlay o'chirish**, **shifrlangan zaxira
  fayli**, xodimlar o'rtasida **fayl almashish**.
- **Qaror:**
  1. `server/`, `deploy/`, `tools/e2e/`, ilovadagi kirish/taklif/sinxronlash ekranlari, `ServerApi`, `SyncEngine`,
     `ServerAccount` o'chirildi (git tarixida qoladi). `INTERNET` ruxsati release manifestida yo'q; `verify_aab.sh` uni
     **taqiqlaydi** (kutubxona qo'shsa ham build tekshiruvdan o'tmaydi). debug/profile manifestlaridagi INTERNET — faqat
     Flutter vositalari uchun.
  2. Lokal baza v5: sinxronlash navbati (`sync_outbox`) va uning 22 trigger'i o'chiriladi; ma'lumot va append-only
     triggerlariga tegilmaydi (migratsiya testi).
  3. Kripto vektorlarining mustaqil Python implementatsiyasi serverdan `tools/vectors/zanjir_refcrypto` ga ko'chirildi
     (o'z `uv` loyihasi, testlari va CI job'i) — Dart kriptosi avvalgidek ikkinchi implementatsiya bilan tekshiriladi.
  4. QR havola — faqat ilova ichida (`zanjir://app/v/<token>`); ochiq tekshirish veb-sahifasi yo'q.
  5. Telefon yo'qolsa ma'lumot yo'qolmasligi uchun — parol bilan shifrlangan zaxira fayli; xodimlar o'rtasida — imzolangan
     ma'lumot almashish fayli (import serverdagi tekshiruvlarni telefonda bajaradi). Tafsilotlar — shu ADR ga 13-faza
     davomida qo'shiladi.
  6. 3-darvoza: upload kalitini foydalanuvchi so'rovi bilan Claude yaratdi (PKCS12, RSA 4096, alias `zanjir-upload`) va
     foydalanuvchiga topshirdi; keystore va parol repoda yo'q. Play Console'ga yuklash — foydalanuvchi.
  7. **Shifrlangan zaxira** (`zanjir_data/lib/src/backup/backup.dart`, format `zanjir.backup/1`):
     `"ZNJB" | 0x01 | uint32 BE sarlavha uzunligi | sarlavha JSON | shifrmatn | MAC`. To'lov — butun lokal baza
     (`VACUUM INTO` nusxasi, gzip). Kalit — paroldan Argon2id (64 MiB, t=3, p=1; o'qishda chegaralar 8–256 MiB, t 1–10,
     p 1–4 — zararli fayl telefon xotirasini to'ldirmasin), shifr — ChaCha20-Poly1305, AAD = sarlavha bilan prefiks
     (sarlavhani o'zgartirsa ochilmaydi). Parol kamida 10 belgi, hech qayerda saqlanmaydi; yo'qolsa zaxira ham yo'qoladi.
     Kalit hosil qilish va shifrlash alohida isolate'da (UI qotmaydi). Sarlavhada shaxsiy ma'lumot yo'q (sana, sxema
     versiyasi, KDF, tuz, nonce).
     Tiklash faqat **bo'sh** ilovaga: yaxlitlik (`PRAGMA integrity_check`), eski sxema joriy versiyagacha migratsiya qilinadi,
     tashkilotning **barcha** qurilma audit zanjirlari tekshiriladi (buzilgan bo'lsa — rad), so'ng barcha jadvallar ustun
     nomlari bo'yicha nusxalanadi. Qurilma maxfiy kaliti zaxirada **yo'q**: tiklangan telefon yangi qurilma sifatida
     ro'yxatdan o'tadi va `BACKUP_RESTORED` hodisasini (zaxira sanasi, SHA-256, oldingi qurilma) yozadi — nusxa, yangi
     qurilma va hodisa bitta tranzaksiyada. Eski qurilmaning imzolari tekshiriladigan holda qoladi; uning kaliti endi
     ishlatilmaydi (telefon yo'qolgan bo'lsa ham undagi kalit bilan yangi yozuvlar boshqa telefonlarga faqat almashish
     fayli orqali tushishi mumkin — almashishda bekor qilish, 13-faza 3-bosqich).
     Ilova: Sozlamalar → "Zaxira nusxa" (oxirgi zaxira sanasi; hali bo'lmasa ogohlantirish), boshlang'ich ekranda
     "Zaxiradan tiklash". Fayl tizim oynasi orqali saqlanadi/tanlanadi (`file_picker`, Storage Access Framework —
     xotira ruxsati kerak emas; AAB tekshiruvi ruxsat qo'shilmaganini tasdiqlaydi).
- **Oqibat:** Markaziy saqlash, tashkilot bo'yicha RLS, server tomonidagi ikkinchi tekshiruv qatlami (ADR-0011, ADR-0014
  server qismlari) endi yo'q — ularning o'rnini import tekshiruvlari va zaxira egallaydi; ADR-0011, ADR-0012, ADR-0015
  tarixiy. Ma'lumot laboratoriya telefonlarida qoladi (lokalizatsiya talabi soddalashadi). Tahdid modeli qayta ko'rib
  chiqiladi (`docs/SECURITY.md`).
