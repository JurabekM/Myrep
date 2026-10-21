# ADR-0001. «Baraka oilasi»: umumiy Rust yadro, Flutter (Android) va Tauri (desktop)

- **Holat:** QABUL QILINDI
- **Sana:** 2026-10-15
- **O'rnini bosadi:** `docs/uy/SPEC.md` 4.1–4.2 (mobil stek: Drift, Dart `core/money`) va `docs/uy/DESKTOP_PROMPT.md` 3.1 (desktop ichidagi `crates/`).

## Kontekst
- Loyiha uchta mahsulotdan (Uy, Kasb-kor, Musofir) va ikki platformadan (Android, desktop) iborat. Kelajakda relay server va «Guvoh» mikrokontroller qurilmasi qo'shiladi.
- Avvalgi rejada pul va domen mantig'i ikki tilda (Dart va Rust) yozilib, mosligi umumiy test vektorlari bilan tekshirilishi kerak edi.
- Tahlil ko'rsatdiki, vektorlar faqat yozilgan holatlarni qamraydi. Masalan, `allocate` ning manfiy summadagi xulqi aniqlanmagan edi va Dart (`~/`) bilan Rust (`div_euclid`) osongina har xil natija berishi mumkin edi: `[-33,-33,-34]` va `[-34,-33,-33]`.
- Uchta mahsulot × ikki platforma × ikki til = domen mantig'ining olti marta takrorlanishi xavfi.

## Qaror
1. Pul, jurnal, kelishuvlar, domen qoidalari, saqlash, kalitlar, PDF va almashish — **bitta Rust yadroda** (`core/`).
2. **Android:** Flutter UI + Kotlin platforma xizmatlari; yadroga `flutter_rust_bridge` v2 orqali ulanadi. Drift va Dart `core/money` ishlatilmaydi.
3. **Desktop:** Tauri 2 + React + TypeScript; yadroga `tauri-specta` orqali ulanadi.
4. Ikkala adapter ham faqat `app` (use-case) crate'ini chaqiradi.
5. `money` va `journal` crate'lari `no_std` — kelajakda RP2350 proshivkasida qayta ishlatiladi.
6. Bitta monorepo; i18n, dizayn tokenlari, PDF shablonlari va kontent — `shared/` da yagona manba.

## Ko'rib chiqilgan muqobillar
| Variant | Nega tanlanmadi |
|---|---|
| Rust yadro + Flutter (ikkala platforma) | Desktopda Excel uslubidagi jadvallar va klaviatura UX'i zaifroq; desktop ADR'ini qayta yozish kerak. **Zaxira varianti** sifatida qoladi |
| Kotlin Multiplatform + Compose | Mavjud ADR'larning deyarli hammasi qayta yoziladi; desktopda JVM (katta hajm, sekin start); mikrokontrollerda ishlamaydi |
| Tauri 2 (Android ham) | Arzon Android telefonlarda WebView sekin; vidjet, Keystore va WorkManager baribir Kotlin'ni talab qiladi |
| Avvalgi reja (Dart + Rust, vektorlar bilan) | Domen mantig'i takrorlanadi; chekka holatlarda ajralish xavfi; ish hajmi ikki baravar |

## Oqibatlar
**Ijobiy**
- Pul hisobi va jurnal xeshlari barcha platformalarda konstruksiya bo'yicha bir xil.
- PDF'lar (typst) telefonda va desktopda bir xil.
- Mavjud ADR'larning ~90% saqlanadi (Flutter, Kotlin, Tauri, React, SQLCipher, vektorlar).
- Yadro relay serverda va qurilmada qayta ishlatiladi.

**Salbiy va ularni yumshatish**
- Build murakkablashadi (NDK, `cargo-ndk`, FRB codegen) → Y1 da CI'da ishlaydigan skelet.
- Rust o'zgarganda Flutter hot reload ishlamaydi → domen va UI ishlari alohida sessiyalarda.
- To'rtta til (Rust, Dart, TS, Kotlin) → domen faqat Rust'da, UI qatlamlari ataylab yupqa.
- APK hajmi o'sadi → CI'da hajm byudjeti (≤ 40 MB, OQ-T1).
- Test vektorlari endi ikki implementatsiyani emas, **Rust va mustaqil Python oracle**ni solishtiradi; qo'shimcha ravishda Dart'dan FFI orqali ishga tushiriladi.
