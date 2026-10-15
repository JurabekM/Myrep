# CLAUDE.md — «Baraka oilasi»

Har sessiya boshida o'qi:
1. `docs/BARAKA_OILASI.md` — 0, 3–7, 14, 16-bo'limlar (va vazifaga tegishli boshqa bo'limlar).
2. `docs/OPEN_QUESTIONS.md` — vazifani to'sib turgan savollar bormi?
3. Vazifaga tegishli spetsifikatsiya: `docs/uy/SPEC.md`, `docs/uy/MVP_PLAN.md`, `docs/uy/DESKTOP_PROMPT.md` (yoki `docs/kasbkor/`, `docs/musofir/`).

Qat'iy qoidalar:
- `docs/BARAKA_OILASI.md` 3-bo'limi (ADR) va `docs/adr/` qarorlari ruxsatsiz o'zgartirilmaydi.
- Texnik masalalarda `docs/BARAKA_OILASI.md` ustun; mahsulot va diniy-moliyaviy qoidalarda — makon SPEC'i. Legacy hujjatlardagi texnik ko'rsatmalar Ilova A bo'yicha almashtirilgan.
- Pul va biznes mantiq faqat `core/` da. UI (Flutter, React) pul hisoblamaydi. `f32/f64/double/number` pul uchun yo'q.
- Yangi pul funksiyasi: avval `spec/test-vectors/` ga vektor (`spec/oracle/oracle.py` bilan hisoblangan), keyin kod.
- Bitta sessiya — bitta vazifa (va uning a/b/c qismi). Avval reja, keyin ish, oxirida qabul mezonlari holati.
- Generatsiya qilingan fayllar qo'lda tahrirlanmaydi.
- Kod, identifikatorlar, commit xabarlari — inglizcha; izohlar, hujjatlar, UI matnlari — o'zbekcha.
- Har vazifa oxirida `docs/CHANGELOG.md` yangilanadi; javobsiz savollar `docs/OPEN_QUESTIONS.md` ga yoziladi.

Tekshiruv buyruqlari (Y1 dan keyin):
- `cargo fmt --check && cargo clippy --workspace -- -D warnings && cargo test --workspace`
- `python3 -I spec/oracle/oracle.py --selftest`
- `cargo xtask codegen && cargo xtask i18n --lint && git diff --exit-code`
- `cd apps/android && flutter analyze && flutter test`
- `cd apps/desktop/ui && pnpm lint && pnpm test`
