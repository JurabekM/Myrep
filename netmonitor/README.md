# NetMonitor 4.0.0

Tanlangan tarmoq interfeysidagi IPv4/IPv6 paketlarni ushlaydi, har birini konsolga chiqaradi,
JSON Lines faylga yozadi va oddiy xavf belgilarini tekshiradi. `netmonitor_new_v3_9.py`
skriptining tuzatilgan davomi: bitta fayl (`netmonitor.py`), Windows uchun bitta `NetMonitor.exe`.

**Faqat o'z tarmog'ingizda yoki egasining ruxsati bilan ishlating.**

## Ishga tushirish

1. **Npcap** drayverini o'rnating: <https://npcap.com/#download>. U exe ichiga kirmaydi
   (litsenziyasi qayta tarqatishga ruxsat bermaydi). Npcap «faqat administratorlar uchun» rejimida
   o'rnatilgan bo'lsa, dasturni administrator nomidan oching.
2. `NetMonitor.exe` ni ishga tushiring, ro'yxatdan interfeys raqamini kiriting.
3. Birinchi ishga tushishda yonida `config.json` (standart sozlamalar) va `logs_pro\` paydo bo'ladi.
   Dastur papkasi yozishga yopiq bo'lsa (`Program Files`), ular `%LOCALAPPDATA%\NetMonitor` ga tushadi.

```
NetMonitor.exe                      interfeysni so'raydi
NetMonitor.exe --iface 0            ro'yxatdagi 0-interfeys (raqam, nom yoki IP manzil)
NetMonitor.exe --list-ifaces        interfeyslar ro'yxati
NetMonitor.exe --config D:\x.json   boshqa sozlamalar fayli (jurnal ham o'sha papkaga)
NetMonitor.exe --self-test          drayversiz o'zini sinaydi (50 ta sun'iy paket)
```

Manba koddan: `pip install --require-hashes -r requirements.txt`, keyin `python netmonitor.py`
(Python 3.10+; Linux'da ham ishlaydi — root huquqi bilan).

## Buyruqlar (ushlash davomida)

| Buyruq | Vazifasi |
|--------|----------|
| `pause` / `resume` | kuzatuvni to'xtatib turish / davom ettirish |
| `exclude <manzil>` | manzilni kuzatuvdan chiqarish: `192.168.1.5`, `10.0.0.0/8`, `fe80::1`; bir nechtasi vergul bilan |
| `unexclude <manzil>` | ro'yxatdan olib tashlash |
| `list` | chiqarilgan manzillar |
| `quiet` / `verbose` | paket satrlarini yashirish / ko'rsatish (signallar va fayl jurnali davom etadi) |
| `status` | holat va hisoblagichlar |
| `help`, `exit` / `quit` | yordam, chiqish (Ctrl+C ham ishlaydi) |

Chiqarilgan manzillar `netmonitor_state.json` da saqlanadi va keyingi ishga tushirishda tiklanadi.

## Sozlamalar (`config.json`)

Fayldagi qiymatlar standartlar ustiga qo'yiladi — faqat o'zgartirmoqchi bo'lganingizni yozsangiz
yetarli. To'liq namuna: `config.example.json`. v3.9 ning `config.json` fayli o'zgarishsiz ishlaydi.

| Kalit | Standart | Ma'nosi |
|-------|----------|---------|
| `log_folder` | `logs_pro` | jurnal papkasi (nisbiy bo'lsa — dastur papkasiga nisbatan) |
| `packet_log_filename` | `captured_packets.json` | paketlar jurnali (har satr — bitta JSON) |
| `log_rotation_lines`, `max_packet_log_files` | 10000, 50 | rotatsiya chegarasi va saqlanadigan arxivlar soni |
| `system_metrics_interval_sec` | 120 | holat xulosasi oralig'i (CPU, RAM, hisoblagichlar); 0 — o'chiq |
| `capture_filter` | yo'q | BPF filtri, masalan `"tcp port 80"` |
| `excluded_ips` | `[]` | boshidanoq chiqariladigan manzillar |
| `console.show_packets` | `true` | paket satrlarini ko'rsatish (`quiet` bilan bir xil) |
| `console.max_lines_per_sec` | 50 | soniyasiga ko'pi bilan shuncha paket satri; 0 — cheksiz. Maxfiy maydonli va signal bergan paketlar har doim chiqadi; faylga hammasi yoziladi |
| `console.payload_preview_bytes` | 150 | konsolda paket matnidan ko'rsatiladigan qism |
| `payload.mask_sensitive_values` | `true` | parol/token **qiymatlarini** `********` bilan almashtirish (konsol va fayl) |
| `payload.log_max_bytes` | 2048 | faylga yoziladigan paket matni uzunligi; 0 — yozilmaydi |
| `payload.sensitive_keywords` | ro'yxat | maxfiy maydon nomlari (`password`, `token`, ...) |
| `geolocation.enabled` | `false` | tashqi IP manzillar egasini `ip-api.com` dan so'rash |
| `security_monitoring.*` | yoqilgan | pastdagi tekshiruvlar |

### Xavf tekshiruvlari

| Signal | Qachon chiqadi |
|--------|----------------|
| `PORT SKANERLASH` | bitta manbadan bitta manzilga 10 s ichida 15 tadan ko'p turli portga **yangi ulanish urinishi** (TCP SYN, ACK'siz) |
| `NULL / FIN / Xmas Scan` | TCP bayroqlari mos ravishda bo'sh, faqat `F`, `FPU` |
| `Shubhali port` | ro'yxatdagi **manzil** portiga yangi murojaat (TCP SYN yoki UDP); standart: 23, 4444, 5555, 6667, 31337 |
| `Ochiq matnda maxfiy maydon` | shifrlanmagan paketda `nom=qiymat` / `nom: qiymat` ko'rinishidagi maydon yoki FTP/POP3 `USER`/`PASS` buyrug'i |
| `Shubhali payload` | paket matnida `suspicious_payload_keywords` dagi so'z |

Bir xil signal (tur, manba, manzil) `alert_quiet_sec` (60 s) ichida takrorlanmaydi.

## Maxfiylik

- Parol va token **qiymatlari standart holatda yashiriladi** — konsolda ham, faylda ham; signal
  faqat maydon nomini ko'rsatadi. Qiymatlarni ko'rish kerak bo'lsa: `payload.mask_sensitive_values: false`.
- Yashirish evristik: faqat `nom=qiymat` shakllari va paketning dastlabki 4096 bayti tekshiriladi.
  Boshqa ko'rinishdagi sir (yoki ikki paketga bo'lingani) jurnalga ochiq tushishi mumkin —
  `logs_pro\` papkasini himoyalang yoki `payload.log_max_bytes: 0` qiling.
- Geolokatsiya standart holatda o'chiq. Yoqilsa, tashqi IP manzillar `ip-api.com` ga yuboriladi
  (bepul xizmat faqat HTTP orqali ishlaydi — so'rovlar tarmoqda ochiq ko'rinadi).

## v3.9 dan farqi

| № | v3.9 dagi muammo | 4.0.0 da |
|---|------------------|----------|
| 1 | interfeys raqamini buyruqlar oqimi «yeb qo'yardi» (ikki oqim bitta kiritishni o'qirdi) | buyruqlar interfeys tanlangandan keyin tinglanadi; `--iface` bor |
| 2 | bitta buzuq paket butun ushlashni to'xtatardi | har paket alohida himoyalangan; xato sanaladi va oraliq bilan yoziladi. scapy 2.6+ dagi DNS savollar ro'yxati hisobga olingan |
| 3 | geolokatsiya har yangi IP uchun ushlashni 2 s gacha to'xtatardi; xato natija keshlanmasdi; o'z so'rovlari ham ushlanardi | so'rovlar alohida oqimda, 1,6 s oraliq bilan; xato 10 daqiqa keshlanadi; HTTP 429 da 60 s tanaffus; xizmatning o'z manzillari kuzatuvga tushmaydi; chiqarilgan manzillar so'ralmaydi |
| 4 | har qanday paket «port skanerlash» ga sanalardi (CDN javoblari soxta signal berardi); jadval cheksiz o'sardi | faqat SYN, (manba, manzil) bo'yicha, qat'iy oyna; jadvallar 5000 yozuv bilan cheklangan; takror signal bostiriladi |
| 5 | DNS nomi tozalanmasdan konsolga chiqardi (ESC kodlari o'tardi) | paket matni bilan bir xil tozalanadi |
| 6 | `User-Agent`, `keyboard`, `bypass` «xavfli» deb bo'yalardi; `password` ichida `pass` qayta bo'yalardi; `PassWord` bo'yalmasdi; faqat dastlabki 150 belgi tekshirilardi | faqat `nom=qiymat` shakli, katta-kichik harfdan qat'i nazar, bir o'tishda; butun matn (4096 baytgacha) tekshiriladi |
| 7 | `172.` bilan boshlangan hamma manzil «ichki» sanalardi; multicast/broadcast so'ralardi | `ipaddress` moduli: faqat haqiqatan ommaviy manzillar so'raladi |
| 8 | bir soniyada ikki rotatsiya — nom to'qnashuvi, keyin har paketda xato | noyob arxiv nomi; band faylda rotatsiya 100+ satrdan keyin qayta uriniladi |
| 9 | `01.1.1.1` qabul qilinardi (hech qachon mos kelmaydi); IPv6 va tarmoq (CIDR) yo'q; IPv6 paketlar ko'rinmasdi | `ipaddress` bilan tekshiruv; IPv6 va CIDR bor; IPv6 paketlar qayta ishlanadi |
| 10 | `SystemMonitor` bo'sh edi, `psutil` ishlatilmasdi | holat xulosasi (CPU, RAM, hisoblagichlar) va jurnalni diskka tushirish |
| 11 | scapy har paketda qayta import qilinardi | importlar fayl boshida |
| 12 | konsolda `\| \| MAC:` | qismlar bitta ajratgich bilan |
| 13 | paket satrlari va jurnal xabarlari aralashardi; ekran to'lib ketardi | bitta qulf; soniyasiga 50 satr chegarasi; `quiet` / `verbose` |
| 14 | jurnal joriy papkaga, sozlama skript papkasiga nisbatan edi | hammasi dastur papkasiga nisbatan |
| 15 | maxfiy so'zlar kodda, shubhali so'zlar sozlamada edi | ikkalasi ham sozlamada (`payload.sensitive_keywords`) |
| 16 | chiqarilgan manzillar qayta ishga tushganda yo'qolardi | `netmonitor_state.json` |
| 17 | tozalash bayt-bayt (sekin); `\` ekranlanmasdi; kirill matni `\xd0...` bo'lardi | jadval orqali; `\` → `\\`; to'g'ri UTF-8 matn o'qiladigan qoladi (boshqaruv va yo'nalish belgilari — yo'q) |
| 18 | `exit` jurnalni yopmasdan chiqardi | avval jurnal yopiladi va holat saqlanadi |
| 19 | `scapy.arch.windows` importi boshqa tizimda yiqilardi | Windows'ga xos qism faqat Windows'da yuklanadi |
| — | paket jurnali har paketda ochib-yopilardi | fayl ochiq turadi, har soniyada diskka tushiriladi |
| — | Npcap yo'q bo'lsa tushunarsiz xato | aniq xabar va havola; oyna Enter bosilguncha yopilmaydi |

Xulq-atvordagi o'zgarishlar (v3.9 ga o'rgangan bo'lsangiz):

- `config.json` bo'lmasa yoki unda kalit yozilmagan bo'lsa, xavf tekshiruvlari **yoqilgan** (v3.9 da o'chiq edi);
- parol qiymatlari standart holatda yashiriladi;
- «shubhali port» endi faqat manzil porti va faqat yangi murojaat uchun;
- konsolga soniyasiga ko'pi bilan 50 paket satri chiqadi (faylga — hammasi);
- geolokatsiya natijasi paketga darhol emas, keshga tushgandan keyin qo'shiladi (birinchi paketlarda `null`).

## Imzo

`NetMonitor.exe` **o'zi imzolangan** (self-signed) kod imzosi sertifikati bilan imzolangan
(Authenticode, SHA-256, `CN=NetMonitor Release (self-signed)`, RSA 3072, 5 yil).

- CI (GitHub Actions) har yig'ishda **yangi, bir martalik** sertifikat yaratadi va imzodan keyin
  yopiq kalitni o'chiradi: bu kalit bilan boshqa hech narsa imzolanmaydi. Har reliz sertifikati boshqa.
- Imzo fayl yig'ilgandan keyin o'zgarmaganini ko'rsatadi (fayl xususiyatlari → «Raqamli imzolar»).
  Lekin sertifikatni hech qaysi sertifikatlash markazi tasdiqlamagan, shuning uchun **Windows
  «Noma'lum noshir» deb ogohlantiradi**, SmartScreen ham ogohlantirishi mumkin. Ogohlantirishsiz
  ishlashi uchun pullik (sertifikatlash markazi bergan) kod imzosi sertifikati kerak.
- Vaqt tamg'asi qo'yilmagan: imzo sertifikat muddati tugaguncha amal qiladi.

Tekshirish (PowerShell):

```powershell
Get-FileHash NetMonitor.exe -Algorithm SHA256        # NetMonitor.exe.sha256 dagi qiymat bilan bir xil bo'lsin
Get-AuthenticodeSignature NetMonitor.exe | Format-List Status, SignerCertificate
# Status: UnknownError («zanjir ishonchsiz ildizda tugadi») — o'zi imzolangan uchun kutilgan holat.
# HashMismatch — fayl imzodan keyin o'zgargan: ishlatmang.
```

Ixtiyoriy — shu kompyuterda noshirni ishonchli qilish (administrator PowerShell, `.cer` turgan papkadan):

```powershell
Import-Certificate -FilePath NetMonitor-codesign.cer -CertStoreLocation Cert:\LocalMachine\Root
Import-Certificate -FilePath NetMonitor-codesign.cer -CertStoreLocation Cert:\LocalMachine\TrustedPublisher
```

Buni faqat o'z kompyuteringizda va `.cer` barmoq izi kutilganiga teng bo'lsa qiling
(`Get-PfxCertificate NetMonitor-codesign.cer | Format-List Thumbprint`). Bekor qilish: `certlm.msc`
da ikkala ombordan «NetMonitor Release (self-signed)» ni o'chiring.

## Yig'ish

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build.ps1   # testlar -> PyInstaller -> exe ni sinash -> release\
powershell -ExecutionPolicy Bypass -File packaging\sign.ps1    # doimiy sertifikat (Cert:\CurrentUser\My) bilan imzolash
```

