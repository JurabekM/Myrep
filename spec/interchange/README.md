# `.baraka` almashish formati (telefon ↔ desktop)

Mobil va desktop uchun **umumiy**. DESKTOP_PROMPT.md 6.3, SPEC 2F.6.

## Konteyner (fayl baytlari)

| Oraliq           | Uzunlik | Mazmun                                                   |
| ---------------- | ------- | -------------------------------------------------------- |
| 0–7              | 8       | magic `BARAKA01`                                         |
| 8–19             | 12      | Argon2id parametrlari: `m_cost_kib`, `t_cost`, `p_cost` (u32 LE) |
| 20–35            | 16      | tuz                                                      |
| 36–59            | 24      | XChaCha20-Poly1305 nonce                                 |
| 60…              | n+16    | shifrmatn + Poly1305 tegi                                |

- Kalit = Argon2id(parol UTF-8, trim qilingan; tuz; parametrlar) → 32 bayt. Tavsiya: 19 456 KiB, t=2, p=1.
- AAD = birinchi 36 bayt (magic + parametrlar + tuz). Sarlavha o'zgartirilsa teg mos kelmaydi.
- Parol kamida 8 belgi. Noto'g'ri parol — `WRONG_PASSWORD`; buzilgan fayl — `CORRUPT_CONTAINER`.

## Ochiq matn

`export-format.schema.json` ga mos JSON (UTF-8). Jadval qatorlari bazadagi ustun nomlari bilan; pul — minor
birlikda butun son; sanalar `YYYY-MM-DD`; vaqtlar ISO 8601 (UTC).

## Birlashtirish qoidalari (import)

1. Yozuvlar `id` bo'yicha moslashtiriladi. `version` kattasi yutadi; teng bo'lsa `updated_at` kechrog'i yutadi.
   Kiruvchi yutqazsa va farq qilsa — ziddiyat (`LOCAL_NEWER`), mahalliy saqlanadi.
2. `deleted_at` (tombstone) oddiy maydon sifatida o'tadi — o'chirish shu orqali qo'llanadi.
3. `journal_entries` — har kelishuv uchun alohida zanjir: avval kiruvchi zanjirning xeshlari qayta hisoblanadi
   (`verify_chain`), so'ng mahalliy zanjir bilan umumiy oraliq solishtiriladi (`check_import`). Farq bo'lsa —
   **FORK**: butun import to'xtaydi, hisobotda kelishuv va birinchi farq ko'rsatiladi. Avtomatik birlashtirish yo'q.
   Mos kelsa — faqat davomi (`seq` > mahalliy soni) qo'shiladi. Jurnalga faqat hisob yurituvchi qurilma yozadi
   (`origin_device_id` kelishuvda).
4. `venture_periods` (yopilgan davrlar) va `signatures` faqat qo'shiladi; mavjud yozuv farq qilsa —
   `CLOSED_PERIOD_DIFFERS` / `SIGNATURE_DIFFERS` ogohlantirishi, o'zgartirilmaydi.
5. `agreements`: imzolangan (`SIGNED`) kelishuvning shu versiyasi (`answers_json`) import orqali o'zgarmaydi —
   `SIGNED_VERSION_DIFFERS`. O'zgarish faqat yangi versiya orqali.
6. Inkremental eksport: `since` berilsa faqat `updated_at > since` (yo'q bo'lsa `created_at > since`) qatorlar;
   ikkalasi ham bo'lmagan jadvallar to'liq chiqadi.
7. Import avval **dry-run** (ko'rik) sifatida hisoblanadi; foydalanuvchi tasdiqlagach qo'llanadi. Hamma yozuv
   bitta tranzaksiyada.

Mos test: `crates/storage/tests/interchange_flows.rs` (round-trip 1:1, fork, ziddiyat, inkremental),
`crates/security/src/container.rs` (konteyner), `src-tauri/src/sync.rs` (fayl + parol).
