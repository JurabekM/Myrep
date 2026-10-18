# TAMGA — AI auditor uchun qo'llanma

Bu hujjat TAMGA'ni **AI agent** (repo va shell'ga kirishi bor auditor agent) yoki inson auditor
mustaqil xavfsizlik tekshiruvidan o'tkazishi uchun yozilgan. Maqsad — muallif da'volarini
**rad etishga urinish**, ularni takrorlash emas.

> Qoida: har bir topilma takrorlanadigan dalil bilan beriladi (buyruq, kirish ma'lumoti, kutilgan va
> haqiqiy natija, `fayl:qator`). Taxminlar topilma emas — ular «savollar» bo'limiga yoziladi.

---

## 0. Auditor agentga tayyor topshiriq

Quyidagi matnni auditor agentning birinchi xabari sifatida bering (inglizcha — spec va kod izohlari
bilan aniqroq ishlaydi; hisobotni o'zbekcha so'rash mumkin):

```text
You are an independent security auditor for the TAMGA repository in the current directory
(an AI-agent flight recorder: Claude Code hook + Windows daemon + hash-chained log with
Ed25519 + ML-DSA-65 signed checkpoints + Cedar policies + an independent Python verifier).

Read docs/AUDIT-GUIDE.md and follow phases A–H in order. Try to FALSIFY claims C1–C14
(section 2); start with the known weaknesses K1–K6 (section 4).
Rules:
- Work only in a sandbox: fresh TAMGA_HOME temp dir, TAMGA_SECRETS=file, a unique short
  TAMGA_PIPE, TAMGA_SENSOR=0 unless testing the sensor. Never modify the real
  ~/.claude/settings.json, %LOCALAPPDATA%\tamga or Windows Credential Manager.
- Use only fake secrets and reserved *.invalid domains; no traffic to real third parties.
- Each finding: claim id, severity (Critical/High/Medium/Low/Info), reproduction,
  expected vs actual, file:line, suggested fix. Mark findings "verified" or "suspected".
- Report in the format of section 6. No style-only remarks.
```

---

## 1. Tizim xaritasi

```text
 Claude Code ── hook JSON ──▶ tamga-hook.exe ─────┐
 MCP mijoz ─── stdio ──▶ tamga-mcp-proxy.exe ─────┼─ named pipe \\.\pipe\tamga-<user> ─▶ tamgad.exe
 TAMGA Studio / tamga.exe (CLI) ──────────────────┘          │
                                                             ├─ faktlar → Cedar → deny / ask / allow
                                                             ├─ jurnal <id>.jsonl (fsync) + <id>.checkpoints
                                                             ├─ vault (XChaCha20-Poly1305, sessiya kaliti)
                                                             ├─ kalitlar: Credential Manager (DPAPI)
                                                             └─ OS sensori → os.observed
 Auditor ── dalil ZIP ──▶ verify-py (faqat Python stdlib) yoki tamga-verify.exe
```

| Qism | Fayllar | E'tibor |
|---|---|---|
| Format | `spec/TAMGA-RECORD-0.1.md`, `spec/test-vectors/*.json` | spec ↔ kod mosligi |
| Yadro | `crates/tamga-core/src/{jcs,record,chain,merkle,keys,checkpoint,rotation,payload}.rs` | kanoniklik, xesh, imzo, domen ajratish |
| Saqlash | `crates/tamga-store/src/{logfile,vault,keystore,secrets,spool,export,integrate}.rs` | fsync, tiklash, shifrlash, zaxira |
| Siyosat | `crates/tamga-policy/src/{facts,taint,lib}.rs`, `policies/default.cedar` | faktlar to'liqligi |
| Daemon | `crates/tamgad/src/{main,normalize,observe}.rs` | IPC, holat, ask oqimi, kalit almashtirish |
| Hook / proxy | `crates/tamga-hook/`, `crates/tamga-mcp-proxy/` | fail-open/closed |
| Sensor | `crates/tamga-sensor/`, `crates/tamgad/src/observe.rs` | ko'r nuqtalar |
| `unsafe` | `crates/tamga-win/src/lib.rs` (yagona) | `CreateProcessW` |
| Mustaqil verifikator | `verify-py/tamga_verify/*.py` | noldan yozilgan Ed25519 / ML-DSA-65 |
| Studio | `studio/src-tauri/src/{lib,data}.rs`, `studio/src/**` | sirlarni yashirish, buyruqlar |
| O'rnatuvchi | `studio/src-tauri/{tauri.bundle.json,installer-hooks.nsh}`, `scripts/{build-installer,sign}.ps1` | huquqlar, qoldiqlar, imzo |

