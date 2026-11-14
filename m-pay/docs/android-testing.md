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
3. Faqat emulyator sinovi uchun: ilovada "Attestatsiya" tugmasi zanjirni
   `/sdcard/Android/data/uz.mpay.walletdemo/files/attestation-chain.pem` ga yozadi; oxirgi
   sertifikatni `emu-sb/android-emulator-test-root.pem` ga saqlab, `mpay.toml` da:

   ```toml
   [pqlink]
   attestation_roots = ["sandbox-attestation-root.der", "android-emulator-test-root.pem"]
   min_security_level = "SOFTWARE"   # FAQAT emulyator; production — STRONG_BOX
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
3. **Terminal telefoni** (`terminal-app`): "Sozlamalar" ga server manzili va `init` bergan
   **terminal** kaliti; summa (masalan 25 000) → "To'lov qabul qilish".
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
