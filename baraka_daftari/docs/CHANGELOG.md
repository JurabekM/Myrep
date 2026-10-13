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

## D8 — 3-qonun: qorovul/o'sadigan pul, narx daftari, darvoza, ribo filtri
- **Vektorlar (avval):** `emergency_target` (31 mln namunasi), `guard_months`, `personal_inflation` (5625 bp namunasi), `readiness_gate` (to'liq matritsa), `allocation_priority`, `purchasing_power`.
- **Sxema v6:** `assets.vault_type` (mavjud «Kelajagim» → `QOROVUL`, balans va tranzaksiyalar o'zgarmaydi — migratsiya testi), `incomes.source_type` (`TER|MOL|TAVAKKAL|RIBO`), `price_items`, `price_points`, `gate_bypasses`. Eski bazalarga `OSADIGAN` aktivi idempotent qo'shiladi.
- **Qorovul maqsadi:** oxirgi 3 tugagan oyning `ZARUR+KERAK` xarajati + doimiy majburiyatlar o'rtachasi × 6 (3 oy — birinchi bosqich). Ajratma avval qorovulga; ortig'i faqat darvoza ochiq bo'lsa «o'sadigan»ga.
- **Darvoza:** qorovul ≥ 6 oy **va** (foizli qarz yo'q yoki reja bor). Qulfli ekranda sabablar va progress; tasdiq bilan **ongli chetlab o'tish** (mahalliy qayd, qaytarish mumkin).
- **Pul olish:** «bu haqiqatan favqulodda holatmi?» tasdig'i Rust tomonida majburiy; faqat qorovuldan olinadi.
- **Narx daftari:** savat (og'irlik %), narxlar tarixi, shaxsiy indeks, haftalik eslatma va ketma-ketlik. **«Sichqon kemirgani»:** real qiymat va mahsulot miqdori (foydalanuvchi kiritgan yillik o'sish bilan), har doim keyingi qadam bilan yakunlanadi.
- **Ribo filtri:** daromad turi (ixtiyoriy; `RIBO` alohida belgilanadi); i18n matnlarida taqiqlangan iboralar testi (uz/ru).
- Kechiktirildi: rasmiy CPI, narx eslatmasi bildirishnomasi (D15), o'sadigan pul funksiyalari (keyingi boblar), qarz inventari (D9 — hozircha darvoza qarz holatini qo'lda bayon qilish bilan).

## D9 — 4-qonun: qarz inventari, haqiqiy narx, friction, tilxat
- **Vektorlar (avval):** `debt_schedule` (teng bo'laklar va jadval jami/ustamasi), `debt_cost` (Karim aka: 40 mln → 69 mln), `debt_burden`.
- **Sxema v7:** `debts`, `debt_instalments`, `debt_payments`, `receivables`, `goals`, `loan_receipts`.
- **Qarz inventari:** bank / do'kon / qarindosh / do'st / boshqa; **to'lov jadvalisiz qarz saqlanmaydi** (bo'sh, asosiydan kam yoki musbat bo'lmagan qator rad etiladi — testlangan). Ustama alohida kiritilmaydi: u jadval jamidan chiqadi (jami − asosiy); ustama bor qarz qizil belgilanadi.
- **Haqiqiy narx:** «asosiy → jami → ortiqcha» va ulush; **imkoniyat narxi** — ortiqcha summa foydalanuvchi maqsadlariga necha marta teng.
- **Friction («to'xta va o'yla»):** zarurat/hashamat, foizsiz muqobil, oylik yukning daromadga nisbati; natija qarz yozuvida saqlanadi.
- **Berilgan qarzlar (`Receivable`):** foiz maydoni **tipda ham, bazada ham yo'q** (test: maydonlar to'liq sanab o'tilgan + sxema ustunlari tekshiruvi); muddat kelganda yumshoq eslatma.
- **Tilxat PDF** (typst): tomonlar, summa, jadval, guvohlar, imzo joylari; imzo — chop etib qo'lda yoki sichqoncha/pero bilan chizilgan PNG. Matn snapshot testi (ʻ/ʼ saqlanadi), markup injection testi, noto'g'ri/katta rasm rad etiladi.
- **Darvoza (D8) bilan bog'lanish:** «foizli qarz» endi qarz inventaridan aniqlanadi (qo'lda belgi olib tashlandi); faqat «reja bor» bayoni qoldi (D10 gacha).
- Qarz to'lovi «Qarz to'lovi» (ZARUR) xarajati sifatida yoziladi; bosh sahifada faol qarz kartochkasi.
- Kechiktirildi: `DEBT_RECOVERY` 70/20/10 va to'lov rejalovchisi, annuitet/differensial simulyator, `DebtContributor` (D10); sotiladigan buyumlar (D10 bilan); ikki tomonlama tasdiq havolasi (sinxronlash/D14 gacha — hozir qo'lda belgi); do'kon nasiyasini `Debt` ga to'liq birlashtirish.

## D10 — Qarzdan chiqish: 70/20/10, rejalovchi, simulyator, «Qarzsiz kun»
- **Vektorlar:** `amortization.json` (amort-001…003 spetsifikatsiya raqamlari **to'liq jadvallar bilan** yashil: 322 147 684 / 14·9·8 oy / jami foiz 610 067 573·397 018 667·341 756 885; 9-oy misoli), qo'shimcha amort-004…006 (extra qoldiqdan katta, 0% stavka, kichik P) va differensial diff-001…003; `debt_recovery_split.json` (70/20/10 va jamg'arma ≥ 1%); `payoff_plan.json` (bir necha qarz, snowball, bir martalik manba).
- **Domen:** `amortize` (annuitet to'lovi aniq kasrda — `num-bigint`, `typst` orqali allaqachon lock'da), `recovery_split`, `payoff_plan`, `closing_order`.
- **`DEBT_RECOVERY` rejimi:** faol qarz bo'lsa taklif; 70/20/10 oila tomonidan sozlanadi, jamg'arma ulushi **0 bo'la olmaydi** (min 1%, Rustda tekshiriladi); rejimda daromaddan ulush taklifi = jamg'arma qismi; **barcha qarz yopilganda avtomatik `STANDARD` ga qaytadi** va bo'shagan ulushni qorovul pulga yo'naltirish taklif qilinadi.
- **Rejalovchi:** odatiy va tezlashtirilgan grafik yonma-yon, necha oy erta, «qarzsiz kun»; manbalar — 20% ulush, qutqarilgan pul, sotiladigan buyumlar; yopish tartibi (standart: ustamali qarz — eng yuqorisidan, so'ng qarindosh/do'st — muddati yaqinidan; qo'lda o'zgartirish ↑↓).
- **Kalkulyator:** annuitet/differensial «nima bo'ladi, agar» (Anvar: 14 → 9 oy); **ECharts** grafigi va **virtualizatsiyalangan katta jadval** (1200 oygacha), kalkulyator kerak bo'lganda yuklanadi.
- **To'lovchilar** (`DebtContributor`): a'zoning oylik ulushi va haqiqiy to'lagan jami. **Sotiladigan buyumlar:** sotilgach tushum bir bosishda qarzga qo'shimcha to'lov.
- Sxema v8: `debt_contributors`, `sellable_items`.
- Kechiktirildi: taklif havolasi orqali ishtirokchi (sinxronlash/D14), to'y rejasi bilan bog'lash (D11), e'lon saytlariga eksport.

## D11 — Marosim rejalovchisi
- **Vektorlar (avval):** `ceremony_totals` (qator jami, manbalar bo'yicha yig'indi, qarz ulushi bp), `repay_months` (qarz muddati: D10 annuitet formulasi bo'yicha oylik imkoniyatga sig'adigan eng kichik n; 600 oydan uzun → `TOO_LONG`).
- **Sxema v9:** `ceremony_plans`, `ceremony_lines`.
- **Byudjet:** marosim turlari (to'y, beshik, sunnat, ma'raka...), qatorlar `miqdor × birlik narxi`, moliyalash manbasi — jamg'arma / oila hissasi / kutilayotgan to'yona / **qarz**.
- **Asosiy qoida:** qarz bilan moliyalangan qator bo'lsa, «Buni qarzsiz qanday o'tkazamiz?» oilaviy muhokamasi (xulosa matni majburiy) o'tkazilmaguncha `CONFIRMED` ga o'tib bo'lmaydi; sana ham shart. Domen darajasida (`check_ceremony_confirm`), servisda va UI da testlangan. Tasdiqlangan rejaga qator qo'shilsa/o'zgarsa yoki sana olinsa — qoralamaga qaytadi.
- **Stsenariylarni solishtirish (2–3):** umumiy narx, eng qimmatdan qancha arzon, qarz va ulushi, **qaytarish muddati (D10 simulyatori formulasi)**, shu pulga erishiladigan muqobil maqsadlar (D9 `Goal`).
- **To'yona o'rniga:** yosh oila uchun maqsad (`Goal`) ochish (virtual).
- **Chop etiladigan smeta** (typst PDF): qatorlar, manbalar, qarz ogohlantirishi, muhokama xulosasi; matn snapshot testi (ʻ/ʼ), markup-injection testi.
- Kechiktirildi: mehmonlar hissasi uchun ulashiladigan havola (hamkor bank bilan), qatorni tahrirlash (hozir o'chirib qayta qo'shiladi), muhokamani oila kengashi PINlari bilan bog'lash.

## D12 — Sheriklik domeni, shartnoma, buyout
- **Vektorlar:** `profit_distribution.json` — **dist-001…004 spetsifikatsiya raqamlari bilan yashil** (+ dist-005…014: beparvolik, ko'p kapital egasi, xato holatlar); `buyout.json` (kamayib boruvchi sheriklik jadvali, teng bo'laklar).
- **Domen qoidalari (2E.1):** foyda — kelishilgan ulush; mudarabada zarar kapital egasi(lar)i zimmasida, ishchi 0 (faqat `negligence` + izoh bilan ishchi zimmasiga); musharakada zarar `capital_i / Σcapital`; ulushlar yig'indisi 100%; **kafolatli summa/daromad domen darajasida bloklanadi** («Bu sheriklik emas — ribo yoki qarz»): shartnoma ustasida kiritishga urinish rad etiladi va tushuntirish chiqadi.
- **Sxema v10:** `partnerships`, `partnership_parties`, `partnership_capital`, `partnership_signatures`, `partnership_versions`, `buyout_plans`, `buyout_payments`.
- **Shartnoma ustasi (2E.2):** tomonlar va rollar, kapital (pul/uskuna narxi bilan), ulushlar, muddat, hisobot davri, tugash va nizo tartibi, guvohlar. **Shartnomasiz sheriklik yo'q** (yozuv shartnoma bilan birga yaratiladi).
- **Tasdiqlar va versiyalash:** a'zo tomon o'z PIN'i bilan, tashqi tomon va guvoh qo'lda; tasdiq faqat shartnomaning **joriy versiyasi** uchun. **Shartlar o'zgarsa versiya oshadi, barcha imzolar qayta so'raladi**, faol sheriklik qoralamaga qaytadi (testlangan); versiyalar matn tarixi saqlanadi.
- **Gate (2E.6):** kapital **kiritish** tayyorgarlik darvozasiga bo'ysunadi (faollashtirishda tekshiriladi); kapital **qabul qilish** darvozasiz, lekin barcha kattalarning oilaviy roziligi (PIN) shart; UI mudarabada kapital qarz emasligini tushuntiradi.
- **Shartnoma PDF** (typst): tomonlar, kapital qatorlari, qoidalar, muddat, buyout, imzo va guvoh joylari (ilovada tasdiqlangan sanasi bilan); yurist/ulamo tasdig'idan o'tmagani ochiq yozilgan; matn snapshot testi (ʻ/ʼ), injection testi.
- **Buyout:** musharakada kapital egasi ulushini davrma-davr sotib olish: reja (teng bo'laklar) va haqiqiy to'lovlar jadvali, ulush vizualizatsiyasi, yakunda «sherik mustaqil bo'ldi».
- **Taqsimot hisobi** (foyda/zarar, beparvolik izohi majburiy). Avtomatik davr yopilishi va ledger — D13.
- Kechiktirildi: ledger/davrni yopish va buyout ayirmasini taqsimotga avtomatik qo'llash (D13), ikkinchi tomon masofadan tasdig'i (D14), shartnoma ulamo tasdig'i (`PENDING`).

## D13 — Korxona daftari, davr taqsimoti, «Hunardan ishga», taklif detektori
- **Vektorlar:** `venture_settlement.json` (buyout ayirmasi bilan davr taqsimoti), `craft_payback.json` (qaytim = ceil(capex / sof), sheriklik ulushidan keyin), `offer_check.json` (yashil/sariq/qizil, belgilar tartibi) — mustaqil Python hisobi.
- **Sxema v11:** `venture_periods`, `venture_entries`, `venture_attachments`, `venture_distributions`, `craft_ideas`, `craft_capex`; **yopilgan davr** SQLite triggerlari bilan ham o'zgarmas (servis qatlamidan tashqari ikkinchi himoya).
- **Kassa daftari:** kirim/chiqim yozuvlari (biznes puli uy budjetidan alohida), foring-major belgisi, chek/rasm dalili (PNG/JPEG/PDF, shifrlangan bazada), davrni yopish → avtomatik taqsimot (mudarabada beparvolik izohi), buyout ayirmasi taqsimotga qo'llanadi, davr hisoboti PDF (typst, snapshot testi). Kapital egasi uchun faqat o'qish; faol bo'lmagan sheriklikda yozuv yo'q.
- **Hunardan ishga:** asbob xarajati (CAPEX) + 3 senariy (yomon/o'rta/yaxshi), qaytim muddati, bir bosishda shartnoma qoralamasi.
- **Taklif detektori:** tekshiruv ro'yxati → yashil/sariq/qizil; ta'limiy ogohlantirish bilan (ribo filtri nomida «kafolatlangan foyda» iborasi ishlatilmaydi).
- UI: `Ledger` (sheriklik kartasida), `CraftsPage` («Hunardan ishga»), uz/ru matnlar, 7 yangi UI testi.


## D14 — `.baraka` eksport/import (telefon ↔ desktop)
- **Format:** `spec/interchange/` — `export-format.schema.json` (JSON Schema, test bilan jadval ro'yxati va sxema versiyasiga bog'langan), `README.md` (konteyner bayt tuzilmasi, birlashtirish qoidalari — mobil ilova uchun umumiy), `example-export.json`.
- **Konteyner** (`security::container`): `Argon2id(parol) → XChaCha20-Poly1305`, sarlavha AAD sifatida himoyalangan, KDF chegaralari tekshiriladi, parol ≥ 8 belgi; noto'g'ri parol — aniq xato (`WrongPassword`), buzilgan sarlavha — «bu .baraka fayli emas».
- **Hujjat** (`storage::interchange`): jadval nomlari va ustunlar faqat lokal sxemadan (PRAGMA) olinadi (SQL injection yo'q); FK bo'yicha topologik tartib; PIN xeshlari va qurilma sozlamalari eksport qilinmaydi; to'liq va inkremental (`updated_at > since`, tombstone'lar bilan).
- **Birlashtirish:** `id` bo'yicha; `version` katta yutadi, teng bo'lsa `updated_at`, teng bo'lsa lokal; tombstone qo'llanadi; teng versiyada turlicha tarkib — ziddiyat ro'yxati. **Yopilgan davrlar, taqsimotlar, imzolangan shartnoma versiyalari va imzolar import orqali o'zgarmaydi** (ziddiyat sifatida ko'rsatiladi). Seed yozuvlar (toifalar, «Men», «Kelajagim», qoida) tabiiy kalit bo'yicha ulanadi — dublikat yo'q; xonadon `id` si lokalga moslanadi. Bazaga sig'maydigan yozuv `REJECTED` bo'ladi. Oldindan ko'rish va qo'llash bir xil kod yo'lidan o'tadi (ko'rish — orqaga qaytariladigan savepoint).
- **Servis/Tauri:** `services::interchange`, `exchange.rs` (OS dialogi Rust tomonida; tanlangan fayl xotirada, parol qayta kiritilishi mumkin; `Zeroizing`).
- **UI:** «Almashish» sahifasi: eksport (parol + takror, to'liq/inkremental), import (fayl → tekshirish → ziddiyatlar → birlashtirish).
- **Testlar:** round-trip 1:1 (yangi baza), seed bazaga import (dublikatsiz), preview = apply hisoboti, versiya/tombstone, teng versiya ziddiyati, soxta fayl bilan yopilgan davr/shartnoma himoyasi, boshqa qurilmada yopilgan davrni olish, inkremental, noto'g'ri/qisqa parol, yangiroq format, noma'lum ustun/jadval; UI 3 test.

## D15 — Reliz tayyorgarligi
- **Onboarding:** 5 qadamli tanishtiruv (xush kelibsiz → daromad → «Kelajagim» va qarzlar → havas chegarasi → xavfsizlik va nusxa), o'tkazib yuborish mumkin; bajarilgani bazada eslab qolinadi (`services::onboarding`).
- **Accessibility:** `axe-core` sinovlari (Almashish, Hunardan ishga, Sheriklik, Onboarding) — haqiqiy topilma tuzatildi (sarlavha tartibi h2→h4); global `:focus-visible`, `prefers-reduced-motion`, Windows **High Contrast** (`forced-colors`) CSS, DPI uchun rem birliklari.
- **«Anvar» ssenariysi:** `crates/services/tests/anvar.rs` — daromad → audit → havas chegarasi → obuna bekor qilish → qarz → 70/20/10 → payoff → qarz yopilishi → darvoza ochilishi → sheriklik (yopiq darvozada faollashmaydi, ochilgach faollashadi) → taqsimot → eksport → yangi bazaga import 1:1. Windows `tauri-driver` E2E spetsifikatsiyasi `desktop/e2e/` da yozilgan (**ishga tushirilmagan**).
- **Reliz to'sig'i:** `pdf::TEMPLATES_APPROVED = false` — shartnoma shabloni tasdiqlanmagani ilovada ogohlantirish sifatida ko'rinadi; `release_gate` testi (`--ignored`) tasdiq berilmaguncha qizil.
- **Imzolash va updater:** `src-tauri/tauri.release.conf.template.json`, `docs/SIGNING_AND_UPDATER.md` — sertifikat/kalit yo'qligi sababli faqat shablon va qadamlar; updater plagini ulanmagan.
- `docs/RELEASE_CHECKLIST.md` (avtomatik / to'siqlar / Windows'da qo'lda), `tests/startup_budget.rs` (Rust qismi ~40 ms).

## Dizayn: Dark mavzu va ilova ikonkasi
- **Mavzu:** Claude Desktop Dark uslubi (fon `#262624`, yon panel `#1f1e1d`, kartalar `#30302e`, matn `#faf9f5`, urg'u terrakota `#d97757`); sarlavhalar serif shriftda; yorug' mavzu `data-theme="light"` orqali ixtiyoriy. Barcha ranglar `ui/src/index.css` tokenlarida.
- **Ikonka:** terrakota daftar + oltin niho («baraka» — o'sish), manba `desktop/branding/icon.svg`; `src-tauri/icons/` to'liq to'plam (`cargo tauri icon`). Oyna `backgroundColor` — yuklanishda oq chaqnash yo'q.

## Import: a'zolar siyosati (tuzatish)
- `.baraka` importda telefondan kelgan kattalar **PIN'siz** keladi (PIN xeshlari eksport qilinmaydi): ular havas chegarasiga rozilik bera olmaydi. Import hisobotida «PIN o'rnatilishi kerak» ro'yxati chiqadi; havas ekranida shunday a'zo uchun avval «PIN o'rnatish» ko'rsatiladi (rozilik tugmasi yo'q).
- A'zo nomlari registri va chekka bo'shliqqa bog'liq emas («anvar» ↔ «Anvar»): dublikat a'zo yaratilmaydi; tabiiy kalit ustunlari lokal qiymatga tenglashtiriladi (faqat registr farqi ziddiyat bo'lmaydi).
- Testlar: PIN'siz kattaning rozilik qabul qilinmasligi va PIN o'rnatilgach kuchga kirishi; ism moslashtirish; import PIN yozuvi yaratmasligi.

## Reliz: sheriklik shartnoma shabloni to'sig'i
- `pdf::templates_releasable(debug_build)`: dev build'da shablon ko'rinadi (ogohlantirish bilan); **release build'da shartnoma PDF'i chiqmaydi**, tasdiqlanmaguncha (`TEMPLATES_APPROVED = false`). Servis qatlamida ham to'siq bor (UI'ga bog'liq emas).
- UI: relizda «Shartnoma PDF» tugmasi yashirin; ogohlantirish qoladi.
- CI: `baraka-release-gate` workflow — versiya tegida (`v*`) `release_gate --ignored` testi ishlaydi; shablon tasdiqlanmaguncha qizil.

## Windows testlari: Tauri'siz `api` crate
- Muammo: Tauri'ga bog'langan test binary'si Windows'da `STATUS_ENTRYPOINT_NOT_FOUND` (0xc0000139) bilan ishlamasdi; shu sabab Windows CI'da `baraka-desktop` testlari o'tkazib yuborilardi.
- Yechim: xato xaritalash (`CommandError`), sessiya (`Session`), DTO va foiz parsing `crates/api` ga chiqarildi (Tauri'siz). `src-tauri` da `[lib]` va `[[bin]]` (app) test harness'lari o'chirildi; bindinglar `export-bindings` bin'idan yoziladi (`cargo run -p baraka-desktop --bin export-bindings`) — har OS'da.
- CI: Windows'da endi hamma testlar ishlaydi (`baraka-desktop` ning 10 ta testi `api` ga ko'chirildi); istisno yo'q.

## Klaviatura, chop etish, hajm, o'rnatuvchi, tezkor tugma ogohlantirishi
- **Ctrl+K — buyruqlar palitrasi:** sahifalar va amallar (tez kiritish, chop etish, qulflash); matn bilan filtr, strelkalar, Enter, Esc.
- **Ctrl+P — chop etish:** WebView2 `window.print()` (tizimning chop etish oynasi); chop uchun oq fon va boshqaruv tugmalari yashirin (`@media print`).
- **`.baraka` hajmi:** eksport `512 MB` chegarasidan oshsa yozilmaydi va aniq xabar chiqadi; import ham shu chegarada. Eksportda «chek rasmlari bilan» belgisi qo'shildi (rasmsiz eksport hajmni keskin kamaytiradi). Blob kodlash hozircha hex (format v1, OPEN_QUESTIONS 72).
- **O'rnatuvchi:** NSIS tillari `Russian` va `English`, til tanlash oynasi bilan (NSIS to'plamida o'zbek tili yo'q).
- **Ctrl+Alt+B ogohlantirishi:** tugma band bo'lsa (boshqa dastur ishlatayotgan bo'lsa) ilova ishlaydi, yon panelda aniq xabar chiqadi.
- Testlar: palitra (filtr, Enter, Esc), Ctrl+P, ogohlantirish, rasmsiz eksport (biriktirmalar fayldan chiqadi, yozuvlar qoladi), chegaradan katta fayl rad etiladi.

## 6-qonun — hujjatlarni sinxronlash (SPEC v0.8, DESKTOP_PROMPT v1.1)
- `docs/SPEC.md` v0.8 va `docs/DESKTOP_PROMPT.md` v1.1 yuklangan manbalar bilan yangilandi: 2F bo'limi (6-qonun, 2F.1–2F.11), 1.1 jadvalidagi 6-qonun qatori, 3.1 katalog daraxti, 5.3 vektorlar (`journal_chain.json`, `profit_spike.json`, `agreement_completeness.json`), 6.3 import qoidalari (fork), 9-bo'lim bosqichlari (D8A, D13A, D14, D15).
- `docs/MVP_PLAN.md` qo'shildi (mobil ilova uchun 17 vazifali reja; 9A va 14A — desktopdagi D8A va D13A bilan bir xil mazmun).
- Qarorlar `docs/OPEN_QUESTIONS.md` 87–93 bo'limida qayd etildi.
- Kod o'zgarmadi (doc-only).

## D8A — Kelishuv dvigateli va append-only jurnal (6-qonun, 1–2-qism)
- **Domen (sof):** `domain::journal` — RFC 8785 (JCS) kanonizatsiya (UTF-16 kalit tartibi, sonlar rad etiladi), SHA-256 xesh-zanjir (genesis 64×`0`), birinchi buzilgan yozuvni topish. `domain::agreements` — 9 savol (`Answer`: MISSING / ANSWERED / NOT_APPLICABLE), turga qarab «tegishli emas» qoidasi, `completeness` (missing + errors), ogohlantirishlar, majburiy imzolar, holat o'tishlari, «katta foyda» qoidasi (`profit_spike_alert`), kanonik JSON kodeki.
- **Vektorlar:** `journal_chain` (chain-001..004 — uchta xesh mustaqil Python hisobi bilan mos; verify-002: buzilgan 2-yozuv; canonical: Uzbek harflari, boshqaruv belgilari, son rad etilishi), `agreement_completeness` (20 case), `profit_spike` (ps-001..005).
- **Sxema v12:** `agreements`, `agreement_versions` (o'zgarmas), `agreement_signatures` (o'zgarmas, versiyaga bog'liq), `journal_entries` (append-only). UPDATE/DELETE triggerlari `RAISE(ABORT)` qiladi; bitta kelishuv — bitta obyekt (unikal indeks). Eski jadvallar tegilmaydi.
- **Servis:** `services::agreements` — `create`, `save_version` (yangi versiya → qoralama, eski tasdiqlar o'tmaydi), `sign` (9/9 bo'lmasa rad; tomon PIN'i tekshiriladi), `activate`, `close`, `view`, `list`, `is_fully_signed`, `adopt_legacy` (idempotent: eski sheriklik va qarz tilxatlari ko'chiriladi, boshlang'ich holat — bitta `OPENING_BALANCE`). `services::journal` — `append` (faqat hisob yurituvchi qurilma, tuzatish `CORRECTION` bilan), `verify`.
- **Sheriklik integratsiyasi:** `NewPartnership.details` (vazifalar, pul joyi, hakam, yangilash sanasi); qolgan savollar sheriklikdan avtomatik (tomonlar, hissalar, foyda, zarar matni, chiqish, muddat). `sign`/`family_consent`/`activate`/`end` kelishuv dvigatelidan foydalanadi; blokerlar: `INCOMPLETE_AGREEMENT`, `ARBITER_SIGNATURE`. Davr yopish: joriy versiya 9/9 va to'liq imzolangan bo'lishi shart; taqsimot, buyout va yopilish jurnalga yoziladi; venture yozuvi jurnalga `VENTURE_*`, bekor qilish `CORRECTION` bilan.
- **Almashish:** yangi jadvallar eksportga kiradi; versiya va imzolar — import orqali o'zgarmaydi (`JOURNAL` ziddiyat turi qo'shildi, UI matni uz/ru). Sxema versiyasi 12.
- **Tauri/UI:** sheriklik formasiga 3 ta javob (vazifalar, pul joyi, hakam) va yangilash sanasi; kelishuv holati (javobsiz savollar soni, hakam tasdig'i tugmasi); bindinglar yangilangan.
- **Qolgan (D8A keyingi qismi):** 9 savolli to'liq wizard UI, kelishuv PDF'i va uning snapshot testi, qarz to'lovlarining `PAYMENT` yozuvi (D9), import da zanjir tekshiruvi va fork aniqlash (D14).
- **Qo'shimcha (D8A, 3-qism):** kelishuv PDF'i (`pdf::agreement_pdf`, 9 bo'lim, tasdiq bloklari, matn snapshot testi); qarz to'lovi kelishuvga bog'langan bo'lsa `PAYMENT` jurnal yozuvi; sheriklik formasiga vazifalar, pul joyi, hakam va yangilash sanasi; forma joriy javoblardan boshlanadi (`AgreementStatusDto.duties/custody_place/arbiter_name/review_date`).
- **D8A (4-qism): shartnoma ustasi.** Chapda 9 qadamli progress (har savolning holati `check_partnership_draft` dan), o'rtada forma (maydonlar tegishli savolga `data-step` bilan bog'langan), o'ngda Sobir hoji maslahati va PDF önizleme (350 ms debounce; hech narsa saqlanmaydi). Sheriklik PDF'i 9 savolli versiyada kelishuv PDF'iga yo'naltirildi. Relizda shablon tasdiqlanmaguncha önizleme ham, PDF ham chiqmaydi.
- **D13A (1-qism): nizo, vazifa hodisasi, «katta foyda».** `events` moduli: «bajara olmayapman» hodisasi (band va mas'ul tomon bilan jurnalga), nizo ochish (faqat faol kelishuvda) va hakam qarori (nizo yopiladi). Nizoli kelishuvda davrni yopish bloklanadi. «Katta foyda» (200% tarix) tasdiqsiz davrni yopmaydi; tasdiq jurnalga yoziladi. Jurnal turlari V13 migratsiyasi bilan kengaydi (zanjir saqlangan). Sheriklik sahifasida vazifalar ro'yxati, nizo bloki va davr yopishda tasdiq katagi.
- **D13A (2-qism, oylik ko'rik): `review` moduli.** Har bir tomon davr uchun «ko'rdim, roziman» yoki «e'tirozim bor» + izoh deb javob beradi (`REVIEW_ACK`); barcha tomonlar javob bergach ko'rik yakunlanadi (`REVIEW_CLOSED`), zanjir boshi yozuvga qayd etiladi. Bayonnoma PDF'i (`pdf::review`) tomonlar javobi, davr yozuvlari, vazifa hodisalari va zanjir boshini chiqaradi; zanjir o'zgarsa «MOS KELMAYDI» ogohlantirishi chiqadi (snapshot va tamper testlari). UI: sheriklik kartasida ko'rik bloki, PDF eksporti.
- **D13A (hakam papkasi): `pdf::dispute_folder`.** Nizoli kelishuv uchun bitta PDF: mundarija (sahifa raqamlari bilan), kelishuv versiyalari, hisob yozuvlari, zanjir holati, ko'rik bayonnomalari (zanjir boshi bilan), vazifa hodisalari, tomonlarning talablari va hakam qarorlari. Snapshot testi va nizo ochiq bo'lganda ishlash testi bor; UI'da «Hakam ish papkasi (PDF)» tugmasi.
- **D13A (kelishuvlar markazi va yillik eslatma).** Sheriklik sahifasi tepasida barcha kelishuvlar jadvali: turi, holat, versiya, yangilash sanasi (30 kun ichida eslatma), ochiq hodisalar soni, nizo va joriy oy ko'rigi holati; holat bo'yicha filtr va nom bo'yicha qidiruv. `events::center` va `agreements_center` buyrug'i.
