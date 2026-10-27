# Desktop E2E (haqiqiy ilova)

`tauri-driver` → platforma WebDriver'i (Linux: `WebKitWebDriver`, Windows: `msedgedriver`) →
`baraka-desktop`. Testlar ekranni foydalanuvchi kabi boshqaradi: ko'rinadigan o'zbekcha matnlar
va yorliqlar bo'yicha. Har bir ko'rilgan ekran haqiqiy webview'da **axe-core** bilan tekshiriladi
(WCAG 2.2 A/AA, rang kontrasti ham).

| Spec | Nima |
|---|---|
| `01-onboarding` | 5 qadamli onboarding, tiklash kodi, «qarzim bor» → qarzlar ekrani, eslatmalar, til va shrift qayta ochilganda saqlanishi |
| `02-bekzod` | Bekzod ssenariysi (mavjud funksiyalar bilan): daromad → ulush → xarajat → audit → qarz → 70/20/10 → «Qarzsiz kun» → qarz yopilishi → Sherzod bilan musharaka → kassa daftari → davr taqsimoti → vazifa hodisasi → oylik ko'rik → zaxira nusxa |
| `03-restore` | Zaxira nusxa → yangi profil → «Mavjud xonadonga qo'shilish» → ma'lumotlar 1:1 |
| `04-kasbkor` | Kasb-kor «ikki cho'ntak»: boshlang'ich qoldiq → maosh → tushum (`Ctrl+N`) → chiqim → «egasi oldi» (pul oqimi kamaymaydi) → maosh Uy'ga → ulush → Uy'da daromad |
| `05-kasbkor-profit` | Kasb-kor haqiqiy foyda (SPEC 3.1 Feruza): tushum va chiqimlar → o'z mehnati → qizining 80 soati → tikuv mashinalari 12 mln / 60 oy → **3 100 000**; Jasur buyurtmasi tannarxdan past; uskuna sotildi → bir martalik xarajat |
| `06-kasbkor-close` | Kasb-kor «Hisob kuni» (SPEC 4.5 Feruza): joriy oyda yozuvlar → ilova keyingi oyga siljitilib qayta ochiladi → eslatma → soliq 4 % tushumdan → qolgan **2 580 000** → 774 000 / 1 290 000 / 516 000 → oy yopiladi, bayonnoma PDF |
| `07-kasbkor-ledger` | Kasb-kor kassa va nasiya: Bahodir (kutilgan 1 500 000, sanalgan 1 450 000 → −50 000, kunni yopish) → Malika (660 000 = 3 × 220 000, birinchi to'lov) → [+2 oy 20 kun] 20 kun kechikkan, summa o'zgarmagan, haftalik ko'rik |
| `08-kasbkor-stock` | Kasb-kor tovarlar: Bahodir shakari (50 kg ilovagacha + 100 kg kartadan, 80 kg sotuv → o'rtacha tannarx 960 000, qoldiq 840 000) → joriy narx 13 500: farq 105 000, 13 000 ga sotish ogohlantirishi → sanoq 69,5 kg: 6 000 yo'qotish → [+91 kun] muzlagan tovar |
| `09-kasbkor-staff` | Kasb-kor xodim va ta'minotchi: Sardor (kelishuv, imzo, 1 000 000 avans 2 oyda, kelishuv PDF) → Ulgurji baza (shakar 12 500 dan, 100 kg nasiyaga qoldiqqa, 500 000 to'lov, bosh sahifada qarz) → [+35 kun] qarz kechikdi (jarimasiz), haq to'landi, varaqcha PDF |
| `10-kasbkor-growth` | Kasb-kor o'sish: 120 mln tushum, 2 mln chiqim → darvoza yopiq (zaxira, «Hisob kuni», reja — keyingi qadamlar) → zakot: oltin 1 100 000 × 85 g, hawl tasdig'i → 2 950 000, hisob saqlandi → tarozi tekshirildi, shakar sanaldi (9,5 kg) → [+35 kun] bosh sahifada tarozi eslatmasi |
| `11-kasbkor-roles` | Ikki ilova: egasi (Shakar 10 kg, sotuv narxi 15 000) «Sotuvchi» rolida ulash fayli → sotuvchi qo'shiladi: menyuda faqat sotuv, nasiya to'lovi, smena, foyda yo'q; 2 kg shakar (30 000) va 50 000 karta; smena 100 000 + 30 000 = 130 000, egasiga 100 000 → fayl egasiga: shakar 8 kg, «Sotuvchi smenalari», qurilma «Sotuvchi» |
| `12-musofir` | Onboarding'da Musofir → sozlash (KRW, ulush 20 %, maqsad 120 mln so'm, qaytish 13 oydan keyin) → o'tgan 3 oy (maosh 2 600 000 von, jamg'armaga 520/500/540 ming, qolgani uyga) → shu oy: maosh (`Ctrl+N`) va ulush taklifi, 3 xarajat, uyga 1 200 000 + 5 000 komissiya → kurssiz so'mdagi qiymat yo'q → kurs 9,1: 54,6 mln, qaytishda 3 884 000 kam → ulush qo'yildi: qo'lda 215 000, maqsadga yetadi |
| `13-musofir-two-shores` | Ikki ilova: musofir (xonadon egasi) shartlar 50/30/20, Mohira qabul qiladi → uyga 1 200 000 von (uyda 10 900 000) → «Uydagi oila qurilmasi» ulash → oila: Musofir makoni ko'rinmaydi, yo'ldagi pul qabul qilinadi (summa taklifdan), uy xarajati 5 450 000 dan 2 000 000 sarflanadi, Mohira kelishuvni PIN bilan tasdiqlaydi → fayl musofirga: qoldiq 3 450 000, Mohira ✓ |
| `14-musofir-return` | Bobur aka: Uy makonida tog'asidan yo'l qarzi 15 000 000 → Musofir: shartlar 50/30/20, uyga 1 200 000 von (uyda 10 900 000) → «Ikki qirg'oq»: qabul, «Qarz to'lovi» maqsadidan tog'aga 3 270 000 (qarz maqsadi 0) → yo'l qarzi belgilanadi: qolgan 11 730 000, 6 oyda yopish uchun oyiga 1 955 000 → «Qaytdim» (9 kun oldin, 120 mln): 81 kun qoldi → tog'a 15 mln qarz so'raydi: sariq, 12,5 %, kutish sanasi → «Kutaman» jurnalda |
| `15-musofir-reserve` | Bobur aka: KRW, maqsad 120 mln → o'tgan 2 oy maosh va 800 000 von xarajat (zaxira pul maqsadi 800 000) → boshlang'ich 500 000 → maosh: ulush 520 000 = 300 000 zaxira pulga + 220 000 jamg'armaga (ikki qadamli taklif), zaxira pul to'la → kasalxona uchun 200 000 (ulush kamaymaydi) → «Hunardan ishga»da «Tikuv sexi» 30 mln → ish boshlash summasi: yashash uchun 90 mln (25 %) → qarz so'rovi rad etildi, natija «qilmadim» |
| `16-musofir-story` | Qaytish xavfsizligi: Uyda oyiga 8 000 000 xarajat → 35 kundan keyin Bobur 18 000 USD bilan qaytdi (1 USD = 12 650): ≈ 227 700 000 so'm, 87 kun qoldi, qal'a devori 48 000 000, erkin pul 179 700 000 → «Oltin foyda»ga 126,5 mln, oyiga 35 % kafolat: qizil, besh belgidan 4 tasi, «5,2 barobar» → «Rad etaman» → Uy «Taklifni tekshirish»: 9 savol, 2 belgi — qizil |
| `17-learning` | «O'zimga sarmoya»: daromad 12 000 000 → «Bir soatim qancha?» qo'lda 10 296 000, kuniga 11 soat, 26 kun: 36 000, ikki barobar 72 000, soat chegarasi eslatmasi → 2 bilim rejasi, 3-si — faol rejalar chegarasi → 1 soat 30 daqiqa o'qish → «O'zimga sarmoya» xarajati 1 200 000 rejaga: kartada sarflangan, daromadning 10 % (ekranda va auditda) → kurs tekshiruvi: daromad kafolati — qizil → «Ilm zakoti» → natija: yangi hisobsiz xabar, 12 870 000 bilan 45 000 — farq 9 000 (25 %) |

