# AETHER-Q Zarbxona v3

Raqamli pul (CBDC kupyuralari) zarbxonasi — `docs/SPEC.md` bo'yicha to'liq implementatsiya.
Python 3.12+, PySide6 dark UI, `cryptography>=47` (ML-DSA-65, ChaCha20-Poly1305), `paho-mqtt`.

**Asosiy xususiyat:** pul **sekin, protsessorni kam band qilib, jonli monitor ostida** zarb
qilinadi (§14). Katta buyurtma kichik partiyalarga bo'linadi. Dastur uzilib qolsa, buyurtma
keyingi kupyuradan **davom etadi** (§15).

## O'rnatish va ishga tushirish

```bash
python -m pip install -r requirements.txt
```

| Buyruq | Nima qiladi |
|---|---|
| `run.bat` (Windows) / `./run.sh` | paketlari o'rnatilgan Python'ni o'zi topadi. `aetherq_core` bor muhit afzal |
| `python run.py` · `python -m app.main` · `python app/main.py` | uchalasi bir xil ishlaydi |
| `--papka D:\zarbxona_data` | profil papkasi (default: dastur yonidagi `data/`) |
| `--selftest` | Qt'siz o'z-o'zini sinash. Natija konsolga va `selftest_natija.txt` ga yoziladi |
| `--version` | versiya |

`run.bat` Python'ni tanlashda `py.exe` ga ishonmaydi: `.venv`, `py -0p` ro'yxati va
`where python` dagi har bir interpreterni alohida sinaydi. Majburan tanlash uchun
`set ZARBXONA_PYTHON=C:\...\python.exe` bering.

### Birinchi qadam — KAT

```bash
python tools/kat_tekshir.py kat/zarbxona_kat_v1.json      # → NATIJA: HAMMASI MOS
python -m pytest tests/test_kat.py -v                     # v3 yadrosi o'sha KAT bilan
```

## Ish tartibi

1. **Birinchi ochilish:** kalit yaratiladi (parol ikki marta, kamida 8 belgi). Keyingi
   safar kalit izi ko'rsatiladi va parol so'raladi.
2. **Kalit va sertifikat** sahifasi → «Ochiq kalitni eksport qilish». Faylni bankka
   bering, izni bank operatori bilan ko'z bilan solishtiring.
3. Bank bergan `.aqcert` → «Sertifikatni import qilish». Bank kaliti sertifikatdan
   olinadi va onlayn ulanishda aynan shu kalit pinlanadi.
4. **Zarb** sahifasida quyidagilarni kiriting:
   - summa;
   - zaxira qulfi;
   - ixtiyoriy cheklov (toifalar, muddat, soliq);
   - partiya hajmi;
   - **konveyer sur'ati** (tezlik, davomiylik yoki cheklovsiz; CPU byudjeti; sovutish).

   Keyin **ZARB** ni bosing. Jarayonni **PAUZA / DAVOM / TO'XTATISH** bilan boshqarasiz.
5. Konveyer monitorida har kupyura, sovutish tanaffuslari va partiya yopilishi ko'rinadi.
   Holat satrida haqiqiy tezlik, haqiqiy CPU ulushi va qolgan vaqt chiqadi.
6. **Partiyalar** sahifasida topshirishning ikki yo'li bor:
   - fayl orqali: eksport qilasiz, keyin «Topshirildi deb belgilash» ni bosasiz;
   - onlayn: MQTT orqali, avto-topshirish bilan. Buning uchun `aetherq_core` kerak.
7. **Tekshiruv** sahifasida butun jurnalni tekshirish va «buzib ko'rish» demosi bor.

Dastur uzilsa, qayta ochilganda quyidagilar bajariladi (§15.5):
- `*.yarim` fayllar o'chiriladi;
- jurnalda yo'q toza partiya jurnalga qabul qilinadi, buzilgani `karantin/` ga
  ko'chiriladi;
- tugallanmagan buyurtma «Buyurtmalar» sahifasida davom ettirishga taklif qilinadi.

## Arxitektura

