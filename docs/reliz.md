# Reliz o'rnatuvchisi (`SRV_1-Setup-<versiya>.exe`)

Foydalanuvchi uchun qadamlar: [qollanma.md](qollanma.md). Bu yerda — qanday yig'iladi,
ichida nima bor va nima sinalgan.

## Yig'ish

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
```

Kerak: `uv`, Inno Setup 6, `tools\caddy.exe`, `tools\nssm.exe`, ~2 GB bo'sh joy.
Natija: `release\SRV_1-Setup-<versiya>.exe` va yonida `.sha256` (ikkalasi gitga kirmaydi —
fayl GitHub'ning 100 MB chegarasidan katta). Oraliq to'plam `dist\SRV_1\` da qoladi
(706 MB, o'chirsa bo'ladi). Keyin imzolanadi — pastdagi [Imzo](#imzo) bo'limi.

| Qadam | Nima qiladi |
|-------|-------------|
| testlar | `uv run pytest`; o'tmasa o'rnatuvchi yig'ilmaydi (`-SkipTests` — o'tkazib yuborish) |
| Python | `uv` boshqaradigan Python 3.12 nusxalanadi (testlar, IDLE, tkinter/Tcl, pip'siz) |
| bog'liqliklar | `uv export --frozen --no-dev` → `uv pip install --require-hashes` (aynan `uv.lock` dagi versiyalar, xesh bilan) |
| SRV_1 | `git ls-files` bo'yicha: `core`, `sdk`, `shell`, `plugins`, `install`, qo'llanma (`git add` qilinmagan fayl bo'lsa yig'ish to'xtaydi) |
| tashqi dastur | `tools\caddy.exe`, `tools\nssm.exe` (NSSM xeshi tekshiriladi) |
| sinash | to'plamdagi Python bilan asosiy modullar import qilinadi, versiya solishtiriladi |
| `.pyc` | hammasi oldindan kompilyatsiya qilinadi (`unchecked-hash`) — `Program Files` yozishga yopiq |
| Inno Setup | `packaging\srv1.iss` → `release\` |

Versiya `pyproject.toml` dan olinadi; u `srv1_core`, `srv1_sdk`, `srv1_shell` dagi
`__version__` bilan bir xil bo'lishi shart (test bor).

## Imzo

```powershell
powershell -ExecutionPolicy Bypass -File packaging\sign.ps1
```

`packaging\sign.ps1` o'rnatuvchini **o'zi imzolangan** (self-signed) kod imzosi sertifikati
bilan imzolaydi (Authenticode, SHA-256):

- sertifikat `CN=SRV_1 Release (self-signed)`, RSA 3072, 5 yil; birinchi yugurishda joriy
  foydalanuvchining shaxsiy omborida (`Cert:\CurrentUser\My`) yaratiladi, keyingi safar
  o'shasi ishlatiladi;
- yopiq kalit eksport qilinmaydigan qilib yaratiladi: faylga ham, gitga ham tushmaydi.
  Shu Windows hisobi yo'qolsa, kalit ham yo'qoladi — yangi sertifikat yaratiladi va boshqa
  kompyuterlarga `.cer` qayta o'rnatiladi;
- ochiq qismi `release\SRV_1-codesign.cer` ga yoziladi (maxfiy emas);
- vaqt tamg'asi qo'yilmaydi (tashqi serverga so'rov yo'q): imzo sertifikat muddati
  tugaguncha (2031-11-14) amal qiladi;
- imzodan keyin fayl o'zgaradi — `.sha256` qayta yoziladi.

**Imzo nima beradi, nima bermaydi.** Imzo fayl yig'ilgandan keyin o'zgarmaganini ko'rsatadi
(fayl xususiyatlari → «Raqamli imzolar»). Lekin sertifikatni hech qaysi sertifikatlash
markazi tasdiqlamagan, shuning uchun **boshqa kompyuterda Windows baribir «Noma'lum
noshir» deb ogohlantiradi** — toki shu `.cer` o'sha kompyuterga o'rnatilmaguncha. Hamma
kompyuterda ogohlantirishsiz ishlashi uchun pullik (sertifikatlash markazi bergan) kod
imzosi sertifikati kerak.

**`.cer` ni boshqa kompyuterga o'rnatish** (ixtiyoriy; administrator PowerShell oynasida,
`.cer` turgan papkadan):

```powershell
Import-Certificate -FilePath SRV_1-codesign.cer -CertStoreLocation Cert:\LocalMachine\Root
Import-Certificate -FilePath SRV_1-codesign.cer -CertStoreLocation Cert:\LocalMachine\TrustedPublisher
```

Diqqat: bundan keyin o'sha kompyuter shu kalit bilan imzolangan **har qanday** dasturga
ishonadi. Buni faqat o'z kompyuterlaringizda qiling va `.cer` barmoq izi kutilganiga teng
ekanini tekshiring (`Get-PfxCertificate SRV_1-codesign.cer | Format-List Thumbprint`).
Bekor qilish: `certlm.msc` da ikkala ombordan «SRV_1 Release (self-signed)» ni o'chiring.

Sinalgani: imzo qo'yildi, `Get-AuthenticodeSignature` imzolovchini to'g'ri ko'rsatadi, holat
`UnknownError` («zanjir ishonchsiz ildizda tugadi») — sertifikat ishonchli omborga
o'rnatilmagani uchun kutilgan holat. **Sinalmagan:** `.cer` ni ishonchli omborga o'rnatish
va undan keyin UAC hamda SmartScreen qanday ko'rinishi (bu kompyuterning xavfsizlik
sozlamalarini o'zgartirish bo'lardi — ataylab qilinmadi).

## O'rnatilgan papka

Repo tuzilmasini takrorlaydi — yadro plaginlar va `tools\` ni o'z fayliga nisbatan topadi,
shuning uchun kodda o'zgarish kerak bo'lmadi:

```
C:\Program Files\SRV_1\
  python\            # ko'chma Python 3.12 + kutubxonalar (Lib\site-packages)
  core\ sdk\ shell\  # srv1.pth orqali sys.path ga qo'shiladi
  plugins\           # ichki plaginlar
  tools\             # caddy.exe, nssm.exe
  install\           # service.ps1 va boshqalar (python\ ni o'zi topadi)
  docs\ licenses\ VERSION
