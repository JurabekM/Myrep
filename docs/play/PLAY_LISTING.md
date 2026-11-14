# ROSTOR-2 — Google Play do'kon sahifasi

`tools/store/check_listing.py` har tilning uzunlik chegaralarini tekshiradi (sarlavha ≤ 30, qisqa tavsif ≤ 80,
to'liq tavsif ≤ 4000, "Nima yangi" ≤ 500). Bloklar `<!-- uz:title -->` … `<!-- /uz:title -->` orasida.

Qoidalar (Play metadata siyosati):
- Rasmiy tashkilotlar (IIV, banklar, Click, Payme, operatorlar) bilan aloqa, homiylik yoki "rasmiy" maqomi da'vo qilinmaydi; ularning logotiplari ishlatilmaydi.
- "Eng yaxshi", "№1", reyting yoki boshqa ilovalar bilan solishtirish yo'q; kalit so'zlar takrorlanmaydi.
- Va'da faqat ilova haqiqatan qiladigan narsa haqida ("100% himoya" emas).

Toifa: **Tools** (Asboblar). Teglar: Xavfsizlik, Antivirus. Narx: bepul, reklama yo'q, ichki xaridlar yo'q.

---

## O'zbekcha (asosiy til — uz)

<!-- uz:title -->
ROSTOR-2 firibgarlik qalqoni
<!-- /uz:title -->

<!-- uz:short -->
APK, qo'ng'iroq, SMS va havolani tekshiradi. To'liq internetsiz ishlaydi.
<!-- /uz:short -->

<!-- uz:full -->
ROSTOR-2 smartfoningizni eng ko'p uchraydigan firibgarlik usullaridan himoya qiladi. Ilova to'liq internetsiz ishlaydi: unda INTERNET ruxsati umuman yo'q, shuning uchun u hech qanday ma'lumotni telefoningizdan tashqariga yubora olmaydi.

APK QALQON
Telegram yoki brauzerdan kelgan .apk faylni o'rnatishdan oldin "ROSTOR-2 bilan ochish" orqali tekshiring. Ilova faylni o'rnatmasdan:
• imzo sertifikatini rasmiy ilovalar va telefoningizdagi Play'dan o'rnatilgan nusxa bilan solishtiradi;
• mashhur ilova nomini taqlid qilishni aniqlaydi;
• "SMS + Maxsus imkoniyatlar" kabi bank troyani belgilarini ko'rsatadi.

QO'NG'IROQ QALQONI
Kiruvchi qo'ng'iroq paytida ogohlantiradi:
• rasmiy raqam bo'lsa ham "bu tashkilot SMS kod yoki CVV so'ramaydi" deb eslatadi;
• xorijiy va yashirin raqamlar haqida ogohlantiradi;
• siz bloklagan raqamlarni rad etadi.
Raqamlar telefonning o'zida tekshiriladi, hech qayerga yuborilmaydi.

XABAR VA HAVOLA TEKSHIRUVI
SMS yoki Telegram xabarini "Ulashish" orqali yuboring yoki matnni belgilab "ROSTOR-2 bilan tekshirish"ni tanlang. Ilova o'zbek (lotin va kirill) hamda rus tilidagi tipik firibgarlik naqshlarini, soxta domenlarni (c1ick.uz, kirill harfli "сlick.uz"), "ovoz bering" botlarini va bank nomidan rasmiy bo'lmagan raqamlarni topadi.

QURILMA AUDITI
Ekraningizni, SMS va bildirishnomalaringizni ko'ra oladigan ilovalarni topadi. Har topilmada tegishli sozlamani ochadigan tugma bor.

FIRIBGARLIK HISOBOTI
Aldanib qolsangiz, ROSTOR-2 dalillarni (xabar, raqam, havola, summa) bitta hisobotga yig'adi va uni telefon kaliti bilan imzolaydi. Hisobotni 102 ga yoki bankingizga "Ulashish" orqali o'zingiz yuborasiz.

O'RGANISH
7 ta asosiy firibgarlik usuli va "O'zingizni sinang" testi — 9 ta haqiqiy vaziyat.

ISHONCH
• Accessibility, SMS, kontaktlar, qo'ng'iroqlar jurnali va barcha fayllarga kirish ruxsatlari so'ralmaydi.
• Tekshiruv bazasi ilova ichida imzolangan holda keladi va faqat ilovaning yangi versiyasi bilan yangilanadi.
• "ROSTOR-2 haqiqiymi?" ekrani ilovaning imzo izini ko'rsatadi — soxta nusxani ajratish uchun.

Hech bir dastur 100% himoya bermaydi. Asosiy qoida o'zgarmaydi: SMS kod, karta muddati va CVV faqat sizniki.

ROSTOR-2 — mustaqil loyiha. U IIV, banklar, to'lov tizimlari yoki aloqa operatorlari bilan bog'liq emas; ularning nomlari faqat rasmiy domen, ilova va telefon raqamlarini tekshirish uchun ishlatiladi.
<!-- /uz:full -->

<!-- uz:whatsnew -->
Birinchi versiya: APK Qalqon, Qo'ng'iroq Qalqoni, xabar va havola tekshiruvi, qurilma auditi, imzolangan firibgarlik hisoboti va "O'zingizni sinang" testi. Ilova to'liq internetsiz ishlaydi.
<!-- /uz:whatsnew -->

---

## Русский (ru-RU)

<!-- ru:title -->
ROSTOR-2: защита от мошенников
<!-- /ru:title -->

<!-- ru:short -->
Проверка APK, звонков, SMS и ссылок. Работает полностью без интернета.
<!-- /ru:short -->

<!-- ru:full -->
ROSTOR-2 защищает смартфон от самых распространённых схем мошенничества. Приложение работает полностью без интернета: у него нет разрешения INTERNET, поэтому оно не может отправить никакие данные за пределы телефона.

Интерфейс приложения — на узбекском языке; проверка сообщений понимает узбекский (латиница и кириллица) и русский.

ЩИТ APK
Проверьте .apk-файл из Telegram или браузера до установки через «Открыть с помощью ROSTOR-2». Без установки приложение сравнивает сертификат подписи с официальными приложениями и с копией из Google Play на вашем телефоне, находит подделку под известные названия и признаки банковского трояна («SMS + Спец. возможности»).

ЩИТ ЗВОНКОВ
Во время входящего звонка предупреждает: даже для официального номера напоминает, что организация не спрашивает SMS-код и CVV; предупреждает о зарубежных и скрытых номерах; отклоняет заблокированные вами номера. Номера проверяются на телефоне и никуда не отправляются.

ПРОВЕРКА СООБЩЕНИЙ И ССЫЛОК
Поделитесь SMS или сообщением Telegram с ROSTOR-2 или выделите текст и выберите «Проверить в ROSTOR-2». Приложение находит типичные мошеннические фразы, поддельные домены, ботов «проголосуйте» и неофициальные номера от имени банков.

АУДИТ УСТРОЙСТВА
Показывает приложения, которые могут видеть ваш экран, SMS и уведомления, с кнопкой перехода в нужную настройку.

ОТЧЁТ О МОШЕННИЧЕСТВЕ
ROSTOR-2 собирает доказательства в один отчёт и подписывает его ключом телефона. Отчёт вы сами отправляете в 102 или в свой банк через «Поделиться».

ДОВЕРИЕ
Не запрашиваются разрешения на спец. возможности, SMS, контакты, журнал звонков и доступ ко всем файлам. База проверки поставляется внутри приложения в подписанном виде и обновляется только с новой версией.

Никакая программа не даёт 100% защиты. SMS-код, срок действия карты и CVV — только ваши.

ROSTOR-2 — независимый проект и не связан с МВД, банками, платёжными системами или операторами связи.
<!-- /ru:full -->

<!-- ru:whatsnew -->
Первая версия: щит APK, щит звонков, проверка сообщений и ссылок, аудит устройства, подписанный отчёт о мошенничестве и тест «Проверь себя». Работает полностью без интернета.
<!-- /ru:whatsnew -->

---

## English (en-US) — for Play review

<!-- en:title -->
ROSTOR-2 Fraud Shield
<!-- /en:title -->

<!-- en:short -->
Checks APK files, calls, SMS and links for fraud. Works fully offline.
<!-- /en:short -->

<!-- en:full -->
ROSTOR-2 protects a smartphone against the most common fraud schemes in Uzbekistan. The app works fully offline: it does not request the INTERNET permission, so it cannot send any data off the device.

The app interface is in Uzbek; message checks understand Uzbek (Latin and Cyrillic) and Russian.

APK SHIELD
Check an .apk file received in Telegram or a browser before installing it via "Open with ROSTOR-2". Without installing it, the app compares its signing certificate with official apps and with the copy installed from Google Play, detects name impersonation and banking-trojan traits (SMS + Accessibility).

CALL SHIELD
During an incoming call it warns: even for an official number it reminds that the organization never asks for SMS codes or CVV; it warns about international and hidden numbers and rejects numbers you blocked. Numbers are checked on the device and never sent anywhere.

MESSAGE AND LINK CHECK
Share an SMS or Telegram message with ROSTOR-2, or select text and choose "Check with ROSTOR-2". It detects typical fraud phrases, look-alike domains, "vote for my daughter" bots and unofficial phone numbers used in the name of banks.

DEVICE AUDIT
Lists apps that can read your screen, SMS and notifications, with a button that opens the relevant setting.

FRAUD REPORT
ROSTOR-2 collects the evidence into one report signed with a device key. The user sends it to the police (102) or their bank through the Android share sheet; the app itself sends nothing.

TRUST
No Accessibility, SMS, contacts, call log or all-files permissions. The verification database ships inside the app, signed, and is updated only with a new app version.

No software gives 100% protection. ROSTOR-2 is an independent project and is not affiliated with the police, banks, payment systems or mobile operators.
<!-- /en:full -->

<!-- en:whatsnew -->
First release: APK Shield, Call Shield, message and link check, device audit, signed fraud report and a self-test quiz. Works fully offline.
<!-- /en:whatsnew -->

---

## Grafika

| Fayl | O'lcham | Manba |
| --- | --- | --- |
| `tools/store/play_icon_512.png` | 512×512 PNG | `py tools/store/make_store_graphics.py` |
| `tools/store/feature_graphic_1024x500.png` | 1024×500 PNG (24-bit) | shu skript |
| `tools/store/screenshots/uz/*.png` | 1080×1920 (9:16, Play ≤ 2:1) | emulyatorda reliz APK, `wm size 1080x1920` |
