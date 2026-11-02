# ROSTOR-2

Smartfonni firibgarlik va kiberhujumlardan himoya qiladigan, **to'liq offlayn** Android ilova.
ROSTOR-1 protokoli (`scutum_q1/`) va Google Play'dagi "Apk Qo'riqchi" tahlili asosida.
Tahlil hisoboti: https://claude.ai/artifact/9XkCoezLo1DYRThF9bH57g

- Reliz APK'da `INTERNET` ruxsati yo'q. Buni `tools/check_release.py` yig'ilgan faylda tekshiradi.
- Tekshiruv bazasi ilova ichida keladi va Ed25519 + ML-DSA-65 bilan imzolangan. Baza faqat ilovaning yangi versiyasi bilan yangilanadi.
- Accessibility, SMS, kontaktlar, qo'ng'iroqlar jurnali va barcha fayllarga kirish ruxsatlari so'ralmaydi. Ruxsatlar: `QUERY_ALL_PACKAGES` (qurilma auditi) va `POST_NOTIFICATIONS` (qo'ng'iroq ogohlantirishi).

## Modullar (F1 + F2 + F3)

| Modul | Nima qiladi |
| --- | --- |
| APK Qalqon | APK faylni o'rnatmasdan tahlil qiladi. Imzoni (v1–v4, `apksig`) rasmiy paketlar va Play'dan o'rnatilgan nusxa bilan solishtiradi, nom taqlidini va bank troyani belgilarini aniqlaydi. Telegram'da APK bosilganda "ROSTOR-2 bilan ochish" orqali ishlaydi |
| Qurilma auditi | Accessibility, bildirishnoma tinglovchisi, administrator, overlay, standart SMS ilova va "noma'lum manbadan o'rnatish" ruxsatiga ega ilovalarni topadi. Har topilmada sozlamani ochadigan tugma bor |
| Havola Qalqoni | Punycode/gomoglif (`c1ick.uz`, kirill `сlick.uz`), `@` bilan aldash, brend nomi begona domenda, qisqartiruvchilar, Telegram "ovoz bering" botlari |
| Xabar tekshiruvi | O'zbek (lotin/kirill) va rus tilidagi SMS: kod so'rash, CVV/muddat, "pul olish uchun karta", qo'rqitish, yutuq, oson daromad. Matnni "Ulashish" yoki "belgilab → ROSTOR-2 bilan tekshirish" orqali yuborish mumkin |
| Qo'ng'iroq Qalqoni (F2) | `CallScreeningService` (Android 10+, "qo'ng'iroqlarni aniqlash" roli). Kiruvchi raqamni bazadagi rasmiy va firibgar raqamlar bilan solishtiradi. Rasmiy raqamda "raqamni soxtalashtirish mumkin, kod so'ralmaydi" eslatmasi; operator (STIR/SHAKEN) tasdiqlamasa — kritik; xorijiy va yashirin raqam — ogohlantirish; firibgar va siz bloklagan raqam — rad etiladi. Tarixga faqat belgilangan qo'ng'iroqlar yoziladi. Xabar tekshiruvi matndagi "bank nomi + rasmiy bo'lmagan raqamga qo'ng'iroq qiling" naqshini ham topadi |
| Firibgarlik hisoboti (F3) | Xabar, havola, APK yoki qo'ng'iroq tekshiruvidan oldindan to'ldirilgan forma. Hisobot qurilma kaliti (Ed25519 + ML-DSA-65, urug'lar Android Keystore AES-GCM bilan shifrlangan) bilan imzolanadi va `.txt` + imzolangan `.json` sifatida Android "Ulashish" orqali foydalanuvchi o'zi tanlagan joyga (102, bank) yuboriladi — ilova hech narsa jo'natmaydi. `target_value_hash` ROSTOR-1 `fraud_report.target_hash` bilan bir xil |
| O'zingizni sinang (F3) | 9 ta haqiqiy vaziyat bo'yicha test, har javobdan keyin tushuntirish |
| ROSTOR-2 haqiqiymi? | Ilovaning o'z imzo izi, o'rnatish manbasi, baza holati va ruxsatlari |
| Firibgarlik turlari | ROSTOR-1 tahdid modeli T1–T6 + T7 (Telegram akkauntini egallash) |

## Tuzilma

