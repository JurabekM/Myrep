# Google Play do'kon sahifasi matnlari

Play Console → **Grow users → Store presence → Main store listing** (va **Translations**). Har blok
Play'ga o'zgarishsiz ko'chiriladi. Chegaralar: nom 30, qisqa tavsif 80, to'liq tavsif 4000,
«What's new» 500 belgi — `python tools/store/check_listing.py` sanaydi (har blok ostida natija).

Qoidalar (Play metadata siyosati): «eng yaxshi», «№1», narx/aksiya, emoji, BOSH HARFLAR, boshqa
ilovalar nomi va va'dalar yo'q. «Ribosiz» — ilova vazifasi; «halol sertifikatlangan», «fatvo» kabi
da'volar yozilmaydi (ilovaning o'zi «Fatvo yoki moliyaviy maslahat emas» deydi). O'zbekcha matnda
`oʻ/gʻ` — U+02BB, tutuq — U+02BC (ilova matnlari bilan bir xil).

Grafika: ikonka `tools/store/play_icon_512.png`, banner `tools/store/feature_graphic_1024x500.png`,
telefon skrinshotlari `tools/store/screenshots/uz/` (7 ta, o'zbekcha sahifa uchun) va
`tools/store/screenshots/ru/` (5 ta, ruscha va inglizcha sahifa uchun), 1080×1920.

Til: Play Console tillari ro'yxatida o'zbekcha bo'lsa — asosiy til `uz`, aks holda asosiy `ru-RU`
va o'zbekcha matn keyin qo'shiladi. Inglizcha (`en-US`) — boshqa tildagi foydalanuvchilar uchun.

---

## Oʻzbekcha (uz)

### Nom
```text
Baraka Dastur
```

### Qisqa tavsif
```text
Ribosiz shaxsiy va oilaviy moliya daftari: internetsiz, shifrlangan.
```

### To'liq tavsif
```text
Baraka Dastur — ribosiz shaxsiy va oilaviy moliya daftari. Ilova internetga ulanmaydi: barcha yozuvlar faqat telefoningizda, shifrlangan holda saqlanadi.

Asosiy imkoniyatlar
• Daromad va xarajatni tez yozish. Bosh ekran daromad turingizga moslashadi: kunlik naqd, buyurtma boʻyicha yoki oylik maosh.
• «Kelajagim»: avval oʻzingizga toʻlang — har daromaddan ulush ajrating va haftalik odatni kuzating.
• Oylik audit: «Pul qayerga ketdi?» savoliga oddiy javob.
• Qarzlar va nasiya: qarzdan chiqish rejasi, majburiyatlar va eslatmalar.
• Favqulodda zaxira, konvertlar, obunalar va avtotoʻlovlar.
• Narx daftari: inflyatsiya pulingizga qanday taʼsir qilayotganini koʻring.
• Kelishuvlar: qarz, sheriklik va oilaviy kelishuvlarni 9 savol bilan yozib oling va PDF hujjat oling.
• Taklifni tekshirish: «tavakkalsiz foyda» vaʼdasidagi xavf belgilarini bir daqiqada koʻring.
• Bilimga sarmoya: kurs yoki oʻqish oʻzini qancha vaqtda qoplashini hisoblang.
• Marosimlar, «Hunardan ishga» gʻoya hisobi va sheriklik daftari.
• Haftalik boblar va vazifalar: moliyaviy odatlarni bosqichma-bosqich oʻrganing.
• Oila aʼzolari: har yozuvda «kim?» belgisi.

Xavfsizlik va maxfiylik
• 6 xonali PIN va biometrik qulf.
• Maʼlumotlar bazasi shifrlangan, kaliti Android Keystore tizimida.
• Reklama, analitika va kuzatuv yoʻq. Ilovada internet ruxsati yoʻq.
• Zaxira nusxa — siz tanlagan parol bilan shifrlangan fayl. Telefon almashsa, shu fayldan tiklaysiz.

Tillar: oʻzbekcha va ruscha.

Ilovadagi materiallar taʼlimiy maqsadda. Ular fatvo, investitsiya yoki moliyaviy maslahat emas.
```

### What's new (1.0.0)
```text
Birinchi nashr: daromad va xarajatlar, «Kelajagim», oylik audit, qarzlar, kelishuvlar, taklifni tekshirish va haftalik boblar. Hammasi internetsiz va shifrlangan.
```

---

## Русский (ru-RU)

### Название
```text
Baraka Dastur
```

### Краткое описание
```text
Личные и семейные финансы без рибы: работает офлайн, данные зашифрованы.
```

### Полное описание
```text
Baraka Dastur — дневник личных и семейных финансов без рибы. Приложение не подключается к интернету: все записи хранятся только на вашем телефоне в зашифрованном виде.

Основные возможности
• Быстрый учёт доходов и расходов. Главный экран подстраивается под ваш тип дохода: ежедневная наличность, работа на заказ или ежемесячная зарплата.
• «Моё будущее»: сначала заплатите себе — откладывайте долю с каждого дохода и следите за еженедельной привычкой.
• Месячный аудит: простой ответ на вопрос «Куда ушли деньги?».
• Долги и покупки в рассрочку: план выхода из долгов, обязательства и напоминания.
• Резерв на чёрный день, конверты, подписки и автоплатежи.
• Тетрадь цен: смотрите, как инфляция влияет на ваши деньги.
• Договорённости: оформляйте долги, партнёрства и семейные договорённости по 9 вопросам и получайте PDF-документ.
• Проверка предложения: за минуту увидите признаки риска в обещании «прибыли без риска».
• Вложение в знания: посчитайте, за сколько окупится курс или обучение.
• Семейные торжества, расчёт идеи «От ремесла к делу» и журнал партнёрства.
• Еженедельные главы и задания: осваивайте финансовые привычки шаг за шагом.
• Члены семьи: у каждой записи есть отметка «кто?».

Безопасность и конфиденциальность
• 6-значный PIN-код и биометрическая блокировка.
• База данных зашифрована, ключ хранится в Android Keystore.
• Нет рекламы, аналитики и отслеживания. У приложения нет разрешения на интернет.
• Резервная копия — файл, зашифрованный выбранным вами паролем. При смене телефона данные восстанавливаются из него.

Языки: узбекский и русский.

Материалы в приложении носят образовательный характер и не являются фетвой, инвестиционной или финансовой консультацией.
```

### Что нового (1.0.0)
```text
Первый выпуск: доходы и расходы, «Моё будущее», месячный аудит, долги, договорённости, проверка предложений и еженедельные главы. Всё офлайн и в зашифрованном виде.
```

---

## English (en-US)

### Title
```text
Baraka Dastur
```

### Short description
```text
Riba-free personal and family finance notebook. Works offline, data encrypted.
```

### Full description
```text
Baraka Dastur is a riba-free (interest-free) notebook for personal and family finances. The app never connects to the internet: every record stays on your phone, encrypted.

Main features
• Quick income and expense entry. The home screen adapts to how you earn: daily cash, paid-per-order work or a monthly salary.
• "My Future": pay yourself first — set aside a share of every income and keep a weekly streak.
• Monthly audit: a simple answer to "Where did the money go?".
• Debts and store credit: a debt payoff plan, obligations and reminders.
• Emergency reserve, envelopes, subscriptions and automatic payments.
• Price diary: see how inflation affects your money.
• Agreements: record loans, partnerships and family agreements with 9 questions and get a PDF document.
• Offer check: spot the warning signs behind a "risk-free profit" promise in one minute.
• Invest in knowledge: estimate how long a course or training takes to pay for itself.
• Family celebrations, a "From craft to business" idea calculator and a partnership ledger.
• Weekly chapters and tasks: build money habits step by step.
• Family members: every record shows "who?".

Security and privacy
• 6-digit PIN and biometric lock.
• Encrypted database; the key is kept in the Android Keystore.
• No ads, analytics or tracking. The app has no internet permission.
• Backup is a file encrypted with a password you choose; restore from it when you change phones.

Languages: Uzbek and Russian.

The content in the app is educational. It is not a fatwa, investment advice or financial advice.
```

### What's new (1.0.0)
```text
First release: income and expenses, "My Future", monthly audit, debts, agreements, offer check and weekly chapters. Everything offline and encrypted.
```
