# APK orqali to'g'ridan-to'g'ri tarqatish

1. **Release kaliti (faqat bir marta, inson):**
   `keytool -genkeypair -v -keystore sv-release.jks -alias sectorverify -keyalg EC -groupname secp256r1 -validity 10000`
   Kalit va parollarni xavfsiz joyda saqlang (yo'qotsangiz yangilanish chiqarib bo'lmaydi). **Commit qilmang.**
2. `sector-verify/keystore.properties` (gitignore qilingan):
   ```
   storeFile=C:/keys/sv-release.jks
   storePassword=...
   keyAlias=sectorverify
   keyPassword=...
   ```
   yoki muhit o'zgaruvchilari `SV_KEYSTORE_PATH`, `SV_KEYSTORE_PASSWORD`, `SV_KEY_ALIAS`, `SV_KEY_PASSWORD`.
3. `.\gradlew.bat clean check :app:assembleRelease` → `app\build\outputs\apk\release\app-release.apk`.
4. Tekshirish: `apksigner verify --print-certs app-release.apk` (SHA-256 sertifikat barmoq izini yozib qo'ying).
5. Tarqatish: ichki fayl serveri yoki MDM. Telefonda «Noma'lum manbalardan o'rnatish» ruxsati kerak.
   Har relizda APK SHA-256 ni e'lon qiling (`certutil -hashfile app-release.apk SHA256`).
6. Yangilash: bir xil kalit bilan imzolangan, `versionCode` kattaroq APK ustidan o'rnatiladi (ma'lumot saqlanadi).
