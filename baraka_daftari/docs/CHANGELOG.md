# CHANGELOG

## D1 + D2 — Poydevor (desktop)
- Cargo workspace (`desktop/`), `money` va `vectors` crate'lari, `src-tauri` (Tauri 2 + tauri-specta), `ui` (React 18 + Vite + TS strict + Tailwind 4 + i18next uz/ru + TanStack Query).
- `money`: `Money`, `Currency`, `allocate` (largest remainder), `percent_of`, `round_half_up`, `FxRate`, `format_money`. `float_arithmetic`, `unwrap_used`, `expect_used` — `deny`.
- `spec/test-vectors`: `allocate`, `percent_of`, `fx_convert`, `money_format`. Runner: `cargo test -p vectors`.
- CSP qat'iy (`unsafe-eval`/`unsafe-inline` yo'q), capabilities faqat `core:default`, shell/http/fs pluginlari yo'q.
- CI: `.github/workflows/baraka-desktop.yml` (fmt → clippy → test → vektorlar → frontend → build, qamrov ≥95%, NSIS).
- Kechiktirildi (keyingi vazifalar): `amortization.json` (D10), `profit_distribution.json` (D12) va boshqa suite'lar.

## D3 — Xavfsizlik va shifrlangan baza
- `security`: Argon2id (PIN) + OS keyring qurilma siri → HKDF → XChaCha20-Poly1305 bilan DB kalitini o'rash. Ikki omil: keyring o'chsa PIN bilan ochilmaydi, keyring bo'lsa ham PIN'siz ochilmaydi. Lockout (3-xatodan keyin 30 s, ikki baravar o'sadi, ≤1 soat, qayta ishga tushganda ham saqlanadi), `AutoLock` (5 daqiqa, sozlanadi), `zeroize`.
- `storage`: SQLCipher (`bundled-sqlcipher-vendored-openssl`), `rusqlite_migration`, sxema v1 (households, members, categories, incomes, expenses, assets + asset_snapshots, vault_transactions, allocation_rules, obligations, fx_rates), umumiy `Record` repository (insert/get/list/update/soft_delete, optimistik `version`).
- `domain`: `Meta`, `Clock`, `IdGen` (UUIDv7), enumlar va sxema v1 entity'lari.
- Tauri: `vault_state`, `setup_pin`, `unlock`, `lock`, `activity` commandlari; 5 soniyalik avto-qulf oqimi; `contentProtected` oynada yoqilgan.
- UI: `Gate` (qulfda kontent render qilinmaydi), `LockScreen` (PIN o'rnatish/ochish, kutish soniyalari), `Ctrl+L`.
- Kechiktirildi: Windows Hello (ixtiyoriy, OPEN_QUESTIONS), PIN almashtirish, tashqi keyring o'zgarishi bilan tiklash oqimi.

## D4 — Daromad, «Kelajagim», audit, «Kimning puli?», bosh sahifa
- **Vektorlar (avval vektor, keyin kod):** `unexplained_gap`, `streak`, `share_suggestion`, `money_parse` (+ runner'lar). Barchasi yashil.
- `money::parse_amount`: foydalanuvchi matni (`8 000 000`, `1500,50`) → minor; frontend pulni hisoblamaydi va parse qilmaydi.
- `domain` (sof): `suggest_share` (foiz / oylik aniq summa), `suggest_rate_increase` (progressiv: 4 hafta streak + 4 hafta shu stavkada → +1%), `compute_streak` (hafta jumadan boshlanadi), `unexplained_gap`, `month_result`, `whose_money`, pul olish pauzasi (`check_confirm`, 24 soat).
- **Sxema v2** (faqat `ADD COLUMN` + 1 jadval; v1 ma'lumotlari saqlanishi testlangan): `vault_transactions.source/income_id`, `obligations.kind/owner/creditor/remaining_minor`, `categories.owner`, `expenses.audit_month`, `withdrawal_requests`.
- Yangi `services` crate: `setup` (xonadon, a'zo, 11 standart kategoriya, «Kelajagim», 5% qoidasi), `income` (taklif + daromad va ajratma bitta tranzaksiyada), `rules`, `vault` (ro'molcha/boshlang'ich balans — bir marta, «o'zingizga to'langan»ga kirmaydi; pauzali pul olish), `audit` (oylik jami almashtiriladi, ikki marta hisoblanmaydi), `obligations` (doimiy to'lovlar + nasiya daftari), `home`.
- Tauri: 17 ta yangi command (`ledger.rs`), sessiya endi `Ctx` va barqaror `device_id` saqlaydi.
- UI: ilova qobig'i + navigatsiya, **bosh sahifa slot arxitekturasi** (birinchi slot — «o'zingizga to'ladingiz»), `Ctrl+N` tez kiritish (summa → Enter), Kelajagim sahifasi, Byudjet sahifasi va audit ustasi (faqat klaviatura: Enter/Shift+Enter/Esc), «Kimning puli?», majburiyatlar va nasiya. i18n kalitlari testi (uz/ru).
- Kechiktirildi / ataylab qilinmadi: daromadni tahrirlash/o'chirish, oila a'zosini tanlash (D6 oila rejimi), oylik davr boshlanish kuni sozlamasi, haftalik vazifa va juma bobi (D5), tauri-driver E2E (D15).

## D5 — Kontent dvigateli (5 bob)
- `baraka_daftari/content/ch01..ch05.json` (placeholder, asl matn ko'chirilmagan; format `content/README.md` da). Har bobda aniq 3 ta haftalik vazifa, «Daftar sahifasi» savoli, diniy bloklar `PENDING` (manba majburiy).
- Yangi `content` crate (sof): JSON yuklash va tekshirish (ID takrori, 3 vazifa, diniy blokda manba), **`visible_blocks` — `Release` rejimida tasdiqlanmagan diniy matn hech qachon chiqmaydi** (butun o'rnatilgan kontent bo'yicha test), `TaskTrigger` + `trigger_met`, `UnlockPolicy` + `decide`.
- Vektor: `chapter_unlock.json` (12 case) — mobil ham shunga mos bo'lishi shart.
- Sxema v3: `task_completions`, `chapter_progress`, `daftar_pages`, `settings` (partial UNIQUE indekslar: tombstone'lar to'qnashmaydi).
- `services::learning`: yo'l (`journey`), bob tafsiloti, qo'lda vazifa belgilash, Daftar sahifasi, sozlanadigan siyosat. Bob ochilishi odat asosida: faqat **tugagan** haftalar, oxirgi N haftaning kamida M tasida kamida K vazifa (standart 3/2/2); haftada ko'pi bilan bitta bob; vaqt o'zi yetmaydi (testlangan).
- Audit qayta kiritilganda yozuv yangilanadi (o'chirib qayta yaratilmaydi), shunda eski haftalar vazifasi «audit» yo'qolmaydi.
- Tauri: 5 command (`study.rs`); UI: «Boblar» sahifasi (o'qish, Daftar sahifasi, vazifalar, ochilish sharti sozlamasi), bosh sahifadagi «haftalik vazifalar» va «juma qissasi» slotlari haqiqiy ma'lumot bilan.
- Kechiktirildi: audio, qissa matnlari (litsenziya), 6–12-boblar, bildirishnomalar (D7).

## D6 — Uch toifa, havas chegarasi, oila kengashi
- **Vektorlar:** `havas_status` (80% → NEAR, 100% → OVER; chegaralar yaxlitlanmagan aniq solishtiriladi), `habit_projection` (haftalik/oylik/yillik prognoz).
- **Sxema v4:** `member_credentials` (a'zoning shaxsiy PIN'i, Argon2id), `necessity_changes` (kim va qachon), `havas_limits`, `limit_consents`, `scheduled_treats`; `categories.is_charity/is_habit`, `expenses.note`.
- **Uch toifa:** barcha standart kategoriyalarga standart toifa; eski bazalarga idempotent to'ldiriladi (foydalanuvchi tanloviga tegilmaydi). Toifa o'zgarishi tarixga yoziladi. Xarajatda toifani alohida belgilash mumkin.
- **Havas chegarasi:** faqat **barcha `ADULT` a'zolar o'z PIN'i bilan** rozilik berganda faol; yangi taklif kelishilgunga qadar eski chegara amalda; kattalar qo'shilsa chegara yangi a'zo rozi bo'lguncha to'xtaydi; bola/kuzatuvchi rozilik bera olmaydi; eskirgan taklifga rozilik rad etiladi. Xato PIN urinishlari sekinlashtiriladi (vault bilan bir jadval). Bloklash yo'q — yumshoq ogohlantirish.
- **Sadaqa** havas ham, obro' ham hisobiga kirmaydi (toifasi qanday belgilanganidan qat'i nazar); **sovg'a** havas hisobiga kirmaydi; **qarz bilan qilingan havas** alohida ko'rsatiladi.
- **Hafta varag'i** (ommaviy kiritish, bitta tranzaksiya, izohdan kategoriya avtomatik), **Juma shirinligi**, **odatlar** statistikasi (oyiga/yiliga, faqat statistika).
- **Oila kengashi** (to'liq ekran, 4 qadam) va **PDF bayonnoma** (`typst`, DejaVu Sans ilovaga o'rnatilgan): ʻ/ʼ belgilari PDF matn snapshot testi bilan tasdiqlangan; foydalanuvchi matnlari typst string literal sifatida qo'yiladi (markup injection yo'q). PDF OS «saqlash» oynasi orqali Rust tomonida yoziladi.
- Dev profil: `debug = "line-tables-only"` (typst bilan `target/` 28 GB ga yetgan edi).
- Kechiktirildi: shaxsiy havas ulushi (a'zo bo'yicha), chop etish dialogi (D15 bilan), bildirishnoma («Juma shirinligi» eslatmasi — D7), bayonnomani ruscha chiqarish.

## D7 — Obunalar, konvertlar, «Qutqarilgan pul», tray, CSV import
- **Vektorlar (avval):** `rescued_money` (manfiy farq → 0), `subscription_cost`, `forgotten_subscription` (≥60 kun), `envelope`, `money_parse_signed`.
- **Sxema v5:** `subscriptions`, `envelopes`, `envelope_periods`, `savings_rescues` (haftaga bir marta HAVAS_DROP).
- **Obunalar:** oylik/yillik jami, «unutilgan» ogohlantirish, bekor qilish — bir oylik narx qutqarilgan pul bo'ladi.
- **Konvertlar:** haftalik chegara, qolgan summa, naqd to'ldirish, hafta yopilganda farq.
- **«Qutqarilgan pul»:** havas xarajatining o'tgan haftaga nisbatan kamayishi; hafta uchun bir marta da'vo qilinadi; «Kelajagim»ga o'tkaziladi («Qutqarilgan pul» izohi bilan).
- **Tray + `Ctrl+Alt+B`** tez xarajat oynasi: daftar qulfli bo'lsa hech qanday summa/ma'lumot so'ralmaydi (UI testi bilan tasdiqlangan).
- **CSV import:** fayl faqat Rust tomonida ochiladi; ustunlarni moslash, sinov (dry-run), takrorlarni o'tkazib yuborish, bitta tranzaksiya.
- Kechiktirildi: Windows'da tray/qisqa tugma amaliy sinovi, bildirishnomalar, boshqa kodirovkali CSV.
