# M-Pay Pay Sandbox — 10 daqiqalik bank namoyishi

Auditoriya: bank to'lov/xavfsizlik bo'limi. Maqsad: M-Pay infratuzilmasi (Vault, Shield, PQ Link,
Wallet SDK) bankning o'z serverida qanday ishlashini haqiqiy binarlar bilan ko'rsatish.
Hamma ma'lumot fiktiv: BIN `990000`–`990099`, "M-Pay Test Scheme".

## Tayyorgarlik (namoyishdan oldin, 5 daqiqa)

```bash
cargo build -p mpay-server -p mpay-terminal-sim
```

```bash
DEMO_AUTO=1 bash scripts/demo.sh
```

Avtomatik repetitsiya `DEMO OK` bilan tugashi shart. Namoyishda interaktiv rejim (har qadamdan oldin
Enter): `bash scripts/demo.sh`. Terminal shrifti katta, qorong'i fon; ikkinchi oynada
`docs/architecture.md` diagrammasi. Telefonlar bo'lsa — §7 uchun `docs/android-testing.md` §3 tayyorgarligi.

## Ssenariy

| Vaqt | Qadam | Ekranda | Aytiladigan asosiy fikr |
|---|---|---|---|
| 0:00–1:00 | Kirish | arxitektura diagrammasi | M-Pay pul o'tkazmaydi va saqlamaydi; bankning serverida (on-prem) ishlaydi. Bitta binar, HTTP API va CLI, dashboard yo'q. |
| 1:00–2:00 | 1. `init` + `serve` | PQ Link barmoq izi, `healthz` | Kalitlar faqat KeyStore orqali: sandbox'da memory, bankda PKCS#11 HSM (SoftHSM bilan CI'da sinalgan). Server identifikatori — klassik + post-kvant (Ed25519 + ML-DSA-65). |
| 2:00–3:30 | 2. Tokenizatsiya | `provision` → GREEN, DPAN `990077******…`; `db_scan_pans` | Har qurilma PQ Link (X25519 + ML-KEM-768) va Android Key Attestation bilan ulanadi. FPAN bazada faqat shifrlangan (AES-256-GCM, DEK/KEK), qidiruv HMAC indeks orqali — skaner ochiq PAN topmaydi. |
| 3:30–5:00 | 3. Tap-to-pay | `00` + `ARPC: to'g'ri`; `6986`; `--cdcvm` → `00`; `replenish` | Har tapda bir martalik kalit (LUK) bilan kriptogramma; emitent ARPC qaytaradi. 1 000 000 so'mdan katta summaga biometriya (CDCVM) shart. LUK'lar tugasa PQ Link orqali to'ldiriladi. Katta summa Shield'da REVIEW bo'ladi — siyosat bo'yicha tasdiqlanadi (`APPROVED_AFTER_REVIEW`). |
| 5:00–7:00 | 4. Shield | `59` (skor ~997); YELLOW + OTP; RED `IDV_DEVICE_FARM` | Real-time qaror < 2 ms p99 (M5). Karta testlash, akkaunt o'g'irlash (ATO), qurilma fermasi. Qoidalar TOML'da (bank o'zi tahrirlaydi) + ONNX ML model; sabab kodlari tushuntiriladi. |
| 7:00–8:00 | 5. Emitent javoblari | `51`, `91` | ISO 8583 orqali emitent emulyatori: mablag' yetarli emas, emitent ishlamayapti. Real integratsiyada shu port bankning protsessingiga ulanadi. |
| 8:00–9:30 | 6. Audit va loglar | maskalangan PAN'lar; `audit-verify` → to'g'ri; UPDATE rad; buzish → `seq 2` | Loglarda faqat `990012******0013` ko'rinishi. Audit append-only (trigger) va xesh-zanjirli: hatto DB administratori trigger'ni o'chirib yozuvni o'zgartirsa ham tekshiruv aniq yozuvni ko'rsatadi. |
| 9:30–10:00 | Raqamlar va savollar | `docs/load-report.md`, `docs/fuzz-report.md` | Yuk: 238 avtorizatsiya/s bitta noutbukda, p99 155 ms (32 parallel); fuzz: 7 maqsad, ~24 mln yugurish, crash yo'q. |

## 7. Telefon bilan qism (ixtiyoriy, +3 daqiqa)

Ikki NFC'li Android: `wallet-demo` ("M-Pay Hamyon") va `terminal-app` ("M-Pay Terminal").
Hamyonda karta qo'shiladi → "To'lovga tayyorlash" (barmoq izi) → telefonlar tekkiziladi →
terminalda **MA'QULLANDI**, kod `00`, maskalangan DPAN va Shield bali. Tartib:
`docs/android-testing.md` §3.

**Diqqat:** ikki telefonli NFC tap hali haqiqiy qurilmalarda sinalmagan (M6 ochiq bandi) —
namoyishdan oldin albatta repetitsiya qiling. Telefonlar bo'lmasa bu qism o'tkazib yuboriladi;
asosiy 10 daqiqa telefonsiz to'liq ishlaydi.

## Ehtimoliy savollar

* **"Bu haqiqiy Visa/Mastercard/Humo/Uzcard bilan ishlaydimi?"** — Yo'q, sandbox o'z test sxemasida.
  Algoritmlar va TLV tuzilmasi almashtiriladigan (`docs/specs/emv-profile.md`); real scheme
  sertifikatsiyasi alohida bosqich.
* **"Post-kvant nima uchun hozir?"** — "hozir yig', keyin och" hujumi: provisioning trafigi (LUK'lar)
  bugun yozib olinsa, kelajakda ochilishi mumkin. Gibrid: klassik algoritm buzilmasa ham himoya saqlanadi.
* **"Ma'lumot qayerda saqlanadi?"** — bankning o'z serverida; M-Pay bulutga hech narsa yubormaydi.
* **"Ishlash tezligi?"** — §6 raqamlari; production DB va HSM bilan o'lchash pilot bosqichida.

## Muammo bo'lsa

* Port band: `MPAY_DEMO_PORT=18444 bash scripts/demo.sh`.
* Skript istalgan qadamda kutilgan natija chiqmasa `XATO: '…' kutilgan edi` bilan to'xtaydi —
  `target/demo/server.log` ni ko'ring. Har yugurish `target/demo/` ni yangidan yaratadi.
