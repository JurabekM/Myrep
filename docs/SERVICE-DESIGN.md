# TAMGA daemon'ini alohida hisobga ko'chirish — dizayn (taklif)

Holat: **taklif, qaror kutilmoqda.** Audit (K1/H-3) qoldig'ini arxitektura darajasida yopish uchun.

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