Ishonch chegaralari: (1) agent → hook: agent bergan hamma narsa ishonchsiz; (2) bir foydalanuvchi
ichidagi jarayonlar → pipe; (3) disk fayllari (jurnal, spool, config) — foydalanuvchi o'zgartira
oladi; (4) dalil to'plami → auditor: langar kalitdan boshqa hech narsaga ishonilmaydi.

---

## 2. Tekshiriladigan da'volar

| # | Da'vo | Qayerda |
|---|---|---|
| C1 | Jurnaldagi har qanday o'zgartirish, o'chirish, qo'shish yoki qayta tartiblash birinchi buzilgan yozuv indeksi bilan topiladi | `chain.rs`, spec §8 |
| C2 | Checkpoint faqat **ikkala** imzo (qat'iy Ed25519 va ML-DSA-65) to'g'ri bo'lsa qabul qilinadi | `keys.rs`, `checkpoint.rs`, `verify.py` |
| C3 | Imzolangan checkpoint qamragan qismni kesish yoki qayta yozish aniqlanadi | `checkpoint.rs` |
| C4 | Kalit almashtirish faqat eski kalit imzolagan checkpoint bilan kuchga kiradi; isbot boshqa yozuvga ko'chmaydi | `rotation.rs`, spec §7.5 |
| C5 | `deny` chiqqan amal bajarilmaydi; hook hech qachon `allow` qaytarmaydi | `tamga-hook`, `tamgad::hook` |
| C6 | Sessiyada o'qilgan sirni keyin tarmoqqa yuborish bloklanadi, daemon qayta ishga tushsa ham | `taint.rs`, vault state |
| C7 | Sirlar jurnalga, log'ga yoki GUI'ga ochiq tushmaydi; `shred` dan keyin payload o'qilmaydi, jurnal tekshirilaveradi | `tamga-redact`, `vault.rs` |
| C8 | Kalit zaxirasi faqat parol bilan ochiladi; sarlavhani o'zgartirish aniqlanadi | `keystore.rs` |
| C9 | Ombordagi kalit jurnal kutgan faol kalitga mos kelmasa daemon imzolamaydi | `tamgad::open_state` |
| C10 | Rust va Python verifikatorlari har kirishda bir xil kod va indeks beradi | `scripts/crosscheck_verifiers.py` |
| C11 | Pipe'ga faqat joriy foydalanuvchi va faqat lokal ulanadi | `tamgad::serve` |
| C12 | O'rnatuvchi admin so'ramaydi; o'chirilganda hook va daemon qolmaydi, dalil saqlanadi | `installer-hooks.nsh` |
| C13 | Sensor e'lon qilinmagan tarmoq ulanishini tool chaqiruviga bog'laydi; ko'r nuqtalar yashirilmaydi | `observe.rs` |
| C14 | `unsafe` faqat `tamga-win` da va u to'g'ri | `tamga-win/src/lib.rs` |

---

## 3. Tahdid modeli

**Doira ichida:** (1) zararli yoki prompt injection bilan aldangan agent — u **xuddi shu Windows
foydalanuvchisi** huquqida ishlaydi; (2) jurnalni keyin tahrirlaydigan lokal foydalanuvchi;
(3) dalil to'plamini auditorga yetguncha qalbakilashtirmoqchi bo'lgan tomon.

**Doira tashqarisida:** administrator yoki yadro darajasidagi hujumchi, buzilgan OS, apparat
hujumlari, Claude Code'ning o'z xatolari.

Eng nozik joy: agent va TAMGA bir xil foydalanuvchi huquqida. Shuning uchun agentning TAMGA'ning
o'ziga ta'sir qila olishi (§4) birinchi tekshiriladi.

---

## 4. Ma'lum zaif nuqtalar (muallif o'zi topgan)

| # | Muammo | Joy | Holat |
|---|---|---|---|
| K1 | Pipe'dagi boshqaruv buyruqlari (`decide`, `shutdown`, `rotate`) chaqiruvchini tekshirmas edi. **Tuzatildi (2026-10-18):** daemon mijoz PID'ini oladi (`GetNamedPipeClientProcessId`), jarayon daraxtini ko'radi va bu buyruqlarni faqat daemon bilan bir papkadagi `tamga.exe` / `tamga-studio.exe` dan, agent daraxtidan (`claude*`, hook, MCP proxy avlodlari) tashqarida qabul qiladi; har urinish `control` yozuvi. **Qoldiq:** bir foydalanuvchi ichida bu mutlaq chegara emas — ota jarayoni chiqib ketgan (ajralgan) jarayonning ajdodlari ko'rinmaydi; jarayonni o'ldirishni (kill) daemon to'xtata olmaydi (hook keyingi chaqiruvda uni qayta ishga tushiradi). Shuning uchun K2 dagi siyosat bloki va jurnal izi ham bor | `tamgad/src/control.rs`, `tamga-win`, `tamga-sensor::identify` | qisman (to'siq + iz) |
| K2 | Agent TAMGA sozlamalarini (`config.json`, Claude Code hook'lari) o'zgartirishi mumkin edi. **Tuzatildi:** `tamper_with_tamga` fakti (TAMGA boshqaruv buyruqlari, daemon, pipe, `%LOCALAPPDATA%\tamga`, o'rnatish papkasi, `.claude/settings*.json`) va `no-tamga-tamper` deny qoidasi; daemon config o'zgarishini va foydalanuvchi darajasidagi Claude Code hook'lari olib tashlanishini `control` yozuvi qiladi. **Qoldiq:** fakt buyruq matniga tayanadi (K4) | `facts.rs`, `default.cedar`, `tamgad::tick` | qisman |
| K3 | Spool papkasi foydalanuvchi yoza oladigan joyda; u yerdan o'qilgan hodisalar faqat `dev.tamga.spooled` belgisi bilan ajratiladi | `spool.rs`, `tamgad::drain_spool` | qisman |
| K4 | Faktlar tahlilchisi buyruq matniga tayanadi va hamma variantni qamrab ololmaydi | `facts.rs` | ma'lum; OS sensori qisman qoplaydi |
| K5 | Oxirgi checkpoint'dan keyingi dumni kesish faqat tashqi guvoh bilan aniqlanadi; `witness_dir` standart o'chiq | spec §7.4 | ma'lum |
| K6 | `dev` rejimi fail-open (daemon ishlamasa amal ruxsat etiladi) | `tamga-hook` | ataylab; `strict` mavjud |

Auditor K1–K6 ni qum qutisida tasdiqlashi, og'irligini baholashi va tuzatish yo'lini taklif qilishi
kerak. K1/K2 tuzatishining o'zini ham tekshiring (`crates/tamgad/src/control.rs`): agent daraxtidan `tamga decide` / `tamga stop` rad etiladimi, Studio'dan qabul qilinadimi, `control` yozuvlari to'g'rimi; qoldiq yo'llarni baholang (masalan K1 uchun yana: pipe mijozining PID'i orqali jarayon yo'lini va imzosini tekshirish,
boshqaruv buyruqlarini jurnalga yozish, agent jarayon daraxtidan kelgan boshqaruv so'rovlarini rad
etish).

---

## 5. Audit bosqichlari

Qum qutisi (har bosqich oldidan):

```powershell
$env:CARGO_TARGET_DIR = "$env:USERPROFILE\.cargo-targets\tamga"   # Windows MAX_PATH uchun qisqa yo'l
$env:TAMGA_HOME = "$env:TEMP\tamga-audit\home"; $env:TAMGA_SECRETS = "file"
$env:TAMGA_PIPE = "tamga-audit"; $env:TAMGA_SENSOR = "0"
```

### A. Asos chizig'i

```powershell
cargo fmt --all --check; cargo clippy --workspace --all-targets -- -D warnings; cargo test --workspace
cd verify-py; py -m unittest discover -s tests -v; cd ..
$env:UPDATE_VECTORS = "1"; cargo test -p tamga-core --test vectors; Remove-Item Env:UPDATE_VECTORS
git status --short spec        # bo'sh bo'lishi kerak: vektorlar deterministik
py scripts/crosscheck_verifiers.py
```

### B. Spec ↔ kod mosligi

1. Spec'dagi har bir MUST uchun kodda joyini toping; topilmasa — topilma.
2. JCS (`jcs.rs`, `jcs.py`): butun sonlar chegarasi, `-0`, kalit tartibi (UTF-16), escape'lar,
   surrogate juftlar, takror kalitlar. Yangi chekka holatlarni ikkala implementatsiyaga bering.
3. Qator chegarasi (1 MiB), CRLF, BOM, yakunlanmagan oxirgi qator — qaysi xato kodi chiqadi?
4. Spec §8 dagi `E_HASH` / `E_PREV` farqi kodga mosmi?

### C. Kriptografiya

1. Domen ajratish jadvalini tekshiring:

   | Maqsad | Prefiks | ML-DSA konteksti |
   |---|---|---|
   | yozuv xeshi / Merkle barg | `0x00` | — |
   | Merkle ichki tugun | `0x01` | — |
   | checkpoint | `TAMGA-CHECKPOINT-v1\0` | `tamga-checkpoint` |
   | kalit almashtirish isboti | `TAMGA-ROTATE-v1\0` | `tamga-rotate` |
   | kalit identifikatori | `TAMGA-KEY-v1\0` | — |
   | payload majburiyati | `TAMGA-PAYLOAD-v1\0` | — |

2. Ed25519 qat'iy tekshiruvi (Rust `verify_strict` va `ed25519.py`): kanonik bo'lmagan `S`, kichik
   tartibli nuqtalar. RFC 8032 va Wycheproof vektorlarini ikkala tomonga bering.
3. ML-DSA-65 (`mldsa65.py` noldan yozilgan): FIPS 204 Verify algoritmi bilan qadamma-qadam
   solishtiring; NIST ACVP vektorlari; `scripts/interop_liboqs.py`.
4. Ishlab chiqarish imzolari hedged (`getrandom`) ekanini, deterministik variant faqat test
   vektorlarida ishlatilishini tekshiring.
5. Vault va kalit zaxirasi: nonce yagonaligi, AAD qamrovi, KDF parametrlari chegaralari, xato
   xabarlari parol haqida ma'lumot bermasligi.

### D. Siyosat to'liqligi

`crates/tamga-policy/src/facts.rs` testlari namunasida yangi testlar yozing: bir xil niyatdagi
amalning (maxfiy faylni tarmoqqa yuborish, papkadan tashqarida o'chirish, skriptni internetdan
olib ishga tushirish) turli sintaktik shakllarida faktlar to'g'ri chiqadimi. Bash, PowerShell va
MCP (`facts::generic`) uchun alohida ko'ring. Agent kerak emas — hook'ka Claude Code JSON'ini
bevosita berish mumkin (`demo/run-demo.ps1 -Simulate` dagi `Send-Hook` namunasi).

Har bir aniqlanmagan holat uchun: bu tuzatiladigan xatomi yoki K4 chegarasimi; OS sensori uni
`os.observed` sifatida ko'rdimi. Faqat qum qutisidagi soxta sirlar va `.invalid` manzillar.

### E. Daemon, IPC va holat

1. K1 va K2 ni qum qutisida tasdiqlang, jurnalda iz qolishini tekshiring.
2. Pipe: `reject_remote_clients`, standart DACL, `first_pipe_instance`; boshqa jarayon nomni
   oldindan egallab olsa nima bo'ladi.
3. Juda katta yoki noto'g'ri JSON, ko'p parallel ulanishlar — daemon qotmaydimi, xotira o'smaydimi.
4. Yiqilishga chidamlilik: yozish o'rtasida jarayonni o'ldiring (`Stop-Process`) — `.partial`
   tiklanishi, checkpoint, taint holati, yarim qolgan kalit almashtirish (`signing-seed-next-v1`).
5. `ask` muddati tugaganda rad etiladimi; `shutdown` kutilayotganlarni rad etadimi.

### F. Kalitlar

1. `tamga key rotate` → `tamga verify`, `tamga-verify`, `verify-py` bir xil kalitlar zanjirini
   ko'rsatadimi.
2. `spec/test-vectors/rotation.json` ga yangi salbiy holatlar qo'shing (bir checkpoint ichida ikki
   almashtirish, almashtirishdan keyin eski checkpoint faylning oxirida).
3. Zaxira: noto'g'ri parol, o'zgartirilgan sarlavha, boshqa jurnal langari, `--force` siz qayta
   yozish — hammasi rad etiladimi. Eski zaxirani tiklaganda daemon ishga tushmasligi (C9).

### G. Differensial tekshiruv (C10)

Tasodifiy mutatsiyalar (bayt almashtirish, qator o'chirish/takrorlash, checkpoint maydonlarini
o'zgartirish) generatori yozing va har bir kirishni Rust (`tamga-verify`) hamda Python
(`python -m tamga_verify --json`) ga bering. Natija (kod, indeks) farq qilgan har bir holat — topilma.

### H. O'rnatuvchi va tarqatish

1. `scripts/build-installer.ps1`, so'ng jim o'rnatish / ustidan o'rnatish / o'chirish (daemon
   ishlab turganda ham). Qoldiqlar: papka, registr, Start menyu, `settings.json`.
2. Imzo: `Get-AuthenticodeSignature` barcha `.exe` larda (o'rnatuvchi, `uninstall.exe`, sidecar'lar).
   Imzosiz dev build ogohlantirish berishini tekshiring.
3. `SHA256SUMS.txt` o'rnatuvchiga mosmi.

---

## 6. Hisobot shakli

```markdown
# TAMGA audit hisoboti — <sana>, commit <sha>

## Xulosa
- Topilmalar: Critical N, High N, Medium N, Low N, Info N
- Tekshirilgan da'volar: C1 ✓, C2 ✓, ... (✗ — rad etildi, ? — tekshirilmadi)

## Topilmalar
### [H-1] <qisqa nom> — High — C5 — verified
- Joy: `crates/...:123`
- Takrorlash: <buyruqlar va kirish>
- Kutilgan / haqiqiy: ...
- Ta'sir: ...
- Tuzatish taklifi: ...

## Savollar (tasdiqlanmagan)
## Tekshirilmagan qismlar va sababi
```

Og'irlik: **Critical** — agent `deny` qilingan amalni bajara oladi yoki buzilgan jurnal tekshiruvdan
o'tadi; **High** — himoyani foydalanuvchi bilmagan holda o'chirish yoki sirning ochiq saqlanishi;
**Medium** — faqat maxsus sharoitda ishlaydigan aylanib o'tish; **Low** — qiyin foydalaniladigan
yoki ta'siri cheklangan; **Info** — hujjat va chegara masalalari.

---

## 7. Auditor uchun cheklovlar

- Haqiqiy foydalanuvchi sozlamalari, Credential Manager va haqiqiy jurnallarga tegilmaydi.
- Tarmoq sinovlari faqat `.invalid` domenlar va lokal manzillar bilan.
- Topilmalar avval loyiha egasiga yuboriladi; ochiq e'lon qilinmaydi.
