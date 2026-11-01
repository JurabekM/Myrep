# CLAUDE.md — «Qarzsiz»

Har sessiya boshida o'qi: `README.md`, `docs/TAHLIL.md` (mahsulot mantig'i va ohangi).

Qat'iy qoidalar:
- Ilova to'liq offlayn: `INTERNET` ruxsati, tarmoq kutubxonalari, analitika va reklama qo'shilmaydi.
- Pul — `Long` (kichik birlik), foiz — bazis punkt. `Float/Double` pul uchun yo'q.
- Pul va biznes mantiq faqat `android/core/` da; Compose UI faqat ko'rsatadi.
- Yangi pul funksiyasi: avval `spec/test-vectors/` ga kirish, `python3 -I spec/oracle/oracle.py --generate spec/test-vectors`, keyin Kotlin.
- Ohang: iliq, ayblamaydigan; natija va'da qilinmaydi; har ma'lumot ekranida disklеymer.
- Hissiy bosim, bajarib bo'lmaydigan va'da va «qonun himoya qiladi» kabi yuridik da'volar matnga kirmaydi.
- Diniy matn chiqarilmaydi (foydalanuvchi o'z odatini o'zi qo'shadi).
- Kod, identifikatorlar, commit — inglizcha; izohlar, hujjatlar, UI — o'zbekcha (lotin).
- UI matni faqat lotinda yoziladi va `ui.Text` / `t()` orqali chiqadi (kirill — avtomatik). `material3.Text` ni
  to'g'ridan-to'g'ri import qilmang. Foydalanuvchining erkin matni — `raw = true`. Yangi so'z noto'g'ri
  o'girilsa — `Translit.words` lug'atiga va `TranslitTest` ga qo'shing.
- Har vazifa oxirida `docs/CHANGELOG.md` yangilanadi.

Tekshiruv:
- `python3 -I spec/oracle/oracle.py --selftest && python3 -I spec/oracle/oracle.py --check spec/test-vectors`
- `cd android && ./gradlew :core:test :app:testDebugUnitTest :app:assembleRelease`
- Ekran o'zgarsa: `android/app/build/outputs/roborazzi/*.png` ni ko'zdan kechiring.