```
core/          Qt'siz; hamma mantiq shu yerda va shu yerda sinaladi
  ibtido.py      §2  sha3, AQ-KMAC256 (⚠ standart emas), HKDF, AEAD, ML-DSA, lp/tagged_hash, iz
  konstanta.py   §3   kupyura.py §4   merkle.py §5   partiya.py §6+§10   cheklov.py §7
  sertifikat.py  §8   ombor.py §9     tekshiruv.py §12   buzish.py §12 (demo)
  surat.py       §14 Surat, Ritm (pauza bilan)
  buyurtma.py    §15 buyurtma, tiklash, yagona yozuvchi   jurnal.py §15.3
  protokol.py    §13.4–13.6 xabarlar, mavzular, wire AQW1
  kanal.py       §13.2 MQTT + xotira kanali    sessiya.py §13.3 adapter
  topshirish.py  §13.5 + §15.7 avto-topshirish
app/           PySide6: main.py, theme.py, ishchilar.py (QThread), kirish.py, oyna.py,
               sahifalar/ (har sahifa alohida fayl), selftest.py, assets/zarbxona.ico
tests/         pytest (T1–T15) + soxta_bank.py
tools/         kat_tekshir.py, kat_yarat.py, broker_smoke.py, ikonka_yarat.py
kat/  docs/    KAT vektorlari va to'liq SPEC
```

## Testlar (§18.1 — bulutda bajarilgan)

```bash
python -m pytest -q                      # GUI testi uchun: QT_QPA_PLATFORM=offscreen
```

