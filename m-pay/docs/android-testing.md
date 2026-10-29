# Android sinov tartibi (M6)

Ikki daraja: (1) emulyatorda provisioning, OTP, LUK va biometriya; (2) ikki haqiqiy telefonda
NFC tap. Emulyator NFC/HCE ni qo'llamaydi, shuning uchun **tap faqat haqiqiy qurilmalarda**
sinaladi.

## 1. Yig'ish

Talablar: Android SDK 36, JDK 21 (Android Studio JBR).

```bash
cd android && JAVA_HOME="C:/Program Files/Android/Android Studio/jbr" ./gradlew assembleDebug
```

APK'lar: `wallet-demo/build/outputs/apk/debug/wallet-demo-debug.apk`,
`terminal-app/build/outputs/apk/debug/terminal-app-debug.apk`.

Kotlin yadro testlari va Rust bilan interop (telefonsiz):

```bash
cd android && ./gradlew :mpay-core:test
```

```bash
bash scripts/android-interop.sh
```

## 2. Emulyator (provisioning, OTP, LUK, biometriya)

1. Server (HTTP, emulyator xostni `10.0.2.2` orqali ko'radi):
   `mpay-server init --dir emu-sb --listen 127.0.0.1:8080`.
2. Emulyator attestatsiyasi `SOFTWARE` darajali va ildizi "Droid Unregistered Device CA"
   (Google Test LLC). Standart siyosat (`STRONG_BOX`, sandbox CA) uni **rad etadi** —
   `403 PQLINK_ATTESTATION` (bu ham sinov: ishonchsiz ildiz o'tmaydi).
3. Faqat emulyator sinovi uchun: ildiz repoda — `config/android-emulator-test-root.pem` (yoki ilovada "Attestatsiya" tugmasi zanjirni
   `/sdcard/Android/data/uz.mpay.walletdemo/files/attestation-chain.pem` ga yozadi; oxirgi
   sertifikatni `emu-sb/android-emulator-test-root.pem` ga saqlab, `mpay.toml` da:

   ```toml
   [pqlink]
   attestation_roots = ["sandbox-attestation-root.der", "android-emulator-test-root.pem"]
   min_security_level = "SOFTWARE"   # FAQAT emulyator; production — STRONG_BOX
   require_verified_boot = false     # FAQAT emulyator: apparat rootOfTrust yo'q; production — true
   ```

4. `mpay-server serve --config emu-sb/mpay.toml`, ilovada "Ulanish" → "Kartani qo'shish"
   (`mpay.toml` dagi test FPAN). Yangi qurilmada Shield YELLOW beradi: operator kaliti bilan
   "OTP olish" → "Tasdiqlash". Kartada maskalangan DPAN va LUK soni ko'rinadi.
5. Biometriya: emulyatorda PIN (`adb shell locksettings set-pin 1111`), barmoq izi
   (Settings → Pixel Imprint, `adb emu finger touch 1`). "To'lovga tayyorlash" → `adb emu finger touch 1`
   → kartada "To'lovga tayyor: N s" (60 s oyna).

**2026-10-24 natijasi (Medium Phone API 36):** yuqoridagi barcha qadamlar o'tdi; server logida
7 ta marshrut 200, ochiq PAN 0 marta. Terminal ilovasi NFC'siz qurilmada "NFC yo'q" xatosini
beradi va terminal kaliti ekranda maskalanadi.

## 3. Ikki telefon: haqiqiy NFC tap (qabul mezoni)

Talablar: ikkala telefonda NFC; hamyon telefonida HCE (`android.hardware.nfc.hce`) va
barmoq izi; ikkalasi server bilan bir tarmoqda (yoki `adb reverse tcp:8080 tcp:8080`).

1. Server kompyuterda: `mpay-server init --dir sb --listen 0.0.0.0:8080` (yoki `--tls`),
   so'ng `serve`. Hamyon telefoni StrongBox'siz bo'lsa (TEE), `min_security_level =
   "TRUSTED_ENVIRONMENT"` va Google ildizlari (`config/google-attestation-roots.pem`) qo'shiladi.
2. **Hamyon telefoni** (`wallet-demo`): server manzili `http://<kompyuter IP>:8080` →
   "Ulanish" → test FPAN bilan "Kartani qo'shish" (kerak bo'lsa OTP) →
   "Standart to'lov ilovasi" (Sozlamalar → Kontaktsiz to'lovlar → M-Pay Hamyon).
3. **Terminal telefoni** (`terminal-app`, 1-faza P1.4 — TLS + mTLS):
   `mpay-server init --tls` sandbox'idan paket yarating:
   `mpay-server terminal-bundle --config sb/mpay.toml --url https://<kompyuter IP>:8443`,
   faylni telefonga `adb push terminal-bundle.json /sdcard/Android/data/uz.mpay.terminalapp/files/`
   (yoki fayl tanlash oynasi), ilovada "Terminal paketini import qilish" → "Ulanishni tekshirish"
   ("Ulanish ishlaydi … mTLS sertifikati qabul qilindi"). So'ng summa (masalan 25 000) →
   "To'lov qabul qilish". Paketsiz qo'lda rejim (oddiy HTTP) faqat `--tls` siz sandbox uchun.
4. Hamyon telefonida "To'lovga tayyorlash" → barmoq izi → 60 s ichida telefonlarni orqa
   tomonlari bilan tekkizing.
5. Kutilgan natija: terminalda **MA'QULLANDI**, kod `00`, maskalangan DPAN, RRN, Shield bali;
   hamyonda ATC 1 ga oshadi va voqealar ro'yxatida "Tap: ATC=1".
6. Qo'shimcha holatlar:
   * 1 000 000 so'mgacha summa biometriyasiz ham o'tadi (CVR'da "CDCVM bajarilmagan");
   * 1 000 000 so'mdan katta summa biometriyasiz → applet `6986` → terminalda "Telefonda
     tasdiqlang" (o'quvchi kutishda qoladi), biometriyadan keyin qayta tekkizish → `00`;
   * ekran o'chiq bo'lsa CDCVM oynasi hisobga olinmaydi (`isInteractive`) — katta summa `6986`;
   * bir xil tapni qayta yuborish imkoni yo'q: har tapda ATC oshadi, server replay'ni `Q1` bilan
     rad etadi (JVM interop testida sinalgan).
7. Server logida faqat maskalangan PAN va token ID borligini tekshiring.

**Holat:** bu bo'lim hali haqiqiy qurilmalarda bajarilmagan — ishlab chiqish muhitida NFC'li
ikki telefon yo'q. Tap yo'li (applet ↔ terminal yadrosi ↔ Rust emitent) JVM interop testida
loopback orqali sinalgan (`InteropTest`); `IsoDep`/`HostApduService` qatlami sinalmagan.

## 4. Terminal TLS + mTLS (emulyatorda, 1-faza P1.4)

1. `mpay-server init --dir emu-tls --listen 127.0.0.1:8443 --tls` (emulyator xostni `10.0.2.2` orqali ko'radi).
2. `mpay-server terminal-bundle --config emu-tls/mpay.toml --url https://10.0.2.2:8443 --out terminal-bundle.json`.
3. `mpay-server serve --config emu-tls/mpay.toml`.
4. `adb push terminal-bundle.json /sdcard/Android/data/uz.mpay.terminalapp/files/terminal-bundle.json`.
5. Ilovada "Terminal paketini import qilish" → paket o'qiladi va **o'chiriladi** → "Ulanishni tekshirish".

Kutilgan: "Ulanish ishlaydi — Kalit: terminal-1 — TLS: server pinlangan, mTLS sertifikati qabul qilindi".
Salbiy: paketni o'chirib, qo'lda rejimda xuddi shu `https://` manzilga — tizim CA'si sandbox sertifikatini
tanimaydi (TLS xatosi); `http://` bilan TLS serverga ulanib bo'lmaydi.

## 5. Virtual NFC — to'liq tap emulyatorda (P1.8 o'rnini bosuvchi sinov)

Emulyatorda NFC/HCE apparati yo'q. Debug build'larda **virtual NFC ko'prigi** bor: hamyon
(`wallet-demo`) `127.0.0.1:47661` da APDU qabul qiladi va ularni haqiqiy HCE servisi bilan bir xil yo'ldan
(`HceDispatcher` → applet, CDCVM, LUK, ATC) o'tkazadi; terminal (`terminal-app`) "Virtual tap" bilan
`IsoDep` o'rniga shu socket'dan foydalanadi. Ikkala ilova bitta emulyatorda. Radiodan boshqa hamma
qatlam haqiqiy: Android Keystore, BiometricPrompt, terminal yadrosi, TLS + mTLS, server, Shield, emitent.

**Xavfsizlik:** ko'prik faqat `src/debug` da — release APK'ga kirmaydi (relay hujumi uchun eshik
bo'lmasin). Tekshiruv: `bash scripts/check-release-apk.sh` (debug'da bor, release'da yo'q).

Tartib (2026-10-25 da shu tartibda bajarildi):

1. `mpay-server init --dir emu-tls --listen 127.0.0.1:8443 --tls`; `config/android-emulator-test-root.pem` ni
   nusxalab `attestation_roots` ga qo'shing, `min_security_level = "SOFTWARE"`,
   `require_verified_boot = false` (emulyatorda apparat `rootOfTrust` yo'q).
2. `mpay-server identity --config emu-tls/mpay.toml` → `fingerprint` va `tls_pin`; hamyonni pinlar bilan yig'ing:
   `./gradlew :wallet-demo:assembleDebug -Pmpay.serverFingerprints=<fp> -Pmpay.tlsPin=<pin>`.
3. `mpay-server terminal-bundle --config emu-tls/mpay.toml --url https://10.0.2.2:8443`; `serve`.
4. Hamyon: server `https://10.0.2.2:8443` → "Ulanish" → karta qo'shish (YELLOW bo'lsa OTP'ni xostdan operator
   mTLS sertifikati bilan oling — Windows `curl` (Schannel) PEM mijoz sertifikatini qabul qilmaydi, Python
   `ssl` ishlaydi) → "Virtual NFC".
5. Terminal: paketni `adb push` → "Terminal paketini import qilish" → "Ulanishni tekshirish" → summa → "Virtual tap".

Natija (Medium Phone API 36):

| Qadam | Natija |
|---|---|
| 25 000 so'm | **MA'QULLANDI**, `00 APPROVED`, Shield 17 |
| 2 000 000 so'm biometriyasiz | "Telefonda tasdiqlang" (`6986`) |
| Hamyonda barmoq izi → 60 s ichida qayta tap | **MA'QULLANDI**, `00 APPROVED_AFTER_REVIEW`, Shield 646 |
| Yana 2 000 000 so'm | "Telefonda tasdiqlang" — CDCVM bir martalik |
| Server logi | `/v1/authorizations` 2 × 200, ochiq PAN 0 |

Haqiqiy NFC radiosi (antenna, maydon uzilishi, `IsoDep` vaqtlari, Android HCE marshrutlash va "standart
to'lov ilovasi") faqat §3 da — ikki haqiqiy telefonda sinaladi.

## 6. OTP SMS — emulyatorda virtual SMS shlyuzi bilan (2-faza P2.1)

Bank SMS shlyuzi o'rnida `mpay-smsgw` (ADR-0016). Tartib (2026-10-25 da bajarildi):

1. §5 dagi 1–3-qadamlar; `mpay.toml` da `[otp] channel = "webhook"` va `[otp.webhook]` qatorlarini yoqing
   (`init` izohda yozib qo'yadi). `MPAY_SMS_TOKEN` muhitda bo'lishi kerak — server uni ishga tushishda
   tekshiradi (`identity`, `terminal-bundle` buyruqlari uchun ham).
2. `MPAY_SMS_TOKEN=… mpay-smsgw --listen 127.0.0.1:47700`, keyin `mpay-server serve`.
3. Hamyonda yangi karta qo'shish. Emulyator kaliti `SOFTWARE` darajasida, shuning uchun boshqa qurilmada
   faol karta emulyatorda **RED** (`IDV_WEAK_ATTESTATION` + `IDV_NEW_DEVICE_EXISTING_CARD`) — bu to'g'ri;
   YELLOW uchun hali tokenlanmagan demo karta olinadi.
4. Kod "virtual telefon" qutisidan: `curl -H "Authorization: Bearer …" "http://127.0.0.1:47700/messages?to=%2B998000000003"`.

| Qadam | Natija |
|---|---|
| Karta qo'shish (`…0037`) | "Qo'shimcha tasdiq kerak (YELLOW): kod SMS bilan +998*******03 raqamiga yuborildi"; operator kaliti maydoni yo'q |
| "Qayta yuborish" | shlyuzda 2 ta SMS, bir xil kod; server `idv/resend` 200 |
| SMS'dagi kodni kiritib "Tasdiqlash" | "Token faol: 990077******8375", 5 ta LUK |
| Server va shlyuz loglari | OTP 0 marta, to'liq telefon 0 marta (faqat `+998*******03`) |

## 7. Play Integrity — emulyatorda sandbox mock'i bilan (2-faza P2.6)

Emulyatorda Google Play Integrity API ishlamaydi (Play Console'da ro'yxatdan o'tgan ilova va Cloud
loyiha kerak). Sandbox'da server mock'i (ADR-0021): demo ilova Kotlin'da `requestHash` ni hisoblaydi va
tokenni o'z PQ Link sessiyasi orqali oladi (`POST /v1/sandbox/integrity-token/device`, muhrlangan) —
operator kaliti va mTLS sertifikati kerak emas, TLS + mTLS sandbox'ida ham ishlaydi. "Ilova yaxlitligi"
tugmalari stsenariyni tanlaydi. (2026-10-26 dagi birinchi sinovda token operator endpointidan olingan;
TLS sandbox'ida u `403 MTLS_REQUIRED` berardi — shuning uchun qurilma yo'li qo'shildi.)

Tartib (2026-10-26 da bajarildi, Medium Phone API 36, HTTP):

1. §2 dagi 1–3-qadamlar (`init` endi `[integrity] mode = "mock"`, `required = true` yozadi).
2. `mpay-server serve`; ilovada "Ulanish".

| Qadam | Natija |
|---|---|
| (birinchi sinov, operator yo'li) Operator kalitisiz "Kartani qo'shish" (`…0013`) | "Xato: 403 INTEGRITY_REQUIRED"; server logi: `integrity: token rad etildi` |
| Operator kaliti, `strong` | token qabul qilindi (`app=2 level=3`); **YELLOW** — faqat `IDV_WEAK_ATTESTATION` (emulyator kaliti SOFTWARE); "OTP olish" → "Tasdiqlash" → "Token faol: 990077******6701", 5 ta LUK |
| Boshqa karta (`…0028`), `no_integrity` | "Rad etildi: RED [IDV_WEAK_ATTESTATION, IDV_INTEGRITY_APP_UNRECOGNIZED, IDV_INTEGRITY_DEVICE_NONE]" |
| Server logi | ochiq PAN 0, token (JWS) 0; `/v1/sandbox/integrity-token` 2 × 200 |

Qurilma yo'li bilan qayta sinov (TLS + mTLS, `required = true`, Shield dvigateli, operator kaliti
maydoni **bo'sh**):

| Qadam | Natija |
|---|---|
| `strong`, karta `…0028` | `/v1/sandbox/integrity-token/device` 200, verdict `app=2 level=3`; YELLOW (faqat `IDV_WEAK_ATTESTATION`) |
| `no_integrity`, karta `…0037` | "Rad etildi: RED [IDV_WEAK_ATTESTATION, IDV_INTEGRITY_APP_UNRECOGNIZED, IDV_INTEGRITY_DEVICE_NONE]" |
| Server logi | ochiq PAN 0, token (JWS) 0 |

Haqiqiy telefonda Play Integrity (`StandardIntegrityManager`) — `TODO(spec)`: bank Play Console va Cloud
loyihasini bergach (`wallet-sdk` `IntegrityTokenProvider` izohiga qarang).

## 8. REVIEW `step_up` — terminalda `Q2` (2-faza P2.7)

Bank siyosati (ADR-0022): Shield REVIEW'da karta egasi telefonda tasdiqlamagan bo'lsa emitent `Q2`
qaytaradi, terminal "Telefonda tasdiqlang" holatiga o'tadi va o'sha summa bilan qayta tap kutadi.
Tartib (2026-10-26 da bajarildi, Medium Phone API 36): §5 dagi TLS + mTLS sandbox, virtual NFC.
REVIEW'ni barqaror chaqirish uchun server `[shield] engine = "stub"` bilan (`REVIEW…` savdo nuqtasi).
O'sha sinovda `[integrity] required = false` edi (mock token o'shanda faqat operator mTLS yo'lida edi);
endi demo ilova tokenni qurilma yo'li orqali oladi (§7) — `required = true` bilan ham ishlaydi. OTP
§5 dagidek xostdan operator mTLS sertifikati bilan olinadi.

| Qadam | Natija |
|---|---|
| Oddiy tap, 25 000 so'm (`SHOP…`) | MA'QULLANDI, `00 APPROVED` |
| Merchant `REVIEW00000001`, 25 000 so'm, biometriyasiz | "Telefonda tasdiqlang — Bank karta egasini tasdiqlashni so'radi (REVIEW_STEP_UP)", "Bekor qilish" ko'rinadi (to'lov kutishda) |
| Hamyon: "To'lovga tayyorlash" → `adb emu finger touch 1` → terminal: qayta tap | MA'QULLANDI, `00 APPROVED_AFTER_REVIEW`, Shield 600 |
| Server logi | `Q2 REVIEW_STEP_UP` → `00 APPROVED_AFTER_REVIEW`; ochiq PAN 0 |

## 9. Terminal ilovasi: klaviatura (3-faza tayyorgarligi)

Avval ilova ochilishi bilan "Summa" maydoni fokus olib, to'liq QWERTY klaviatura pastdagi holat
kartasi va sozlamalarni yopardi. Endi:

| Harakat | Kutilgan (`adb shell dumpsys input_method \| grep mInputShown`) |
|---|---|
| Ilovani ochish | `mInputShown=false` (boshlang'ich fokus maydonda emas; manifest `stateHidden`) |
| "Summa" ga teginish | raqamli klaviatura (`inputType=0x2`), "✓" — `ImeAction.Done` |
| "✓", bo'sh joyga teginish yoki istalgan tugma | klaviatura yopiladi; tugma bitta bosishda ishlaydi |
| Pastdagi maydon (Merchant ID) | klaviatura ustiga aylanadi, ko'rinib turadi |

Tekshirilgan: Medium_Phone_API_36.0 emulyatori (1080×2400).

## 10. Bekor qilish ro'yxati build'da (ADR-0029)

Kalit oshkor bo'lgan va hujumchi serveri ro'yxatni bermaydigan holat:

```bash
mpay-server root-keygen --out root.json                      # root_fingerprint chiqadi
mpay-server init --dir sb --listen 127.0.0.1:8080             # "PQ Link server barmoq izi: <SFP>"
mpay-server revoke --root-key root.json --version 5 --fp <SFP> --out rev.json
mpay-server revocations-check --file rev.json --root-fingerprint <ROOT>
mpay-server serve --config sb/mpay.toml                       # [pqlink] revocations yo'q → 404
cd android && ./gradlew :wallet-demo:assembleDebug -Pmpay.revocationsFile=../rev.json -Pmpay.rootFingerprint=<ROOT>
```

Ilovada "Ulanish" → **"Xato: server identifikatori bekor qilingan: <SFP>…"**, voqealarda
"Bekor qilish ro'yxati yangilandi: versiya 5 (ilova)"; server logida faqat `/v1/pqlink/identity` va
`/revocations` — handshake boshlanmaydi. Nazorat: boshqa barmoq izini bekor qiluvchi ro'yxat bilan
build — handshake boshlanadi (2026-10-27, emulyator Medium_Phone_API_36.0).

## 11. M-Pay mijoz hamyoni (`wallet-app`, ADR-0030)

Product ilova: onboarding, PIN/biometriya qulfi, ko'p karta, to'lov, tarix, karta boshqaruvi,
bildirishnomalar, uz/ru/en. Sandbox tayyorlash:

1. `mpay-server init --dir emu-sb --listen 127.0.0.1:8080`; `mpay.toml` da §2 dagi emulyator sozlamalari,
   §6 dagi `[otp] channel = "webhook"` va `[integrity] package_name = "uz.mpay.wallet"`.
2. `mpay-smsgw` va `mpay-server serve` (§6).
3. `./gradlew :wallet-app:assembleDebug` (yoki `assembleRelease`; server `-Pmpay.server=…`, pinlar `-Pmpay.serverFingerprints=…`).
4. Terminal: `terminal-app` qo'lda rejim (`http://10.0.2.2:8080` + terminal kaliti), hamyonda
   Sozlamalar → "Virtual NFC (faqat sinov)" (faqat debug).

Natija (2026-10-29, Medium Phone API 36, debug va release):

| Ekran / holat | Natija |
|---|---|
| Tanishuv → til (ru) → PIN | ekran rus tilida; `123456` — "juda oddiy", takrorlash mos kelmasa — qaytadan |
| Biometriya, bildirishnoma ruxsati | tizim oynasi, so'ng bosh ekran; server: identity → enroll → hello/finish → `/v1/wallet/tokens` 200 |
| Karta qo'shish | Luhn xatosi qizil; `MM/YY`; Integrity mock 200; YELLOW → "Kod SMS orqali +998*******01" |
| OTP | noto'g'ri kod → "Kod noto'g'ri" (422); shlyuzdagi kod → karta, 5 ta kalit, bank kartasi maskasi |
| OTP'siz tashlab ketilgan karta | "Tasdiqlanmagan" — o'chirish mumkin |
| Yangi qurilmada boshqa qurilmaning kartasi / ko'p karta urinishi | "Bank kartani qo'shishni rad etdi" (Shield RED) |
| To'lov: biometriya → virtual tap | terminal `00`; hamyonda "To'lov tasdiqlandi 25 000,00 so'm" (emitent tarixidan) |
| Ikkinchi karta tanlab 25 000 (qoldiq 10 000) | terminal va hamyonda `51` |
| Asosiy karta to'xtatilgan | to'lov ekrani faol kartani ko'rsatadi va tap aynan shu karta bilan |
| Tarix | kartalar bo'yicha, kun sarlavhasi, Toshkent vaqti, rad etilgani chizilgan |
| O'zim to'xtatish / yoqish | banner, "To'xtatilgan" belgisi, yoqish tugmasi |
| Bank to'xtatdi (operator API) | "Bank to'xtatgan" banneri, yoqish tugmasi yo'q |
| Bank yoqdi, fon sinxronlash | bildirishnoma "Karta holati o'zgardi — Karta yana faol" |
| Qulf | fonda 30 s → biometrik oyna; noto'g'ri PIN — "yana 4 urinish"; PIN almashtirish → eski PIN rad |
| Til almashtirish (sozlamalar) | butun ilova rus tilida, qulf qayta so'ralmaydi |
| Hamyonni tozalash | onboarding (til saqlanadi) |
| Release (R8, 4,4 MB) | ishga tushadi, karta qo'shiladi; sinov vositalari yo'q; `screencap` qora (FLAG_SECURE) |
| Loglar (server, SMS shlyuzi, logcat) | ochiq PAN, OTP, terminal kaliti — 0; faqat maskalangan PAN va token ID |

Emulyatorda topilib tuzatilgan xatolar:

* ildizda `Surface` yo'q edi — rang berilmagan matnlar qora;
* biometric 1.1.0 eski `fragment` ni olib keladi — bildirishnoma ruxsatida crash ("lower 16 bits");
* to'lov ekrani: oldingi tap holati qolardi, tanlangan karta tapga qo'llanmasdi;
* tapdan keyin karta tanlovi ekranda qolib, SDK'da tozalanardi;
* terminal javobi kelmasa — abadiy "kutilmoqda";
* karta qo'shilgach bank kartasi maskasi chiqmasdi;
* tasdiqlanmagan karta "bu telefonda yo'q" deb ko'rinardi;
* release dex'ida virtual NFC sinf nomi satri qolardi (`DebugTools` build turiga ajratildi).

WorkManager davriy ishi emulyator soati sakraganda keyingi ishni kunlarga surdi — debug'da
"Fon sinxronlash (faqat sinov)" bir martalik ish beradi (xuddi shu `SyncWorker`).
