# Desktop E2E (haqiqiy ilova)

`tauri-driver` → platforma WebDriver'i (Linux: `WebKitWebDriver`, Windows: `msedgedriver`) →
`baraka-desktop`. Testlar ekranni foydalanuvchi kabi boshqaradi: ko'rinadigan o'zbekcha matnlar
va yorliqlar bo'yicha. Har bir ko'rilgan ekran haqiqiy webview'da **axe-core** bilan tekshiriladi
(WCAG 2.2 A/AA, rang kontrasti ham).

| Spec | Nima |
|---|---|
| `01-onboarding` | 5 qadamli onboarding, tiklash kodi, «qarzim bor» → qarzlar ekrani, eslatmalar, til va shrift qayta ochilganda saqlanishi |
| `02-anvar` | Anvar ssenariysi (mavjud funksiyalar bilan): daromad → ulush → xarajat → audit → qarz → 70/20/10 → «Qarzsiz kun» → qarz yopilishi → Dilshod bilan musharaka → kassa daftari → davr taqsimoti → vazifa hodisasi → oylik ko'rik → zaxira nusxa |
| `03-restore` | Zaxira nusxa → yangi profil → «Mavjud xonadonga qo'shilish» → ma'lumotlar 1:1 |
| `04-kasbkor` | Kasb-kor «ikki cho'ntak»: boshlang'ich qoldiq → maosh → tushum (`Ctrl+N`) → chiqim → «egasi oldi» (pul oqimi kamaymaydi) → maosh Uy'ga → ulush → Uy'da daromad |
| `05-kasbkor-profit` | Kasb-kor haqiqiy foyda (SPEC 3.1 Nilufar): tushum va chiqimlar → o'z mehnati → qizining 80 soati → tikuv mashinalari 12 mln / 60 oy → **3 100 000**; Jasur buyurtmasi tannarxdan past; uskuna sotildi → bir martalik xarajat |
| `06-kasbkor-close` | Kasb-kor «Hisob kuni» (SPEC 4.5 Nilufar): joriy oyda yozuvlar → ilova keyingi oyga siljitilib qayta ochiladi → eslatma → soliq 4 % tushumdan → qolgan **2 580 000** → 774 000 / 1 290 000 / 516 000 → oy yopiladi, bayonnoma PDF |
| `07-kasbkor-ledger` | Kasb-kor kassa va nasiya: Bahodir (kutilgan 1 500 000, sanalgan 1 450 000 → −50 000, kunni yopish) → Malika (660 000 = 3 × 220 000, birinchi to'lov) → [+2 oy 20 kun] 20 kun kechikkan, summa o'zgarmagan, haftalik ko'rik |
| `08-kasbkor-stock` | Kasb-kor tovarlar: Bahodir shakari (50 kg ilovagacha + 100 kg kartadan, 80 kg sotuv → o'rtacha tannarx 960 000, qoldiq 840 000) → joriy narx 13 500: farq 105 000, 13 000 ga sotish ogohlantirishi → sanoq 69,5 kg: 6 000 yo'qotish → [+91 kun] muzlagan tovar |
| `09-kasbkor-staff` | Kasb-kor xodim va ta'minotchi: Sardor (kelishuv, imzo, 1 000 000 avans 2 oyda, kelishuv PDF) → Ulgurji baza (shakar 12 500 dan, 100 kg nasiyaga qoldiqqa, 500 000 to'lov, bosh sahifada qarz) → [+35 kun] qarz kechikdi (jarimasiz), haq to'landi, varaqcha PDF |

## Ishga tushirish (Linux)
```bash
sudo apt-get install webkit2gtk-driver xvfb
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