## Ishga tushirish (Linux)
```bash
sudo apt-get install webkitgtk-webdriver xvfb   # Ubuntu 24.04 va eskisida: webkit2gtk-driver
cargo install tauri-driver --locked
pnpm --dir ../ui build
(cd ../src-tauri && cargo build --features tauri/custom-protocol)   # debug build
pnpm install
xvfb-run -a -s "-screen 0 1440x900x24" pnpm e2e
```
Skrinshotlar — `.out/`. Har bir ishga tushirish vaqtinchalik toza profil bilan.

Faqat **debug** build'da ishlaydigan yordamchilar (release'da kompilyatsiyaga kirmaydi):
- `BARAKA_DEV_SHIFT_DAYS=N` — yadro soatini N kunga siljitadi (davrlar, eslatmalar);
- `BARAKA_E2E_FILES=<papka>` — «Saqlash» / «Ochish» tizim oynalari o'rniga shu papka
  (WebDriver tizim oynalarini boshqara olmaydi);
- `BARAKA_INSECURE_DEV_SECRET=1` — keyring'siz platforma siri.

## Windows
`msedgedriver` (WebView2 versiyasiga mos) `PATH` da bo'lishi kerak; `tauri-driver
--native-driver <msedgedriver.exe>`. `BARAKA_APP` — boshqa binar yo'li.

## Sovuq start
Release build bilan (`cargo build --release --features tauri/custom-protocol`): jarayon
ishga tushirilgandan UI'ning birinchi yadro chaqiruvigacha (sahifa yuklangan, React ishga tushgan;
qulf yoki sozlash ekrani shu javobdan keyin chiziladi). Ilova `BARAKA_STARTUP_TRACE=1` bo'lsa
`startup_ms=N` ni stderr'ga yozadi (faqat raqam). `node scripts/cold-start.mjs [binar] [marta]` —
har safar o'lchab, birinchisi va medianani chiqaradi.

U15 natijasi (Linux, Xvfb, dasturiy render): mediana 934 ms, oraliq 897–1007 ms.