```
app/                      Flutter (UI + qoidalar) + Kotlin (Android API, imzo tekshiruvi)
  lib/engine/             qoidalar: apk_rules, audit_rules, link_rules, text_rules
  android/.../inspect/    ApkInspector (apksig), DeviceAuditor
  android/.../call/       PhoneRules (sof JVM qoidalar), CallShield, ShieldScreeningService
  android/.../report/     ReportCodec (format, imzo, o'qish matni), ReporterKeys (Keystore), ReportFileProvider
  test/fixtures/          phone_kat.json — Kotlin va Dart uchun umumiy raqam vektorlari
  android/.../db/         DbBundle (gibrid imzo tekshiruvi), DbKeys (qadab qo'yilgan ochiq kalit)
registry/registry.json    baza manbasi: 34 tashkilot, manbasi bilan (2026-11-01 tekshiruvi)
tools/rostor_db/          baza yig'ish/imzolash, KAT vektorlari
tools/rostor_report/      kelgan hisobotlarni tekshirish va guruhlash (developer uchun), hisobot KAT
tools/check_release.py    reliz APK/AAB kafolatlarini tekshirish (INTERNET yo'q, ruxsatlar, baza va ilova imzosi)
tools/create_upload_key.ps1  Play upload kalitini yaratish (faqat siz, o'z terminalingizda)
tools/build_release.ps1   imzolangan APK + AAB, mapping, Dart belgilari, SHA256SUMS -> release/<versiya>/
tools/store/              Play grafikasi, skrinshotlar (uz, 1080×1920), do'kon matni tekshiruvi
tools/testapks/           zararsiz sinov APK'lari (soxta "Click" va oddiy ilova)
tools/make_icon.py        ikonka generatori
docs/play/                do'kon matni (uz/ru/en), maxfiylik siyosati, Play Console javoblari, reliz chek-listi
```

## Yig'ish va sinash

Kerak: Flutter 3.32+, JDK 21 (`flutter config --jdk-dir` Android Studio JBR), Python 3.12+ va `cryptography>=46`.

```bash
cd app && flutter test
```

```bash
cd app/android && ./gradlew :app:testDebugUnitTest
```

Reliz (to'liq tartib — [docs/play/RELEASE_CHECKLIST.md](docs/play/RELEASE_CHECKLIST.md)). Upload kaliti bir marta, o'zingiz yaratasiz:

```bash
powershell -ExecutionPolicy Bypass -File tools/create_upload_key.ps1
```

```bash
powershell -ExecutionPolicy Bypass -File tools/build_release.ps1 -SigningProperties C:\keys\rostor2\upload\key.properties
```

Kalitsiz sinov nusxasi (`release/<versiya>-SINOV/`, Play'ga yaramaydi):

```bash
powershell -ExecutionPolicy Bypass -File tools/build_release.ps1 -AllowDebug
```

Bazani yangilash: `registry/registry.json` ni tahrirlang (har yozuvda manba URL shart, `db_version` ni oshiring), keyin:

```bash
py tools/rostor_db/rostor_db.py build
```

Kelgan hisobotlar (foydalanuvchilar yuborgan `.json` fayllar) bilan ishlash. `aggregate` ROSTOR-1 SPEC 1.1 §15.2 chegaralarini qo'llaydi: kamida 15 ta alohida qurilma (har biri 1 ovoz), 90 kun, qurilmaga kuniga 10 ta hisobot. Natija — faqat **nomzod**: registry'ga qo'shishdan oldin har biri qo'lda tekshiriladi. Qurilma kaliti arzon yaratiladi, shuning uchun bu to'liq Sybil-himoya emas.

```bash
py tools/rostor_report/rostor_report.py verify kelgan/R2-XXXXXXXXXXXX.json
```

```bash
py tools/rostor_report/rostor_report.py aggregate kelgan/ --out nomzodlar.json
```

```bash
py tools/rostor_report/test_rostor_report.py
```

Imzolash kalitlari repo tashqarisida: `C:\keys\rostor2\db` (`ROSTOR2_KEY_DIR`). Kalit yo'qolsa, eski ilovalar yangi bazani qabul qilmaydi.

## Holat

F0–F4 tayyor, versiya 1.0.0 (1). Play materiallari `docs/play/` va `tools/store/` da. Imzolangan reliz `release/1.0.0+1/` da (AAB Play uchun, APK'lar sinov uchun); `release/1.0.0+1-SINOV/` — debug kaliti bilan eski sinov nusxasi.

**Upload kaliti izi** (`CN=ROSTOR-2, C=UZ`, faqat developer uchun — foydalanuvchi ko'radigan iz emas):
`56:25:D8:0E:71:91:40:41:90:DE:4E:38:5A:28:75:C8:C0:90:E3:D5:2D:71:91:6F:8B:65:ED:75:1A:1A:F1:0B`

**Rasmiy imzo izi:** birinchi Play yuklashdan keyin Play Console → App integrity → App signing key SHA-256 shu yerga yoziladi. Shu paytgacha rasmiy iz yo'q.

`gradlew` uchun `JAVA_HOME` Android Studio JBR (JDK 21) bo'lishi kerak. Emulyatorda qo'ng'iroqni sinash:

```bash
adb -s emulator-5556 emu gsm call +79123456789
```
