# TAMGA — AI agentlar uchun "qora quti"

> **Tamga** — turkiy xalqlarda urug' muhri, egalik va haqiqiylik belgisi.
> Bu loyihada u AI agent bajargan har bir harakatga bosiladigan, o'zgartirib bo'lmaydigan muhrni bildiradi.

**Bir jumlada:** TAMGA AI agentning har bir harakatini bajarilishidan **oldin** siyosat bo'yicha
tekshiradi, **keyin** esa xesh-zanjirli, post-kvant imzoli jurnalga yozadi. Bu jurnalni
uchinchi tomon auditor manba koddan mustaqil ravishda tekshira oladi.

**Asosiy talab (foydalanuvchidan):** GUI foni Claude Code desktop ilovasining **dark theme**
ko'rinishida bo'ladi (6-bo'lim).

---

## 1. Muammo va yangilik

| Hozir bor | Yetishmaydi (TAMGA yopadigan bo'shliq) |
|---|---|
| Tracing/observability (LangSmith, OTel GenAI) — dasturchi uchun | **Dalil darajasidagi** jurnal: o'chirilgan yoki o'zgartirilgan yozuv aniqlanadi |
| Agentning o'z ruxsat tizimi (allow/deny) | Agentdan **tashqaridagi** mustaqil siyosat va mustaqil guvoh |
| Log fayllar | Ochiq format + mustaqil verifikator + test vektorlari (standart) |
| — | **"Aytdi va qildi" solishtiruvi**: agent xabar bergan harakat bilan OS haqiqatda ko'rgan harakat farqi |
| — | GDPR bilan mos: yuklama (payload) o'chirilsa ham zanjir tekshiriladi (crypto-shredding) |

**Yangilik da'vosi** (F0 raqobatchilar tahlili, 2026-10-17: [COMPETITORS.md](COMPETITORS.md)):
ochiq format, bajarilishdan oldin to'xtatish, gibrid post-kvant imzo, mustaqil
verifikator, OS bilan solishtirish va crypto-shredding bitta lokal, serversiz vositada birlashgan.
Bu **kombinatsiya** hech qayerda topilmadi. **Alohida elementlarning har biri esa allaqachon bor**,
shuning uchun ularning birortasi uchun "birinchi" deb aytilmaydi.
Eng yaqin raqobatchilar: AgentProvenance (5 mezonning hammasi qisman, faqat Linux), Pipelock va
Microsoft AGT. Haqiqiy farqlar: Windows-native "aytdi va qildi", Ed25519+ML-DSA-65 gibrid imzo,
test vektorli shredding. Format nomi Pipelock'ning "Agent Action Receipt" (AARP) bilan to'qnashmasligi uchun
"AAR" dan **TAMGA Record** ga o'zgartirildi. draft-sharif-agent-audit-trail-08 bilan bayt-darajada mos emas
(sabablari asosli), lekin unga yo'qotishsiz proyeksiya qilinadi — spec §11.

## 2. Tahdid modeli (halol chegaralar)

- **Himoya qiladi:** jurnaldagi yozuvni jim o'zgartirish, o'chirish yoki tartibini almashtirish;
  agentning ruxsatsiz xavfli harakati; agentning "men buni qilmadim" degan tarixni qayta yozishi.
- **Qisman:** mashinaning administratori butun jurnalni o'chirishi mumkin. Bunga qarshi
  imzolangan **checkpoint**lar tashqi guvohga yuboriladi (boshqa mashina, git remote, RFC 3161 TSA).
  Shundan keyin o'chirish *aniqlanadi*, lekin *oldi olinmaydi*.
- **Himoya qilmaydi (v1):** buzilgan OS yadrosi, xotiradan imzo kalitini o'g'irlash
  (kalit v1 da Windows DPAPI ostida turadi, TPM esa v2 da).

## 3. Arxitektura

```
 Claude Code ──hook──┐
 MCP mijoz ──proxy───┤                    ┌─────────── tamgad (daemon, Rust) ───────────┐
 SDK (keyin) ────────┼── named pipe/UDS ─▶│ normalize → redact → POLICY → decision     │
 OS sensor ──────────┘                    │        ↓                                    │
                                          │ TR record → hash chain   → Merkle → sign     │
                                          │        ↓                         ↓          │
                                          │ segment files (JSONL)   checkpoint → witness│
                                          │ SQLite index            payload vault (enc) │
                                          └───────────────▲─────────────────────────────┘
                                                          │ IPC (read + approve)
                                          TAMGA Studio (Tauri 2 + React) — dark GUI
                                          tamga-verify (mustaqil CLI, auditor uchun)
```

### Texnologiya qarorlari

| Qism | Tanlov | Sabab |
|---|---|---|
| Yadro, daemon, CLI | **Rust** (workspace) | xavfsizlik, tezlik; mashinada Rust muhiti tayyor |
| GUI | **Tauri 2 + React + TypeScript + Vite** | Claude Code ko'rinishini CSS'da piksel aniqligida takrorlash; Tauri bu mashinada sinalgan |
| Yozuv formati | **JSON + RFC 8785 (JCS)** kanonikalashtirish | auditor o'qiy oladi, xesh deterministik |
| Xesh | **SHA-256** (zanjir va Merkle, RFC 9162 uslubi) | standart, FIPS |
| Imzo | **Gibrid Ed25519 + ML-DSA-65 (FIPS 204)** | post-kvant + klassik; ikkalasi ham haqiqiy bo'lishi shart |
| Siyosat | **Cedar** (`cedar-policy` crate) | Rust-native, formal tahlil qilinadi, deklarativ |
| Saqlash | append-only segment fayllar + **SQLite** indeks | segment haqiqat manbai, indeks esa qayta quriladi |
| Yuklama maxfiyligi | XChaCha20-Poly1305, har sessiyaga alohida kalit | kalitni o'chirish = unutish; zanjir buzilmaydi |
| IPC | Windows named pipe / Unix domain socket | lokal, serversiz |

### Repo tuzilmasi

```
tamga/
  spec/                 TAMGA-RECORD-0.1.md (ochiq standart) + test-vectors/
  crates/
    tamga-core/         TAMGA Record turlari, JCS, hash chain, Merkle, gibrid imzo
    tamga-store/        segmentlar, SQLite indeks, payload vault
    tamga-policy/       Cedar bilan baholash, standart siyosatlar to'plami
    tamga-redact/       sirlarni topish (API kalit, token, .env)
    tamgad/             daemon: IPC, quvur, checkpoint, guvoh
    tamga-hook/         Claude Code hook binari (stdin JSON → qaror)
    tamga-mcp-proxy/    stdio MCP proxy (istalgan agent uchun)
    tamga-verify/       mustaqil verifikator CLI (faqat tamga-core'ga bog'liq)
    tamga-cli/          `tamga` — boshqaruv, eksport, kalitlar
  studio/               Tauri 2 + React GUI
  verify-py/            ikkinchi, mustaqil Python verifikator (cross-impl)
  docs/
```

## 4. TAMGA Record (ochiq format, v0.1)

```json
{
  "tamga": "0.1",
  "seq": 1842,
  "ts": "2026-10-17T10:41:07.118Z",
  "session": "cc_7f3a…",
  "agent": {"kind": "claude-code", "version": "…", "model": "…"},
  "actor": {"user": "…", "host": "…"},
  "event": "tool.pre",
  "tool": {"name": "Bash", "input_digest": "sha256:…"},
  "decision": {"verdict": "deny", "policy": "no-secret-exfil", "by": "policy"},
  "payload_ref": {"vault": "v1", "salt_digest": "sha256:…"},
  "prev": "sha256:…",
  "hash": "sha256:…"
}
```

- `hash = SHA-256(JCS(record without "hash"))`. `prev` maydoni oldingi yozuvga bog'laydi.
- Har N yozuvda yoki T soniyada **Signed Tree Head** yaratiladi: Merkle ildizi, seq va vaqt
  gibrid imzo bilan muhrlanadi.
- Yuklama (buyruq matni, fayl diff'i) zanjirga **tuzlangan xesh** sifatida kiradi.
  Ochiq matn esa shifrlangan vault'da saqlanadi.
- Hodisalar: `session.start/end`, `prompt`, `tool.pre`, `tool.post`, `decision.human`,
  `os.observed`, `checkpoint`.

## 5. Siyosat va qaror oqimi

1. Agent harakatni e'lon qiladi. Masalan, Claude Code `PreToolUse` hook'i `tamga-hook`ni chaqiradi.
2. Daemon hodisani normallashtiradi, sirlarni yashiradi, keyin Cedar'da baholaydi.
3. Qaror: **allow** / **deny** / **ask**. "Ask" bo'lsa, Studio'da tasdiqlash navbati ochiladi.
4. Qaror hook'ka qaytadi (`permissionDecision` + sabab). Rad etish sababi agentga ko'rsatiladi.
5. `PostToolUse` natijasi `tool.post` sifatida yoziladi.
6. **Daemon ishlamasa:** hook yozuvni lokal spool faylga yozadi, shu bilan hech narsa yo'qolmaydi.
   Rejim `strict` bo'lsa, harakat bloklanadi (fail-closed). Rejim `dev` bo'lsa, ruxsat beriladi
   va bu holat belgilanadi.

**F2 da aniqlangan qoidalar (2026-10-17):**

- **`allow` agentga qaytarilmaydi.** Claude Code hook'i `permissionDecision: "allow"` qaytarsa,
  Claude Code'ning o'z ruxsat so'rovlari chetlab o'tiladi. Shuning uchun TAMGA faqat `deny` yoki
  `ask` qaytaradi. `allow` holatida hook hech narsa chiqarmaydi va agentning ruxsat tizimi o'z
  holicha ishlaydi. TAMGA o'z ruxsat qatlamini qo'shadi, mavjudini almashtirmaydi.
- **Hook daemon'ni merossiz ishga tushiradi.** Rust std bola jarayonga barcha meros qilinadigan
  handle'larni beradi (`inherit_handles(false)` hali barqaror emas). Shu sabab daemon hook'ning
  stdout pipe'ini ushlab qolib, Claude Code'ni 10 soniyalik timeout'gacha kutdirardi. Yechim:
  `tamga-win` crate'i spawn'dan oldin std handle'lardan `HANDLE_FLAG_INHERIT` bayrog'ini oladi.
  Bu workspace'dagi yagona `unsafe` joy.
- **O'lchangan kechikish (release, 200 ta `PreToolUse`):** p50 9.1 ms, p99 10.8 ms. Bu Windows
  jarayon yaratish (~4 ms) va diskka `fsync`ni o'z ichiga oladi. Maqsad < 20 ms bajarildi.

**Standart siyosatlar to'plami (v1):** `.env` yoki kalit fayllarni o'qib tashqariga yuborish;
`rm -rf` loyiha tashqarisida; `git push --force` asosiy branchga; tarmoqqa noma'lum domenga
`curl | sh`; tizim sozlamalarini o'zgartirish; ishchi papkadan tashqariga yozish.

## 6. Dizayn: Claude Code dark theme ⭐

**Qoida:** barcha ranglar faqat `studio/src/theme/tokens.css` dagi tokenlardan olinadi.
Komponentda hex qiymat yozilmaydi.
**F0 natijasi (2026-10-17):** tokenlar Claude desktop oynasining skrinshotidan piksel bo'yicha
o'lchandi. Haqiqiy tema boshlang'ich taxmindan (`#262624` iliq-kulrang) ancha to'q va neytral chiqdi.
Studio skrinshotida 7 ta nazorat nuqtasining hammasi Claude bilan piksel-bir-xil.

| Token | Qiymat | Manba | Qayerda |
|---|---|---|---|
| `--bg-app` | `#151515` | o'lchangan | asosiy fon, sarlavha paneli |
| `--bg-sidebar` | `#111111` | o'lchangan | chap panel |
| `--bg-field` | `#1D1D1D` | o'lchangan | qidiruv maydoni |
| `--bg-input` | `#20201F` | o'lchangan | kiritish qutisi |
| `--bg-bubble` | `#1C1C1C` | o'lchangan | banner, tanlangan qator |
| `--bg-selected` | `#343434` | o'lchangan | tanlangan navigatsiya bandi |
| `--bg-code` | `#0E0E0E` | hosila | kod/terminal bloklari |
| `--border` | `#292929` | o'lchangan | panel ajratuvchisi |
| `--border-strong` | `#373736` | o'lchangan | input chegarasi |
| `--text-primary` | `#F0EFEC` | o'lchangan | asosiy matn |
| `--text-secondary` | `#C3C2B7` | o'lchangan | ikkilamchi matn |
| `--text-muted` | `#898781` | o'lchangan | izoh, placeholder |
| `--text-faint` | `#5A5955` | o'lchangan | eng past darajadagi matn |
| `--accent` | `#D97757` | Claude clay | asosiy tugma |
| `--success` | `#4EBA65` | Claude Code CLI | allow, zanjir butun |
| `--danger` | `#FF6B80` | Claude Code CLI | deny, buzilish aniqlandi |
| `--warning` | `#FFC107` | Claude Code CLI | ogohlantirish |
| `--ask` | `#B1B9F9` | Claude Code CLI | inson tasdig'ini kutayotgan harakat |

- **Shrift:** UI uchun Segoe UI Variable (Inter zaxira), kod va xeshlar uchun JetBrains Mono.
- **Uslub:** 8–12 px radius, soya o'rniga ingichka chegara. Sessiya qayta o'ynatilganda
  harakatlar **Claude Code transkriptiga o'xshab** ko'rsatiladi: yig'iladigan tool-bloklar,
  har birining yonida muhr belgisi (✓ imzolangan / ⚠ buzilgan).
- **Ikonka:** loyihaga xos tamga belgisi, `scripts/make_icon.py`. F0 da vaqtincha A varianti (Muhr); foydalanuvchi A/B/C dan birini tanlaydi.
- **Oyna:** native sarlavha o'chirilgan (`decorations: false`), o'z sarlavha paneli va Windows uslubidagi oyna tugmalari bor.

### Studio ekranlari

1. **Jonli** — harakatlar oqimi real vaqtda, filtr bo'yicha (agent, tool, qaror).
2. **Tasdiqlash** — "ask" navbati: Ruxsat / Rad / Har doim ruxsat (siyosatga yoziladi).
3. **Sessiyalar** — ro'yxat va transkript uslubidagi qayta o'ynatish.
4. **Harakat tafsiloti** — kirish, natija, diff, xesh, imzo holati, qaysi siyosat ishlagani.
5. **Yaxlitlik** — zanjirni tekshirish, checkpoint'lar, guvoh holati, buzilish xaritasi.
6. **Siyosatlar** — Cedar muharriri va "agar shu harakat bo'lsa nima bo'ladi" sinovi.
7. **Hisobotlar** — dalil to'plami eksporti (ZIP: yozuvlar, STH, verifikator yo'riqnomasi, PDF xulosa).
8. **Sozlamalar** — rejim (strict/dev), integratsiyalar, kalitlar, guvoh manzili.

## 7. Bosqichlar

Har bosqich **qabul mezoni** bilan yopiladi. Testlarning o'tishi yetarli emas:
natija haqiqiy ishga tushirib ko'rsatiladi.

| # | Bosqich | Natija | Qabul mezoni |
|---|---|---|---|
| **F0** | Poydevor (1–2 kun) | workspace, Tauri skeleti, `tokens.css`, CI, raqobatchilar tahlili | bo'sh Studio ochiladi; foni skrinshotda Claude Code bilan yonma-yon solishtiriladi |
| **F1** | TAMGA Record yadrosi | `spec/TAMGA-RECORD-0.1.md`, `tamga-core`, test vektorlari | JCS va xesh vektorlari o'tadi; ML-DSA-65 NIST vektorlari bilan mos; 1 baytni o'zgartirish aniq seq'da aniqlanadi |
| **F2** | Daemon + Claude Code hook | `tamgad`, `tamga-store`, `tamga-hook`, `tamga install claude-code` | **haqiqiy** Claude Code sessiyasi to'liq yoziladi; daemon o'chiq bo'lsa spool ishlaydi |
| **F3** | Siyosat va bloklash | `tamga-policy`, standart to'plam, "ask" oqimi | agent `.env`ni o'qib `curl` qilmoqchi bo'lsa bloklanadi, sababi agentga ko'rinadi |
| **F4** | Studio GUI | 8 ekran, jonli oqim, qayta o'ynatish | har bir tugma bosib sinaladi; skrinshotlar ko'z bilan tekshiriladi |
| **F5** | MCP proxy | `tamga-mcp-proxy` | istalgan MCP serverni o'rab, chaqiruvlarni yozadi va bloklaydi |
| **F6** | Verifikator va dalil | `tamga-verify`, `verify-py`, eksport ZIP | ikki mustaqil implementatsiya bir xil hukm beradi; o'chirilgan oraliq checkpoint orqali aniqlanadi |
| **F7** | "Aytdi va qildi" | Windows OS sensori (QARCHIG'AY tajribasi) | agent e'lon qilmagan fayl yoki jarayon harakati `os.observed` + ogohlantirish sifatida chiqadi |
| **F8** | Reliz | o'rnatuvchi (Setup.exe), README, demo | toza mashinaga o'rnatilib, demo stsenariy boshidan oxirigacha o'tadi |

**Demo stsenariy (F8):** agent "loyihani tozalash" niyatida `.env`ni tashqariga
yubormoqchi bo'ladi → TAMGA bloklaydi. Keyin kimdir jurnaldan bitta yozuvni o'chiradi →
`tamga-verify` aniq qaysi joy buzilganini qizil bilan ko'rsatadi.

## 8. Sifat qoidalari

- Kriptografiya: faqat tekshirilgan crate'lar. O'z primitivlarimizni yozmaymiz.
  Har bir algoritm rasmiy test vektorlari bilan tekshiriladi.
- `unsafe` kod bo'lmaydi. Agar zarur bo'lsa, faqat Miri bilan tekshiriladi.
- Daemon hook'ka qaror qaytarishi **< 20 ms (p99)** bo'lishi shart, aks holda agent sekinlashadi.
  Bu o'lchab tekshiriladi.
- Sirlar hech qachon ochiq matnda zanjirga, log'ga yoki GUI eksportiga tushmaydi.
- Barcha vaqtlar UTC, tz-aware.

## 9. Ochiq savollar (keyinroq qaror qilinadi)

- Litsenziya: spec uchun CC-BY, kod uchun Apache-2.0 (taklif).
- Tashqi guvoh standart sifatida: git remote, RFC 3161 TSA yoki boshqa TAMGA tuguni.
- v2: TPM'dagi kalit, Python/TS SDK, OpenTelemetry GenAI'dan import, jamoaviy (ko'p mashinali) rejim.
