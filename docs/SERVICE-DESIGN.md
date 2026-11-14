# TAMGA daemon'ini alohida hisobga ko'chirish — dizayn

Holat: **amalga oshirildi (S1–S5), administrator sinovi kutilmoqda** — [SERVICE-TEST.md](SERVICE-TEST.md).
Audit (K1/H-3) qoldig'ini arxitektura darajasida yopish uchun.

**Qabul qilingan qarorlar (2026-10-19):**
- Ikki rejim: oddiy (admin'siz) qoladi, himoyalangan rejim qo'shiladi. Ikkalasi **alohida o'rnatuvchi**
  (`TAMGA Studio` va `TAMGA Studio Protected`): NSIS `both` rejimi administrator foydalanuvchidan
  oddiy o'rnatishda ham UAC so'raydi, bu admin'siz xususiyatni buzardi.
- `ask` va boshqa boshqaruv amallari himoyalangan rejimda har safar UAC orqali (Studio `tamga.exe` ni
  administrator sifatida ishga tushiradi).
- Bir mashinada bir nechta foydalanuvchi: bitta mashina jurnali, har yozuvda `actor.user` = mijoz SID'i.
- Kalitlar xizmat kontekstida: DPAPI (mashina doirasi) + papka ACL'i (foydalanuvchiga yopiq).
- Himoyalangan rejimda spool yo'q va hook har doim fail-closed.
- Mavjud oddiy rejim jurnalini ko'chirish hali avtomatlashtirilmagan (§5 — keyingi bosqich).

## 1. Muammo

Hozir `tamgad` agent bilan **bir xil Windows foydalanuvchisi** huquqida ishlaydi. Shu sababli
operatsion tizim ular orasida chegara qo'ymaydi: shu foydalanuvchi nomidagi jarayon daemon
jarayonini to'xtata oladi, uning fayllari (jurnal, config, spool) va kalitlariga (Credential Manager)
kira oladi. K1/H-3 tuzatishlari to'siqni ko'taradi va har urinishni jurnalga yozadi, lekin bu
mutlaq chegara emas — buni audit ham, muallif ham qayd etgan.

## 2. Maqsadlar

| # | Maqsad |
|---|---|
| G1 | Daemon jarayoni, uning jurnali, kalitlari va sozlamalari foydalanuvchi huquqi bilan o'zgartirib bo'lmaydigan joyda |
| G2 | Hook va proxy hamon oddiy foydalanuvchi sifatida daemon'ga ulana oladi (hodisa yuboradi) |
| G3 | Inson qarori (`decide`), kalit almashtirish, to'xtatish — agent soxtalashtira olmaydigan yo'l bilan |
| G4 | Hook kechikishi o'zgarmaydi (p99 < 20 ms) |
| G5 | Mavjud jurnallar va kalitlar yo'qolmasdan ko'chiriladi; format (TAMGA Record) o'zgarmaydi |

## 3. Variantlar

| | A. Windows xizmati (virtual hisob) | B. Alohida mahalliy foydalanuvchi | C. Hozirgi model + mustahkamlash |
|---|---|---|---|
| Daemon kimning huquqida | `NT SERVICE\tamgad` (virtual service account) | yangi `tamga-svc` foydalanuvchisi | joriy foydalanuvchi |
| O'rnatish | **administrator kerak** (bir marta) | administrator kerak + parol boshqaruvi | admin'siz |
| G1 | ✅ fayllar ACL bilan himoyalangan, jarayonni oddiy foydalanuvchi to'xtata olmaydi | ✅ | ❌ |
| Kalitlar | xizmat hisobining DPAPI / mashina darajasidagi himoya | foydalanuvchi DPAPI'si | joriy foydalanuvchi |
| Boshqaruv qulayligi | xizmat menejeri (avto-start, qayta ishga tushish) | Task Scheduler — mo'rtroq | hozirgidek |
| Parol saqlash | kerak emas | kerak (xavf manbai) | — |

**Tavsiya: A — virtual hisobli Windows xizmati.** B dan farqli ravishda parol yo'q; C esa maqsadni bajarmaydi.

## 4. Tavsiya etilgan dizayn (A)

**Jarayon va ma'lumotlar**
- `tamgad` xizmat rejimini oladi (Windows Service Control Manager bilan ishlash), `NT SERVICE\tamgad`
  hisobida avto-start.
- Ma'lumotlar `%ProgramData%\TAMGA\` ga ko'chadi. ACL: to'liq huquq faqat xizmat hisobi va
  Administratorlarda; oddiy foydalanuvchida **faqat o'qish** (jurnal va ochiq kalitni ko'rish, eksport,
  mustaqil tekshirish uchun).
- Imzo va vault kalitlari xizmat hisobi kontekstida saqlanadi — foydalanuvchi ularni o'qiy olmaydi.

**Pipe**
- Nomi foydalanuvchiga emas, mashinaga bog'langan; DACL: interaktiv foydalanuvchilarga **ulanish**
  (hodisa yuborish) ruxsati, xizmat hisobiga to'liq huquq.
