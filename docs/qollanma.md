# SRV_1 — foydalanuvchi qo'llanmasi

SRV_1 — Windows 10 kompyuteringizda ishlaydigan kichik server: fayllarni
kuzatadi va qidiradi, saytlar va kichik dasturlarni joylaydi, datchik va
platalar bilan ishlaydi, jadvallarni tahlil qiladi, kompyuterni boshqarishga
yordam beradi. Ikki qismdan iborat:

- **yadro** — fonda ishlaydi, oynasi yo'q;
- **shell** — «SRV_1» oynasi; yadroni shu orqali boshqarasiz.

Hech narsa internetga o'zi chiqmaydi: yadro va saytlar faqat shu kompyuterdan
ochiladi (`127.0.0.1`). Tashqariga ochish — faqat siz ataylab yoqsangiz
([Saytni internetga ochish](#saytni-internetga-ochish)).

## 1. O'rnatish

### Oson yo'l — `SRV_1-Setup-<versiya>.exe`

Kerak: Windows 10 x64 (yoki yangisi), taxminan 0,8 GB bo'sh joy. Python, `uv` va
boshqa narsa kerak emas — hammasi o'rnatuvchi ichida (Caddy va NSSM ham).

1. `SRV_1-Setup-<versiya>.exe` ni oching. Fayl o'zi imzolangan sertifikat bilan
   imzolangan: Windows uni tanimaydi va «Noma'lum nashriyotchi» deb ogohlantiradi:
   «Batafsil» → «Baribir ishga tushirish». Ogohlantirish chiqmasligi uchun
   o'rnatuvchi yonidagi `SRV_1-codesign.cer` ni shu kompyuterga o'rnatish mumkin
   ([reliz.md](reliz.md#imzo)); bu ixtiyoriy.
2. O'rnatish turini tanlang: «Hamma foydalanuvchilar uchun» (administrator
   huquqi so'raladi, `C:\Program Files\SRV_1`) yoki «Faqat men uchun».
3. Oxirgi sahifada ikki belgi bor:
   - **«Windows xizmati sifatida o'rnatish»** — belgilasangiz, administrator
     oynasi ochiladi va Windows parolingiz so'raladi; yadro kompyuter yonganda
     o'zi ishga tushadigan bo'ladi ([2-bo'lim](#2-yadroni-ishga-tushirish)).
   - «SRV_1 ni ochish» (belgilangan) — boshqaruv oynasini ochadi.
4. Boshqa hech narsa kerak emas: «SRV_1» oynasi ochilganda server (yadro) o'zi
   ishga tushadi ([2-bo'lim](#2-yadroni-ishga-tushirish)).

Quyidagi bo'limlardagi `install\service.ps1` kabi buyruqlar o'rnatilgan
papkadan (`C:\Program Files\SRV_1`) bajariladi; `uv run python` o'rniga
`python\python.exe` yoziladi.

Olib tashlash: «Dasturlar va komponentlar» → SRV_1. Xizmat ham olib tashlanadi;
ma'lumotlar papkasi (`C:\ProgramData\SRV_1`) **qoladi** — kerak bo'lmasa, o'zingiz
o'chirasiz. cloudflared, Mosquitto va avrdude o'rnatuvchiga kirmaydi: kerak
bo'lsa, `tools\` ga qo'yiladi ([tools/README.md](../tools/README.md)).

### Manba koddan (ishlab chiquvchilar uchun)

Kerak: Windows 10 x64, [uv](https://docs.astral.sh/uv/), taxminan 1 GB bo'sh joy.

1. Loyiha papkasini doimiy joyga qo'ying (masalan `C:\SRV_1`). Keyin
   ko'chirsangiz, yorliq va xizmatni qayta o'rnatish kerak bo'ladi.
2. Tashqi dasturlarni `tools\` ga qo'ying — ro'yxat va nazorat yig'indilari
   [tools/README.md](../tools/README.md) da. Majburiysi faqat `caddy.exe`
   (saytlar uchun); qolganlari kerakli plagin uchun.
3. Oddiy PowerShell oynasida, loyiha papkasidan:

   ```powershell
   powershell -ExecutionPolicy Bypass -File install\install.ps1
   ```

   Skript Python muhitini tayyorlaydi, `tools\` ni tekshiradi, ma'lumotlar
   papkasini (`C:\ProgramData\SRV_1`) yaratadi va Ish stoli hamda Bosh menyuga
   «SRV_1» yorlig'ini qo'yadi. Administrator huquqi kerak emas.

Ma'lumotlar papkasiga faqat siz, tizim va administratorlar kira oladi: unda
kirish tokeni, bazalar va loyihalaringiz turadi.

## 2. Yadroni ishga tushirish

**Odatiy yo'l — hech narsa qilmaysiz.** «SRV_1» oynasini ochasiz; server ishlamayotgan
bo'lsa, oyna uni o'zi (alohida oynasiz) ishga tushiradi va 5–30 soniyada ulanadi.
Yuqori o'ng tomonda holat va bitta tugma turadi:

| Tugma | Nima qiladi |
|-------|-------------|
| «Serverni to'xtatish» | tasdiq so'raydi va serverni vaqtincha o'chiradi: joylangan saytlar, IoT va rejalashtirilgan vazifalar ham to'xtaydi. Ma'lumotlarga tegilmaydi |
| «Serverni ishga tushirish» | to'xtatilgan serverni qayta yoqadi |

Oynani yopsangiz, server **ishlashda davom etadi** — to'xtatish uchun avval tugmani bosing.
Kompyuter o'chib yonsa yoki tizimdan chiqsangiz, server to'xtaydi; oynani ochganingizda
yana ko'tariladi. Kompyuter yonishi bilan oynasiz ham ishlashi kerak bo'lsa — pastdagi
Windows xizmati.

Server ishga tushmasa, sabab oynaning yuqorisidagi sariq satrda yoziladi
([Nosozliklar](#8-nosozliklar)).

**Qo'lda, nosozlikni aniqlash uchun** — PowerShell oynasida (o'rnatilgan nusxada: Bosh
menyudagi «SRV_1 yadro (konsol)»):

```powershell
uv run python -m srv1_core
```

Oyna ochiq turguncha yadro ishlaydi; `Ctrl+C` yoki oynani yopish uni
to'xtatadi (saytlar va boshqa jarayonlar ham birga to'xtaydi).

**Doimiy** — Windows xizmati sifatida (kompyuter yonishi bilan o'zi ishga
tushadi, yiqilsa 5 soniyadan keyin qayta ko'tariladi). PowerShell'ni
**«Administrator sifatida ishga tushirish»** bilan oching:

```powershell
powershell -ExecutionPolicy Bypass -File install\service.ps1 -Action install
```

Skript Windows parolingizni so'raydi: xizmat sizning nomingizdan ishlaydi,
shunda fayllaringiz, COM portlar va token shell bilan bir xil egada bo'ladi.
Parol hech qayerga yozilmaydi — uni Windows o'zi saqlaydi.

| Buyruq (`-Action`) | Nima qiladi |
|--------------------|-------------|
| `plan` | hech narsani o'zgartirmay, nima qilinishini ko'rsatadi |
| `status` | xizmat holati |
| `install`, `remove` | o'rnatish, olib tashlash (administrator) |
| `start`, `stop`, `restart` | boshqarish (administrator) |

Xizmat o'rnatilgan bo'lsa, oynadagi tugma xizmatni to'xtatadi va yoqadi — har safar
Windows administrator tasdig'ini (UAC) so'raydi. Xizmat ishlayotganda yadroni qo'lda
ikkinchi marta ishga tushirsangiz, u «manzil band» deb darhol chiqadi.
Xizmat jurnali: `C:\ProgramData\SRV_1\logs\service.log`.
Windows parolingizni almashtirsangiz, xizmatni `remove` va `install` qiling.

## 3. Shell oynasi

«SRV_1» yorlig'ini oching. Chap tomonda sahifalar:

| Sahifa | Nima ko'rsatadi |
|--------|-----------------|
| Tizim | protsessor, xotira, disklar — jonli |
| Plaginlar | plaginlar ro'yxati; yoqish va o'chirish |
| Jurnal | yadro va plaginlar hodisalari — jonli; tarmoq ushlanayotganda paketlar xulosasi va shubhali paketlar ham shu yerda |
| Xotira | har jarayon qancha RAM olayotgani va 350 MB chegarasi |
| plagin panellari | har yoqilgan plaginning o'z sahifasi |

Til (o'zbekcha, ruscha, inglizcha) yuqori o'ng burchakdan almashtiriladi.

Agar oyna **token so'rasa** — server ishlayapti, lekin uning token faylini o'qib
bo'lmadi: odatda server boshqa Windows hisobi nomidan yoki boshqa ma'lumotlar papkasi
bilan ishlayapti ([Nosozliklar](#8-nosozliklar)).

## 4. Plaginlar

Plaginlar sahifasida yoqiladi va o'chiriladi. «Og'ir» plaginlar (`data`)
standart holatda o'chiq: yoqilganda alohida jarayonda, RAM chegarasi bilan
ishlaydi; ish tugagach o'chirib qo'ying.

| Plagin | Nima uchun | Batafsil |
|--------|-----------|----------|
| `files` | papkalarni kuzatish, fayl qidirish, nusxalash/ko'chirish/o'chirish | [fayllar.md](fayllar.md) |
| `hosting` | statik sayt, Python va Node dasturlarini joylash | [hosting.md](hosting.md) |
| `iot` | MQTT, serial port, Modbus, telemetriyani saqlash | [iot.md](iot.md) |
| `data` | CSV/Parquet/Excel import, SQL so'rovlar, hisobot | [data.md](data.md) |
| `electronics` | serial monitor, ESP va Arduino'ga proshivka yozish | [elektronika.md](elektronika.md) |
| `itops` | jarayonlar, Windows xizmatlari, tarmoq skaneri, zaxira | [itops.md](itops.md) |
| `monitor` | CPU, RAM va disk tarixi, chegaradan oshsa ogohlantirish; tarmoq paketlarini ushlash va xavf belgilarini tekshirish | [monitor.md](monitor.md), [tarmoq-kuzatuvi.md](tarmoq-kuzatuvi.md) |

**Tarmoq kuzatuvi** («Kuzatuv» sahifasining pastida) uchun Npcap drayveri kerak
(<https://npcap.com/#download>; o'rnatuvchiga kirmaydi). «Interfeyslar» jadvalidan
qatorni tanlab, «Ushlashni boshlash» ni bosing. Paket matni standart holatda
saqlanmaydi. Faqat o'z tarmog'ingizda yoki ruxsat bilan ishlating.

Plagin faqat o'z manifestida (`plugins\<nom>\plugin.toml`) ruxsat etilgan
papka, port va COM portlarga tegadi. Masalan, `files` yangi papkani kuzatishi
yoki `electronics` yangi COM portga yozishi uchun uni manifestga qo'shing va
plaginni o'chirib-yoqing.

### Sayt joylash (eng ko'p kerak bo'ladigani)

1. Fayllarni `C:\ProgramData\SRV_1\projects\<nom>\` ga qo'ying.
2. «Hosting» sahifasida «Loyiha qo'shish»: nom, tur (`static`, `python`,
   `node`), dastur uchun buyruq (masalan `python app.py`).
3. Brauzerda `http://<nom>.localhost:8080/` ni oching.

Dastur bir muddat ishlatilmasa uxlatiladi (RAM bo'shaydi) va keyingi so'rovda
o'zi uyg'onadi.

### Saytni internetga ochish

«Hosting» sahifasida loyihani tanlab, **«Internetga ochish»** ni bosing va
tasdiqlang. Bir necha soniyadan keyin «Internetdagi manzil» ustunida
`https://<tasodifiy-so'zlar>.trycloudflare.com` ko'rinadi — uni istalgan
joydan ochish mumkin. Manzil chiqqandan keyin ishlab ketishi uchun bir
daqiqagacha kuting: shu orada brauzer «ulanib bo'lmadi» deyishi mumkin. Buning uchun `tools\cloudflared.exe` kerak; Cloudflare
akkaunti kerak emas.

Bilib qo'ying:

- manzilni bilgan **har kim** saytni ochadi — parol yo'q. Maxfiy narsani
  bunday ochmang;
- manzil har safar yangi; yadro qayta ishga tushsa, tunnel yopiladi;
- «Tunnelni yopish» yoki loyihani to'xtatish kirishni darhol uzadi;
- bir vaqtda ko'pi bilan 2 ta tunnel (har biri alohida jarayon va RAM);
- bu Cloudflare'ning bepul sinov xizmati: kafolati yo'q, doimiy sayt uchun emas.

## 5. Zaxira va tiklash

`itops` plagini har kuni 03:00 da ma'lumotlar papkasini zip arxivga oladi va
oxirgi 7 tasini saqlaydi; «Hozir zaxira olish» tugmasi ham bor. Arxivlar:
`C:\ProgramData\SRV_1\plugins\itops\data\backups\`.

- **Token arxivga kirmaydi** — arxivni boshqa joyga nusxalash xavfsiz.
- `projects\` va `logs\` standart holatda **kirmaydi** (katta bo'lishi mumkin).
  Loyihalaringizni ham zaxiralash uchun `backup_projects` ni yoqing
  ([itops.md](itops.md)).
- Arxivlar ma'lumotlar bilan **bir diskda** turadi: bu xato o'chirishdan
  saqlaydi, disk buzilishidan emas. Boshqa diskka yozishni sozlang yoki
  arxivlarni vaqti-vaqti bilan ko'chirib turing.

Tiklash:

1. Yadroni to'xtating (xizmat bo'lsa: `service.ps1 -Action stop`) va shell'ni yoping.
2. `C:\ProgramData\SRV_1` ni boshqa nomga o'zgartirib saqlab qo'ying.
3. Arxivni bo'sh `C:\ProgramData\SRV_1` ga oching:
   `Expand-Archive srv1-backup-....zip C:\ProgramData\SRV_1`.
4. Yadroni ishga tushiring. Yangi token yaratiladi; shell uni o'zi topadi.

## 6. Xavfsizlik haqida qisqacha

- Yadro faqat `127.0.0.1:8710` da tinglaydi va har so'rovda token talab qiladi.
  Token: `C:\ProgramData\SRV_1\auth.token`. Uni hech kimga bermang; shubha
  bo'lsa, faylni o'chirib yadroni qayta ishga tushiring — yangisi yaratiladi.
- Xavfli amallar (jarayon ishga tushirish va to'xtatish, proshivka, fayl
  o'chirish, tunnel ochish, xizmatlarni boshqarish) audit jurnaliga yoziladi
  (`srv1.db`, `audit_log` jadvali), rad etilganlari ham.
- Yadroni administrator sifatida ishga tushirmang — kerak bo'lmasa. Oddiy
  foydalanuvchi bilan hammasi ishlaydi, faqat `itops` Windows xizmatlarini
  boshqara olmaydi (ko'rsatadi, xolos).

## 7. Yangilash va olib tashlash

O'rnatuvchi bilan: yangi `SRV_1-Setup-<versiya>.exe` ni ustidan o'rnating. U ishlab turgan
serverni o'zi tartibli to'xtatadi (xizmat bo'lsa — to'xtatib, keyin qayta yoqadi);
ma'lumotlarga tegmaydi.

Manba koddan: yadroni to'xtating, loyiha papkasini yangilang, `install\install.ps1`
ni qayta yuguring (ma'lumotlarga tegmaydi), yadroni ishga tushiring.

Olib tashlash:

```powershell
powershell -ExecutionPolicy Bypass -File install\service.ps1 -Action remove   # administrator
powershell -ExecutionPolicy Bypass -File install\uninstall.ps1
```

`uninstall.ps1` yorliqlarni o'chiradi va qolgan papkalar yo'lini ko'rsatadi.
Ma'lumotlar papkasi o'chirilmaydi — uni o'zingiz, ishonchingiz komil bo'lganda
o'chirasiz.

## 8. Nosozliklar

| Belgi | Sabab va yechim |
|-------|-----------------|
| Shell token so'rayapti | Server boshqa hisob nomidan yoki boshqa papka bilan ishlayapti. `service.ps1 -Action status` ni ko'ring; `SRV1_DATA_DIR` o'zgaruvchisi yadro va shell uchun bir xil bo'lsin. Boshqa kompyuterdan `auth.token` ko'chirish **yordam bermaydi**: token har kompyuterda o'ziniki. |
| «Server ishga tushmadi», sariq satrda «manzil band» | 8710-portni boshqa dastur egallagan. Uni yoping yoki `config.toml` va `%APPDATA%\SRV_1\shell.json` da portni bir xil qilib o'zgartiring. |
| «Server ishga tushmadi», «javob bermadi» | Sariq satrdagi papkada `core-launch.log` va `srv1.log` ning oxirini o'qing. Ko'p uchraydi: `config.toml` da xato; `config.toml` va `shell.json` da port har xil. |
| «Server to'xtatilgan» | Server tugma bilan to'xtatilgan yoki o'zi to'xtagan. «Serverni ishga tushirish» ni bosing; xizmat bo'lsa `logs\service.log` ning oxirini o'qing. |
| Tugma bosilganda Windows tasdiq so'raydi | Server Windows xizmati sifatida o'rnatilgan: uni to'xtatish va yoqish administrator huquqini talab qiladi. |
| Xizmat ishga tushib, darhol to'xtaydi | Odatda `config.toml` yoki plagin sozlamasida xato; sabab `logs\service.log` da. Sozlama xatosida xizmat ataylab qayta urinmaydi. |
| «Hosting» da `Caddy: missing` | `tools\caddy.exe` yo'q. |
| Sayt ochilmaydi, 8080 band | Boshqa dastur 8080 ni egallagan. `hosting.json` da `listen_port` ni va manifestdagi `ports` ni o'zgartiring. |
| Loyiha `failed` | «Loyiha jurnali» ga nomini yozib, xatoni o'qing. Ko'p uchraydi: dastur `PORT` o'zgaruvchisidagi portda tinglamaydi; buyruq `.cmd`/`.bat` (masalan `npm start`) — `node server.js` deb yozing. |
| «Internetga ochish» 30 soniyadan keyin xato beradi | Tarmoq Cloudflare'ga chiqishni to'smoqda yoki internet yo'q. Xato matnida cloudflared'ning oxirgi satrlari bor. |
| `itops`: «administrator huquqi kerak» | Windows xizmatlarini boshqarish uchun yadro administrator nomidan ishlashi kerak. Ko'rish har doim ishlaydi. |
| Proshivka: «port band» | Portni boshqa dastur (Arduino IDE, serial monitor) ochgan — uni yoping. |
| Xotira sahifasida chegara oshgan | Ishlatmayotgan plaginlarni o'chiring (`data` — birinchi navbatda), keraksiz loyiha va tunnellarni to'xtating. |

Nima haqiqiy uskunada sinalgan, nima sinalmagani — [bosqichlar.md](bosqichlar.md)
oxiridagi «Sinalmaganlar» bo'limida ochiq yozilgan.
