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
(685 MB, o'chirsa bo'ladi).

| Qadam | Nima qiladi |
|-------|-------------|
| testlar | `uv run pytest`; o'tmasa o'rnatuvchi yig'ilmaydi (`-SkipTests` — o'tkazib yuborish) |
| Python | `uv` boshqaradigan Python 3.12 nusxalanadi (testlar, IDLE, tkinter/Tcl, pip'siz) |
| bog'liqliklar | `uv export --frozen --no-dev` → `uv pip install --require-hashes` (aynan `uv.lock` dagi versiyalar, xesh bilan) |
| SRV_1 | `git ls-files` bo'yicha: `core`, `sdk`, `shell`, `plugins`, `install`, qo'llanma |
| tashqi dastur | `tools\caddy.exe`, `tools\nssm.exe` (NSSM xeshi tekshiriladi) |
| sinash | to'plamdagi Python bilan asosiy modullar import qilinadi, versiya solishtiriladi |
| `.pyc` | hammasi oldindan kompilyatsiya qilinadi (`unchecked-hash`) — `Program Files` yozishga yopiq |
| Inno Setup | `packaging\srv1.iss` → `release\` |

Versiya `pyproject.toml` dan olinadi; u `srv1_core`, `srv1_sdk`, `srv1_shell` dagi
`__version__` bilan bir xil bo'lishi shart (test bor).

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
  ixtiyoriy Ish stoli yorlig'i.
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

- O'rnatuvchi **imzolanmagan** — Windows «Noma'lum nashriyotchi» deb ogohlantiradi.
- **PyQt6 GPL v3** da: o'rnatuvchini boshqalarga tarqatganda GPL shartlari amal qiladi
  (`licenses\THIRD-PARTY.md`).
- Hajm kattaligi: Qt'ning ishlatilmaydigan qismlari (Quick/QML, ~60 MB) ataylab
  olib tashlanmagan — nimadir sinib qolishi xavfi tejalgan joydan qimmat.
- Administrator boshqa hisob bo'lsa (UAC'da boshqa foydalanuvchi kiritilsa), xizmat
  o'sha hisob nomidan o'rnatiladi; kerakli hisobni `service.ps1 -Account` bilan bering.
- cloudflared, Mosquitto, avrdude o'rnatuvchiga kirmaydi.