Kerak: Python 3.12. Kutubxonalar xesh bilan qulflangan (`requirements*.txt`). Versiyani
o'zgartirgach qayta yaratish:

```bash
uv pip compile requirements.in --universal --python-version 3.12 --generate-hashes --no-header -o requirements.txt
uv pip compile requirements-dev.in --universal --python-version 3.12 --generate-hashes --no-header -o requirements-dev.txt
```

CI: `.github/workflows/netmonitor.yml` — Linux'da `ruff`, `pytest`, jonli ushlash sinovi; Windows'da
yig'ish, imzolash va imzolangan exe ni sinash. Tayyor fayllar ish sahifasida
`NetMonitor-<versiya>-signed` artefakti bo'lib turadi.

## Nima sinalgan

| Qayerda | Nima |
|---------|------|
| Linux va Windows (CI) | 54 ta test (`pytest`), `ruff` |
| Linux (CI) | jonli ushlash haqiqiy interfeysda: paketlar ushlandi, parol yashirildi, `exclude` va `pause` ishladi, `exit` toza chiqdi (`tests/live_smoke.py`) |
| Windows (CI), imzolangan exe | `--version`; `--self-test` (50 ta sun'iy paket fayldan o'qilib butun zanjirdan o'tadi); `--list-ifaces` (Windows interfeyslari ro'yxati); Npcap yo'q mashinada tushunarli xabar va 3-kod; imzo va SHA-256 |

**Sinalmagan:** Windows'da haqiqiy Npcap drayveri bilan jonli ushlash — CI mashinasiga Npcap'ni
jim o'rnatib bo'lmaydi. Ushlash chaqiruvi v3.9 dagi bilan bir xil (`sniff(iface="\Device\NPF_{GUID}")`),
lekin 4.0.0 ning o'zi Npcap bilan faqat sizning kompyuteringizda tekshiriladi. SmartScreen va
antiviruslarning munosabati ham sinalmagan.

## Ma'lum cheklovlar

- TCP oqimi yig'ilmaydi: bir nechta paketga bo'lingan matn bo'lak-bo'lak tekshiriladi.
- HTTPS va boshqa shifrlangan trafik ichidan hech narsa ko'rinmaydi (faqat manzillar va portlar).
- Windows'da loopback (`127.0.0.1`) interfeysi ro'yxatda yo'q; kerak bo'lsa `--iface` bilan nomini bering.
- Bitta exe har ishga tushishda o'zini vaqtinchalik papkaga ochadi (1–2 s); ba'zi antiviruslar
  PyInstaller bilan yig'ilgan dasturlarni shubhali deb belgilashi mumkin.