```

PyInstaller ishlatilmagan: plaginlar papkadan dinamik yuklanadi, `subprocess` rejimidagi
plaginlar esa `python -m ...` bilan ishga tushadi — oddiy Python bilan bu hozirgidek ishlaydi.

## O'rnatuvchi nima qiladi

- Sehrgar o'zbekcha (Inno Setup'da o'zbekcha til fayli yo'q: inglizcha asos ustidan
  `[Messages]` va `[CustomMessages]` da yozilgan).
- O'rnatish turi: hamma uchun (administrator, `Program Files`) yoki faqat joriy
  foydalanuvchi uchun (UAC'siz).
- Bosh menyu: «SRV_1», «SRV_1 yadro (konsol)», «Qo'llanma», «SRV_1 ni olib tashlash»;
  ixtiyoriy Ish stoli yorlig'i. «SRV_1» oynasi yadroni o'zi ko'taradi (1.1.0 dan);
  «yadro (konsol)» faqat nosozlikni aniqlash uchun qoldi.
- Oxirgi sahifada «SRV_1 ni ochish» belgilangan holda turadi (1.1.0 dan).
- Yangilash va olib tashlashdan oldin oynasiz ishlayotgan yadro `install\stop-core.ps1`
  bilan tartibli to'xtatiladi (1.1.0 dan; `SRV_1` xizmati ishlab turgan bo'lsa bu qadam
  o'tkazib yuboriladi — xizmat pastdagi qoidaga ko'ra boshqariladi).
- `install\install.ps1 -SkipSync -NoShortcut` ni **o'rnatayotgan foydalanuvchi nomidan**
  yuritadi: `%PROGRAMDATA%\SRV_1` yo'q bo'lsa yaratiladi va faqat unga, SYSTEM va
  administratorlarga ochiladi; bor bo'lsa — tegilmaydi.
- Oxirgi sahifada ixtiyoriy «Windows xizmati sifatida o'rnatish»: alohida administrator
  oynasida `install\service.ps1 -Action install` (parolni Windows so'raydi; o'rnatuvchi
  parolni ko'rmaydi). Standart holatda belgilanmagan.
- **Xizmatga ehtiyotkorlik:** o'rnatuvchi `SRV_1` xizmatiga faqat u shu o'rnatilgan
  papkadan ishlayotgan bo'lsa tegadi (reyestrdagi NSSM `Application` yo'li bo'yicha):
  yangilashda to'xtatib, keyin qayta ishga tushiradi; olib tashlashda xizmatni ham olib
  tashlaydi. Boshqa papkadan (masalan, ishlab chiqish nusxasidan) o'rnatilgan xizmatga
  tegilmaydi.
- Olib tashlashda ma'lumotlar papkasi va `%APPDATA%\SRV_1\shell.json` qoladi.

## 1.1.1 (2026-11-14)

1.1.0 dan farqi — «Jurnal» sahifasida tarmoq paketlari: ushlash paytida davriy xulosa
(`netcap_stats`) va har bir belgilangan paket (`netcap_packet`); jurnal vaqti mahalliy;
plagin maydonlari `p_` qo'shimchasisiz ko'rinadi
([tarmoq-kuzatuvi.md](tarmoq-kuzatuvi.md#jurnalga-chiqish-jurnal-sahifasi)).

| Ko'rsatkich | Qiymat |
|-------------|--------|
| `SRV_1-Setup-1.1.1.exe` | 157,8 MB, imzolangan (1.1.0 dagi sertifikat bilan) |
| SHA-256 (imzolangan fayl) | `3202fb5b7396ec185cfbadf712e3b369e79d765ab355ce15c4acdc482202c1d2` |
| sertifikat barmoq izi (SHA-1) | `0134A8B5752CD8EDBD0CFAAD27F644238E63BC3F` |
| yig'ishdan oldingi testlar | 485 test o'tdi |

Sinalgani (jim rejimda vaqtinchalik papkaga o'rnatib, toza ma'lumotlar papkasi, port 8719):
yorliq buyrug'i bilan yadro o'zi ko'tarildi (`/health` → `1.1.1`); o'rnatilgan nusxada
loopback'da ushlash boshlandi va `/api/v1/logs` da `netcap_stats` hamda `netcap_packet`
satrlari paydo bo'ldi; `stop-core.ps1` yadroni to'xtatdi; olib tashlash toza. 1.1.0 dagi
to'liq tekshiruv (oynadagi tugma, xotira o'lchovi) 1.1.1 uchun **takrorlanmagan**; uning
«Sinalmagan» ro'yxati 1.1.1 ga ham tegishli.

## 1.1.0 (2026-11-14)

Ikki yangilik: tarmoq kuzatuvi ([tarmoq-kuzatuvi.md](tarmoq-kuzatuvi.md)) va serverni
oynadan ishga tushirish/to'xtatish ([shell.md](shell.md#server-yadroni-ishga-tushirish-va-toxtatish)).
Ikkinchisi 1.0.x dagi jiddiy kamchilikni tuzatadi: o'rnatilgan dastur yadroni o'zi ishga
tushirmas edi — yangi kompyuterda oyna token so'rar, token ko'chirilganda ham ulanadigan
narsa bo'lmas edi.

| Ko'rsatkich | Qiymat |
|-------------|--------|
| `SRV_1-Setup-1.1.0.exe` | 157,6 MB, imzolangan (o'zi imzolangan sertifikat) |
| SHA-256 (imzolangan fayl) | `6bf8dce4e25a82b469ec653717f79b0fdc0f3c0480ba69d9da6f9c4a790046eb` |
| sertifikat barmoq izi (SHA-1) | `0134A8B5752CD8EDBD0CFAAD27F644238E63BC3F`, 2031-11-14 gacha |
| to'plam hajmi | 706 MB (scapy qo'shildi) |
| yig'ishdan oldingi testlar | 478 test o'tdi |

**Sinalgani** — o'rnatuvchi jim rejimda (`/VERYSILENT /CURRENTUSER /TASKS=""`) vaqtinchalik
papkaga o'rnatildi; ma'lumotlar papkasi **yo'q** edi (boshqa kompyuterdagi holat), port 8719:

- yorliqdagi buyruqning o'zi (`python\pythonw.exe -m srv1_shell`): yadro 6,1 s da javob
  berdi, papka va `auth.token` yaratildi, oyna yadroga ulandi; yadro
  `python\python.exe -m srv1_core --no-console` bo'lib, oynasiz ishlaydi;
- oyna yopilgach yadro ishlashda davom etdi; oyna qayta ochilganda yangi yadro ochilmadi,
  o'shasiga ulandi;
- oyna ichidan (tugmani dastur bosdi, oyna ekranga chiqarilmadi, suratlar ko'zdan
  kechirildi): ishga tushish 3,5 s → «Serverni to'xtatish» 4,0 s, yadro jarayoni tugadi,
  plagin bo'limlari yopildi → «Serverni ishga tushirish» 4,5 s, bo'limlar qaytdi;
- `electronics`, `files`, `iot`, `itops`, `monitor` — `running`; tarmoq kuzatuvi moduli
  (scapy) to'plamdagi Python'da import bo'ladi;
- `install\stop-core.ps1` o'rnatilgan nusxadagi yadroni to'xtatdi (kod 0); auditda
  `core.shutdown` yozuvi bor;
- olib tashlash toza; mashinadagi mavjud `SRV_1` xizmati (ishlab chiqish nusxasidan)
  butun sinov davomida `Running` holatida qoldi.

Xotira (private, bo'sh holat, bir marta o'lchangan, ishga tushgandan ~45 s o'tib):
shell 74,4 MB + yadro 79,8 MB + yadroning ko'rinmas konsoli 6,2 MB = **160,4 MB**
(Caddy'siz — `hosting` bu sinovda ham port to'qnashuvi sabab `error` edi).

**Sinalmagan:**

- **boshqa (toza) kompyuter** — eng muhimi. Sinov shu mashinada, toza ma'lumotlar papkasi
  bilan o'tkazildi; boshqa kompyuterdagi nosozlik koddan aniqlangan va shu yerda
  takrorlangan holatda tuzatilgan, lekin o'sha kompyuterning o'zida tekshirilmagan;
- Windows xizmati yo'li: tugma `sc start/stop SRV_1` ni UAC bilan chaqirishi (administrator
  tasdig'i kerak; qaror mantiqi soxta UAC bilan sinalgan, haqiqiy UAC — yo'q);
- o'rnatuvchining yangilashdan oldin yadroni to'xtatishi (bu mashinada `SRV_1` xizmati
  ishlab turgani uchun o'rnatuvchi bu qadamni o'tkazib yubordi; skriptning o'zi sinalgan);
- haqiqiy sichqoncha bilan tugmani bosish va tasdiq oynasi (tugma dastur orqali bosilgan);
- `.cer` o'rnatilgandan keyingi UAC/SmartScreen ko'rinishi; sekin (HDD, 4 GB) mashinada
  ishga tushish vaqti (kutish chegarasi 90 s);
- 1.0.0 dagi «Sinalmagan» ro'yxatining qolgani (administrator rejimi, sehrgar sahifalari).

## 1.0.1 (2026-11-13)

1.0.0 dan farqi — uch tuzatish: muzlab qolgan loyihaga so'rov 120 s da 504 oladi
([hosting.md](hosting.md)), o'lgan Mosquitto o'zi qayta ko'tariladi ([iot.md](iot.md)),
`monitor` ogohlantirishlari Windows bildirishnomasi bo'lib chiqadi ([monitor.md](monitor.md)).

| Ko'rsatkich | Qiymat |
|-------------|--------|
| `SRV_1-Setup-1.0.1.exe` | 153,2 MB |
| SHA-256 | `46984484c2707bffc3b51615e10a808694845eb5ba74211fef081d6a8d500e35` |
| yig'ishdan oldingi testlar | 400 test o'tdi |

Sinalgani (jim rejimda vaqtinchalik papkaga o'rnatib): yadro ishga tushdi (`/health` →
`1.0.1`), yangi modullar import qilinadi, `monitor` chegarasi pasaytirilganda
ogohlantirish ko'tarildi; olib tashlash toza. 1.0.0 dagi to'liq tekshiruv (shell oynasi,
`data` plagini, xotira o'lchovi) 1.0.1 uchun **takrorlanmagan**; quyidagi «Sinalmagan»
ro'yxati 1.0.1 ga ham tegishli.

Yig'ish skripti endi `git add` qilinmagan fayl bo'lsa to'xtaydi: to'plamga faqat git
biladigan fayllar tushadi.

## 1.0.0 (2026-11-13) — o'lchangan va sinalgan

| Ko'rsatkich | Qiymat |
|-------------|--------|
| `SRV_1-Setup-1.0.0.exe` | 153,2 MB |
| SHA-256 | `f5d2a75da4d77d5b94b6e29d39fb04d9b0dce7cd0b1639465f9d2140abce76f1` |
| o'rnatilgan hajm | 694 MB, 13 758 fayl |
| eng og'ir qismlar | PyQt6 214 MB, polars 160 MB, `.pyc` 65 MB, Caddy 50 MB |
| yig'ishdan oldingi testlar | 386 test o'tdi |

Shu (ishlab chiqish) mashinasida sinalgani — o'rnatuvchi jim rejimda (`/VERYSILENT
/CURRENTUSER`) vaqtinchalik papkaga o'rnatildi:

- yadro o'rnatilgan Python'dan ishga tushdi (alohida ma'lumotlar papkasi, 8719-port):
  `/health` → `1.0.0`; `electronics`, `files`, `iot`, `itops`, `monitor` — `running`;
- og'ir `data` plagini yoqildi: alohida jarayon aynan o'rnatilgan `python\python.exe` dan
  ko'tarildi, keyin o'chirildi;
- shell o'rnatilgan `pythonw.exe` dan ochildi va yadroga ulandi (oyna surati ko'zdan
  kechirildi: to'q mavzu, o'zbekcha, grafiklar chiziladi);
- xotira (private, bo'sh holatda, bir marta o'lchangan): yadro 78,4 MB + shell 72,4 MB +
  konsol 6,6 MB = **157,4 MB** (Caddy'siz — pastga qarang);
- ishlash paytida dastur papkasida birorta fayl o'zgarmadi yoki paydo bo'lmadi;
- olib tashlash: papka va yorliqlar to'liq ketdi; mashinadagi mavjud `SRV_1` xizmati
  (ishlab chiqish nusxasidan) `Running` holatida qoldi;
- sehrgarning birinchi sahifasi suratga olindi: o'zbekcha, «Tanlash...» tugmasi ham.

**Sinalmagan:**

- **`hosting` o'rnatilgan nusxada**: sinov paytida mashinada asosiy `SRV_1` xizmati
  ishlab turgani uchun 9099/8080/2019 portlar band edi va plagin `error` holatida
  qoldi (kutilgan to'qnashuv). O'rnatilgan `tools\caddy.exe` ishga tushadi
  (`caddy version` → 2.11.9), lekin sayt joylash shu nusxada tekshirilmagan;
- sehrgarning qolgan sahifalari va «hamma foydalanuvchilar uchun» (administrator) rejimi,
  `Program Files` ga o'rnatish, o'rnatuvchi ichidan xizmatni o'rnatish, yangilashda
  xizmatni to'xtatib-qayta ishga tushirish, olib tashlashda xizmatni olib tashlash —
  administrator huquqi va sichqoncha kerak;
- toza Windows 10 / 4 GB mashina (bu mashinada Python va `uv` bor);
- SmartScreen va antivirus munosabati (fayl imzolanmagan).

## Ma'lum cheklovlar

- 1.1.0 **o'zi imzolangan** sertifikat bilan imzolangan: `.cer` o'rnatilmagan kompyuterda
  Windows baribir «Noma'lum nashriyotchi» deb ogohlantiradi ([Imzo](#imzo)). 1.0.x imzolanmagan.
- Npcap o'rnatuvchiga kirmaydi (litsenziyasi qayta tarqatishga ruxsat bermaydi): tarmoq
  kuzatuvi uchun uni alohida o'rnatish kerak ([tools/README.md](../tools/README.md)).
- **PyQt6 GPL v3** da: o'rnatuvchini boshqalarga tarqatganda GPL shartlari amal qiladi
  (`licenses\THIRD-PARTY.md`).
- Hajm kattaligi: Qt'ning ishlatilmaydigan qismlari (Quick/QML, ~60 MB) ataylab
  olib tashlanmagan — nimadir sinib qolishi xavfi tejalgan joydan qimmat.
- Administrator boshqa hisob bo'lsa (UAC'da boshqa foydalanuvchi kiritilsa), xizmat
  o'sha hisob nomidan o'rnatiladi; kerakli hisobni `service.ps1 -Account` bilan bering.
- cloudflared, Mosquitto, avrdude o'rnatuvchiga kirmaydi.