| # | Fayl | Nima |
|---|---|---|
| T1 | `test_kat.py` | KAT: ibtidolar, ML-DSA, kalit ombori, cheklov, sertifikat, 4 partiya (har kupyura id, nazorat, konvert, sarlavha, barg, yadro, muhr, isbot), bank_id, mint_auth, wire |
| T2 | `test_kat.py` | standart KMAC256 (pycryptodome) KAT bilan **mos kelmasligi** qulflangan |
| T3, T4, T6, T8–T10 | `test_zarb.py` | to'liq sikl; 8 xil buzish aniq qoida bilan topiladi; sekin == tez; uzilish → davom; tiklash; yagona yozuvchi |
| T5, T7 | `test_surat.py` | ritm soxta soat bilan (tezlik, byudjet, kattasi, qisqa uyqu, sovutish, **portlash yo'q**, bekor qilish, pauza); haqiqiy vaqt |
| T11–T13 | `test_protokol.py` | `SoxtaFabrika` + §11 qoidalarini takrorlaydigan soxta bank; wire; avto-topshirish |
| T14 | `test_kirish_nuqta.py` | uchala kirish nuqtasi va `--selftest` subprocess bilan |
| T15 | `test_gui.py` | offscreen: har sahifa, har tugma, haqiqiy zarb, PAUZA/DAVOM/TO'XTATISH, buzish demosi |

## §18.2 — foydalanuvchi mashinasida qabul sinovlari

Bular bulutda **bajarilmagan va bajarib bo'lmaydi**. Aniq buyruqlar:

**A1 — Rust `aetherq_mint` bilan bayt-ma-bayt**
```bat
set ZARBXONA_AQ_YOL=C:\...\aetherq_bank
python -m pytest tests\test_moslik.py -v
```
AETHER-Q topilmasa, test `skip` bo'ladi. `mint_batch` chaqiruvi `tools/kat_yarat.py` dan
olingan. Imzosi farq qilsa, testni moslang.

**A2 — haqiqiy `aqbank` fayl orqali qabul qiladi**
1. `python run.py --papka D:\zb_test` ni ishga tushiring, kalit yarating, ochiq kalitni
   bankka bering va bank sertifikatini import qiling.
2. Kichik buyurtma bering, masalan 12 345 so'm, partiya hajmi 4, «cheklovsiz» sur'at.
3. «Partiyalar» → «Faylni eksport qilish». Bank tomonida `aqmint.import_batch` bilan
   qabul qiling va bank auditini ishga tushiring.
4. Xuddi shu faylni **qayta** import qiling. Kutilgan natija: «bu partiya allaqachon
   qabul qilingan».

**A3 — `AetherQFabrika` bilan loopback bank serveri**
- AETHER-Q venv'ida bank serverini lokal brokerga (masalan `mosquitto -p 1883`) ulang.
- «Partiyalar» sahifasida broker `localhost`, port 1883 ni kiriting va «Topshirilmaganlarni
  hozir topshirish» ni bosing.
- Kutilgan: log'da «vakolat tasdiqlandi», keyin har partiya uchun «topshirildi».

**A4 — haqiqiy broker (`broker.hivemq.com`)** ⚠ Loopback test brokerni sinamaydi.
```bash
python tools/broker_smoke.py                          # kanal + wire, bank kerak emas
python tools/broker_smoke.py --toliq --papka data     # haqiqiy bankka topshirish
```

**A5 — sekin rejimda uzoq buyurtma (~30 daqiqa)**
1. Sur'atni «Davomiylik 30 daqiqa», CPU byudjetini 25 % qilib qo'ying. Summa ~200 000,
   partiya hajmi 50.
2. Holat satridagi «haqiqiy CPU» ni Task Manager bilan solishtiring.
3. O'rtada oynani yoping, «To'xtatib chiqilsinmi?» ga «Ha» deb javob bering.
4. Qayta oching → «Buyurtmalar» → «Davom ettirish».
5. Oxirida «Tekshiruv» → «Butun jurnalni tekshirish» → TOZA chiqishi kerak.

⚠ Windows'da `process_time` granulyarligi ~15,6 ms. Qisqa o'lchovlar ishonchsiz.

**A6 — har sahifa va har tugma skrinshot bilan** ko'z bilan tekshiriladi. Offscreen
testda shriftlar to'liq bo'lmasligi mumkin, shuning uchun ko'rinish sifati faqat haqiqiy
ekranda baholanadi.

## Holat: nima qilindi, nima sinaldi, nima sinalmadi

**Qilindi va bulutda sinaldi (71 test o'tadi):**
- SPEC §2–§17 hammasi, T1–T15.
- KAT'ning hamma qiymati birinchi urinishdayoq bayt-ma-bayt mos keldi.
- Onlayn protokol faqat **soxta** sessiya va soxta bank bilan sinaldi: xavfsizlik
  qatlami sinalmagan, faqat yuqori qatlam.

**Sinalmadi (bulutda imkonsiz):**
- A1–A6.
- `aetherq_core` bilan haqiqiy handshake.
- Haqiqiy bank qabuli.
- Haqiqiy MQTT broker: bulut konteyneridan `broker.hivemq.com:1883` ga TCP ulanish
  bloklangan, `broker_smoke.py` «brokerga ulanib bo'lmadi» dedi.
- `run.bat`: Linux'da yozilgan, Windows'da ishga tushirilmagan.
- Haqiqiy ekrandagi ko'rinish: faqat offscreen skrinshotlar ko'rildi.
- Uzoq sekin zarbdagi CPU ulushi. Monitor ko'rsatadigan CPU va tezlik ish vaqtida
  **o'lchanadi**, taxminiy vaqt esa «TAXMINIY» deb aniq belgilanadi.

**`tools/kat_tekshir.py` bulutda ishga tushirilmadi.** Xavfsizlik siyosati tashqaridan
kelgan skriptni bajarishga ruxsat bermadi. Uning o'rniga v3 yadrosi o'sha KAT JSON
bilan `tests/test_kat.py` orqali tekshirildi. Birinchi qadamni o'zingiz bajaring.

**Adapter taxmini:** SPEC `aq.ClientHandshake` ning `open()` qanday yozuv turini
qaytarishini aytmaydi. Shuning uchun v3 ochiq matnni turidan qat'i nazar oladi. Agar
haqiqiy kutubxonada ilova ma'lumotidan boshqa yozuv turlari ham bo'lsa, A3 da
`core/topshirish.py` dagi `sessiya.open` chaqiruvlarini moslash kerak bo'lishi mumkin.