- Daemon har ulanishda mijozning foydalanuvchi SID'ini oladi va yozuvga `actor` sifatida yozadi
  (bir mashinada bir nechta foydalanuvchi bo'lsa ham to'g'ri).

**Boshqaruv buyruqlari (G3)**
- `decide`, `rotate`, `shutdown`, config o'zgarishi faqat **ma'muriy kanal** orqali: administrator
  huquqida ishlayotgan (UAC tasdiqlangan) `tamga.exe` yoki Studio'ning ma'muriy rejimi.
  UAC so'rovi xavfsiz ish stolida ko'rsatiladi — agent uni foydalanuvchi o'rniga tasdiqlay olmaydi.
- Murosa: har bir `ask` ni tasdiqlash uchun UAC oynasi noqulay bo'lishi mumkin. Variant: `ask`
  qarori uchun alohida, ma'muriy bo'lmagan, lekin xizmat tomonidan yaratilgan bir martalik oyna
  (xizmat o'zi ko'rsatadigan tasdiqlash dialogi). Bu ochiq dizayn savoli (§7).

**Soxta serverdan himoya (pipe squatting).** Xizmat to'xtagan paytda oddiy foydalanuvchi ham pipe
nomini egallashi mumkin (`AU` da `FILE_CREATE_PIPE_INSTANCE` yo'q, lekin nom bo'sh bo'lsa birinchi
nusxani istalgan jarayon yaratadi). Shuning uchun mijoz (hook, CLI, Studio) ulanishdan keyin tekshiradi:
1. pipe serveri PID'i == SCM bo'yicha ishlab turgan `tamgad` xizmatining PID'i (`QueryServiceStatusEx`);
2. server exe yo'li == `install_dir\tamgad.exe`.
Faqat exe yo'li yetarli emas: o'rnatish papkasidagi `tamgad.exe` ni foydalanuvchi o'zi ham ishga tushira
oladi. Ikkinchi qatlam: himoyalangan rejim belgisi bor mashinada `tamgad.exe` xizmatdan tashqari ishga
tushmaydi. `%ProgramData%` muhit o'zgaruvchisidan emas, `SHGetKnownFolderPath` dan olinadi — aks holda
mijoz jarayoni o'zgaruvchini almashtirib, belgini "ko'rmay", oddiy rejimga (o'z daemon'iga) o'tib ketardi.
Pipe orqali SID aniqlanmasa (anonim impersonatsiya darajasi), `actor.user` = `unidentified`.

**O'rnatuvchi va `%ProgramData%`.** Oddiy foydalanuvchi `%ProgramData%` da papka yarata oladi, o'rnatuvchi
esa administrator huquqida ishlaydi — oldindan tayyorlangan papkaga (junction, begona fayllar) ishonib
rekursiv ACL qo'yish tizim fayllariga tegishi yoki begona faylni «himoyalangan» deb qabul qilishi mumkin.
`studio/src-tauri/service-acl.ps1`: mavjud papka faqat ishonchli bo'lsa saqlanadi (egasi administratorlar/
SYSTEM, reparse point yo'q, boshqalarda yozish huquqi yo'q), aks holda `TAMGA.untrusted-<vaqt>` ga olinadi;
yangi papka himoyalangan DACL bilan **bir vaqtda** yaratiladi; amallar reparse point ortidan yurmaydi;
oxirida butun daraxt qayta tekshiriladi. Biror muhim qadam yiqilsa xizmat `disabled` qilinadi va
o'rnatuvchi xato bilan tugaydi (exit 2) — himoya jim yo'qolmaydi.

**Hook va proxy** o'zgarmaydi (oddiy foydalanuvchi, pipe orqali). Daemon ishlamasa — hozirgi
`dev`/`strict` siyosati.

## 5. Ko'chirish (G5)

1. Yangi o'rnatuvchi (per-machine, admin) xizmatni o'rnatadi.
2. Birinchi ishga tushishda mavjud `%LOCALAPPDATA%\tamga` dan jurnal, checkpoint'lar va ochiq
   kalit `%ProgramData%\TAMGA` ga ko'chiriladi; imzo kaliti `tamga key backup/restore` mexanizmi
   orqali xizmat kontekstiga o'tkaziladi, so'ng `key rotate --reason restore` tavsiya etiladi.
3. Zanjir uzilmaydi: ko'chirish oldidan va keyin `tamga verify` bir xil natija berishi kerak.

## 6. Sinov rejasi

| Sinov | Admin kerakmi |
|---|---|
| Xizmat rejimi mantig'i, pipe DACL qurish, SID olish — birlik testlari | yo'q |
| Xizmatni o'rnatish, avto-start, qayta ishga tushish | **ha — foydalanuvchi bajaradi** |
| Oddiy foydalanuvchi jarayoni daemon'ni to'xtata olmasligi, fayllarni o'zgartira olmasligi | ha (o'rnatilgan xizmat kerak) |
| Ko'chirish: eski jurnal → yangi joy, `tamga verify` mos | ha |
| Hook kechikishi (G4) | ha |

Muallif (AI) bu mashinada administrator huquqi talab qiladigan amallarni bajarmaydi: kod va birlik
testlari tayyorlanadi, o'rnatish va jonli sinov foydalanuvchi tomonidan bajariladi.

## 7. Ochiq savollar (foydalanuvchi qarori)

1. **Admin'siz o'rnatish xususiyatidan voz kechish** — qabul qilinadimi? Variant: ikki rejim
   (oddiy per-user va «himoyalangan» per-machine).
2. **`ask` tasdiqlash yo'li:** har safar UAC, yoki xizmat ko'rsatadigan alohida dialog?
3. Bir mashinada bir nechta foydalanuvchi — har biriga alohida jurnalmi yoki umumiymi?
