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
