# H3 — release imzolash va tarqatish (faqat inson)

**Nega inson:** imzo kaliti ilovaning "shaxsi". Kim kalitga ega bo'lsa, ilovaning yangilanishi sifatida istalgan
kodni o'rnata oladi. Shuning uchun kalitni **faqat siz** yaratasiz va saqlaysiz: u repoga, CI'ga (siz qaror
qilmaguningizcha) va Claude bilan chatga **hech qachon tushmaydi**.

**Oldin:** H1 va H2 bajarilgan, `docs/RELEASE_CHECKLIST.md` dagi AC jadvali to'liq, `master` CI'da yashil.
**Vaqt:** birinchi marta ~1 soat (kalit + zaxira + birinchi reliz); keyingi relizlar ~15 daqiqa.

---

## 0. Tarqatish yo'lini tanlang

| | **A. APK to'g'ridan-to'g'ri** (ichki server, MDM, Telegram) | **B. Google Play** |
|---|---|---|
| Fayl | `app-release.apk` | `app-release.aab` |
| Foydalanuvchidagi imzo | **sizning kalitingiz** | Google'ning *app signing* kaliti (Play App Signing) |
| Sizning kalitingiz | release kaliti | *upload* kaliti (faqat Play'ga yuklash uchun) |
| Qo'shimcha | — | `docs/PLAY_STORE.md` (FGS deklaratsiyasi, Data safety, maxfiylik URL) |

> **Muhim:** A va B da foydalanuvchi qurilmasidagi imzolar **har xil**. Play'dan o'rnatilgan ilovani APK bilan
> (yoki aksincha) yangilab bo'lmaydi — avval o'chirish kerak, bu esa qurilmadagi ma'lumotni (sessiyalar bazasi) o'chiradi.
> Bitta yo'lni tanlang. Ikkalasi kerak bo'lsa — ularni alohida foydalanuvchi guruhlariga bering.

## 1. Kalitni yaratish (bir marta)

Windows'da (JDK 17 o'rnatilgan; `keytool` — `%JAVA_HOME%\bin` da):

```
mkdir C:\keys
keytool -genkeypair -v -storetype PKCS12 -keystore C:\keys\sv-release.p12 ^
  -alias sectorverify -keyalg RSA -keysize 4096 -validity 10000 ^
  -dname "CN=Sector Verify, O=<tashkilot nomi>, C=UZ"
```

- **Parol:** kamida 16 belgi, parol menejeri yaratgani. PKCS12 da kalit paroli ombor paroli bilan **bir xil** bo'ladi.
- **RSA 4096** — ikkala yo'lga ham mos (Play upload kaliti uchun RSA 2048+ tavsiya etiladi). `-validity 10000` ≈ 27 yil.
- B yo'lida bu **upload kaliti** bo'ladi; app signing kalitini Google o'zi yaratadi (Play Console standarti — shuni tanlang).

Sertifikat barmoq izini yozib oling (bu maxfiy emas, uni e'lon qilish mumkin):

```
keytool -list -v -keystore C:\keys\sv-release.p12 -alias sectorverify
```
→ `SHA256:` qatorini `RELEASE_CHECKLIST.md` ning 4-bo'limiga yozing.

## 2. Zaxira (kalit yaratilgan kuni)

Kalit yo'qolsa: **A yo'lida** ilovani boshqa hech qachon yangilab bo'lmaydi (faqat o'chirib, qayta o'rnatish —
ma'lumot yo'qoladi). **B yo'lida** upload kalitini Play qo'llab-quvvatlash orqali tiklash mumkin, lekin bir necha kun oladi.

| Nima | Qayerda | Nechta |
|---|---|---|
| `sv-release.p12` | shifrlangan USB (BitLocker To Go) + parol menejeri ilovasi (fayl biriktirmasi) | **2 ta**, alohida joyda |
| Parol | parol menejeri; qog'ozda — seyfda | kalit faylidan **alohida** |
| SHA-256 barmoq izi | `RELEASE_CHECKLIST.md` | — |

**Hech qachon:** git (repoda `*.jks`, `*.p12`, `*.keystore`, `keystore.properties` gitignore qilingan — baribir `git status`
bilan tekshiring), e-pochta, Telegram, bulut papkasi (shifrsiz), Claude chati.

## 3. Build'ni kalitga ulash

`sector-verify\keystore.properties` (gitignore qilingan) yarating:

```
storeFile=C:/keys/sv-release.p12
storePassword=<parol>
keyAlias=sectorverify
keyPassword=<o'sha parol>
```

- `storeFile` — **to'liq yo'l**, `/` bilan. Nisbiy yo'l `sector-verify\app\` papkasiga nisbatan hisoblanadi.
- Fayl o'rniga muhit o'zgaruvchilari ham ishlaydi: `SV_KEYSTORE_PATH`, `SV_KEYSTORE_PASSWORD`, `SV_KEY_ALIAS`, `SV_KEY_PASSWORD`.
- Kalit topilmasa build to'xtamaydi, faqat ogohlantiradi va release **imzosiz** chiqadi (`app-release-unsigned.apk`) —
  bu holatda fayl nomidan bilasiz.

## 4. Versiya va tag

`versionName` eng so'nggi `sector-verify/v*` tag'dan, `versionCode` — `HEAD` dagi commitlar sonidan olinadi.

1. Reliz commit'i `master` da, CI yashil. To'liq klon kerak (`git clone` — `--depth` siz), aks holda `versionCode` kichik chiqadi.
2. `CHANGELOG.md` dagi `## [1.0.0] — chiqarilmagan` sarlavhasida "chiqarilmagan" o'rniga reliz sanasini yozing
   (`— YYYY-MM-DD`), bo'lim boshidagi yashirin izohdagi ro'yxatni bajaring (H2 kalibrlashi, H1 natijasi) — alohida PR bilan.
   Bu bo'lim GitHub Release izohiga aylanadi.
3. Tag'ni **build'dan oldin**, aynan shu commit'ga qo'ying:
   ```
   git checkout master && git pull
   git tag sector-verify/v1.0.0
   git push origin sector-verify/v1.0.0
   ```
   Tag'dan keyin commit bo'lsa, versiya `1.0.0-3-gabc1234` ko'rinishida chiqadi — bu reliz emas.
4. Har keyingi reliz: yangi tag (`v1.0.1`, `v1.1.0` ...) — `versionCode` commitlar bilan o'z-o'zidan oshadi.

## 5. Yig'ish

```
cd sector-verify
.\gradlew.bat clean check :app:bundleRelease :app:assembleRelease :app:lintRelease
```

| Natija | Yo'l |
|---|---|
| APK (A) | `app\build\outputs\apk\release\app-release.apk` |
| AAB (B) | `app\build\outputs\bundle\release\app-release.aab` |
| R8 mapping | `app\build\outputs\mapping\release\mapping.txt` |

## 6. Tekshirish

`apksigner` — Android SDK'da (`%LOCALAPPDATA%\Android\Sdk\build-tools\36.0.0\apksigner.bat`):

```
apksigner verify --verbose --print-certs app\build\outputs\apk\release\app-release.apk
```

- `Verified using v3 scheme (APK Signature Scheme v3): true` bo'lsin. minSdk 29 bo'lgani uchun v1 va v2 `false` — bu normal
  (Android 9+ faqat v3 ni o'qiydi, `apksigner` ortiqcha imzo qo'shmaydi).
- `Signer #1 certificate SHA-256 digest` — 1-bo'limda yozgan barmoq izi bilan **aynan bir xil**.
- AAB: `jarsigner -verify -verbose app\build\outputs\bundle\release\app-release.aab` → `jar verified.`
- Versiya: `aapt2 dump badging app-release.apk | findstr "versionName targetSdk"` → `versionName='1.0.0'`, `targetSdkVersion:'36'`.

**Haqiqiy telefonda** (kamida bitta, eng yaxshisi Android 16): APK'ni o'rnating → reja import → qisqa o'lchov →
hisobot → ZIP eksport → kompyuterda `sv-replay verify <zip>` → `OK`.

> `sv-replay verify` tekshiradigan imzo — **boshqa kalit**: har telefon o'zining Keystore'ida yaratgan hisobot kaliti
> (EC P-256). U release kalitiga bog'liq emas va hech qayerga ko'chirilmaydi.

## 7. Arxiv (har reliz uchun)

Papka `releases\1.0.0\` (repodan tashqarida, zaxira qilinadigan joyda):
- `app-release.apk` va/yoki `app-release.aab`;
- `mapping.txt` — crash log'dagi stack trace'ni ochish uchun **majburiy** (busiz R8 nomlari o'qilmaydi);
- `SHA256SUMS.txt`: `certutil -hashfile app-release.apk SHA256` natijasi;
- `CHANGELOG.md` dan shu reliz bo'limi.

## 8. Tarqatish

**A — APK:** ichki fayl serveri yoki MDM orqali. Har relizda APK SHA-256 va sertifikat barmoq izini e'lon qiling,
foydalanuvchilar o'rnatishdan oldin solishtirsin. Telefonda "Noma'lum manbalardan o'rnatish" ruxsati kerak.
Yangilash: shu kalit bilan imzolangan, `versionCode` kattaroq APK eski ilova ustidan o'rnatiladi, ma'lumot saqlanadi.

**B — Play:** Play Console → ilova yaratish → **Play App Signing** (Google boshqaradigan kalit) → **Internal testing**
treki → `app-release.aab` ni yuklang → `docs/PLAY_STORE.md` dagi deklaratsiyalarni to'ldiring → sinovchilar bilan
tekshirgach Production'ga. R8 mapping AAB ichida bor — Play uni crash hisobotlari uchun o'zi oladi.

## 9. Kalit yo'qolsa yoki oshkor bo'lsa

| Holat | A — APK | B — Play |
|---|---|---|
| **Yo'qoldi** (zaxira ham yo'q) | yangilab bo'lmaydi; yangi kalit = yangi ilova (foydalanuvchilar o'chirib, qayta o'rnatadi) | Play Console → upload kalitini tiklash so'rovi (yangi upload kaliti) |
| **Oshkor bo'ldi** | **eski kalit bor bo'lsa**: `apksigner rotate` bilan yangi kalitga o'tish (APK Signature Scheme v3) va yangi relizni yangi kalit bilan imzolash; tarqatish kanalida ogohlantirish | upload kalitini darhol almashtirish (Play qo'llab-quvvatlash); app signing kaliti Google'da, unga ta'sir qilmaydi |

## 10. CI'da imzolash (`sector-verify-release` workflow)

Qo'lda yig'ish (3–7-bo'limlar) o'rniga reliz CI'da imzolanishi mumkin: **tag push qilasiz — qolganini CI qiladi.**

**Ish tartibi** (`.github/workflows/sector-verify-release.yml`, faqat `sector-verify/v*` tag push qilinganda):
1. siz tasdiqlaysiz (environment'ning *Required reviewer* so'rovi);
2. `check` + imzolangan `bundleRelease`, `assembleRelease`, `lintRelease`;
3. `scripts/verify-release.sh` tekshiradi: APK v3 imzo, debug kalit emas, sertifikat SHA-256 = `SV_CERT_SHA256`,
   `versionName` = tag, targetSdk 36; AAB imzo va sertifikat. Bittasi mos kelmasa — reliz chiqmaydi;
4. artefakt (90 kun) va **draft** GitHub Release: `sector-verify-<versiya>.apk`, `.aab`, `mapping-<versiya>.txt`,
   `SHA256SUMS.txt`, izoh — `CHANGELOG.md` dagi shu versiya bo'limi. Draft'ni siz tekshirib **Publish** qilasiz.

**Xavfsizlik:** kalit faqat `sector-verify-release` environment secret'larida — PR'lar, fork'lar va oddiy branch
push'lari unga kira olmaydi. Kalit fayli runner'ning vaqtinchalik papkasida tiklanadi va job oxirida (xato bo'lsa ham)
o'chiriladi; parollar faqat Gradle qadamiga beriladi; Gradle keshi bu job'da o'chiq (parollar kesh yozuvlariga tushmasin).
B yo'lida (Play) CI'ga faqat **upload kaliti** qo'yiladi — app signing kaliti Google'da qoladi.

### Sozlash (bir marta, ~10 daqiqa)
1. GitHub → repo → **Settings → Environments → New environment** → nomi aynan `sector-verify-release`.
2. **Deployment branches and tags** → *Selected branches and tags* → **Add deployment branch or tag rule** →
   *Ref type: Tag* → `sector-verify/v*`.
3. **Required reviewers** → o'zingizni qo'shing (har reliz oldidan "Approve" so'raladi).
4. **Environment secrets** (*Add environment secret*):

   | Nomi | Qiymati |
   |---|---|
   | `SV_KEYSTORE_BASE64` | PowerShell: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\keys\sv-release.p12")) \| Set-Clipboard` → Ctrl+V |
   | `SV_KEYSTORE_PASSWORD` | ombor paroli |
   | `SV_KEY_ALIAS` | `sectorverify` |
   | `SV_KEY_PASSWORD` | o'sha parol (PKCS12) |

5. **Environment variables** (*Add environment variable*): `SV_CERT_SHA256` = 1-bo'limdagi `SHA256:` qiymati
   (`AB:CD:…` ko'rinishida ham bo'ladi). Bu maxfiy emas — u noto'g'ri kalit bilan reliz chiqishidan himoya qiladi.
6. Clipboard tarixini tozalang (Win+V → *Clear all*).

### Har reliz
```
git checkout master && git pull
git tag sector-verify/v1.0.0
git push origin sector-verify/v1.0.0
```
→ GitHub **Actions → sector-verify-release** → *Review deployments* → **Approve** → ~10 daqiqa →
**Releases** → draft → APK'ni yuklab, haqiqiy telefonda sinab (6-bo'lim oxiri) → **Publish release**.
7-bo'limdagi arxiv uchun draft'dagi fayllarni yuklab oling.

| Xato | Sabab |
|---|---|
| `environment'da yo'q: SV_…` | secret/variable nomi xato yoki boshqa environment'ga qo'yilgan |
| `sertifikat SHA-256 mos emas` | boshqa kalit yuklangan yoki `SV_CERT_SHA256` xato |
| `versionName '1.0.0-2-g…' (kutilgan '1.0.0')` | tag reliz commit'ida emas yoki tag'dan keyin commit bor |
| `debug kalit bilan imzolangan` / `v3 imzo yo'q` | kalit build'ga ulanmadi (secret qiymatlari) |

Linux/macOS (yoki WSL) da qo'lda tekshirish uchun ham shu skript:
`./scripts/verify-release.sh app/build/outputs/apk/release/app-release.apk 1.0.0 <SHA256>`.

## 11. H3 tugadi, qachonki

- [ ] Kalit yaratilgan, 2 ta zaxira bor, barmoq izi `RELEASE_CHECKLIST.md` da.
- [ ] `sector-verify/v1.0.0` tag'i reliz commit'ida, GitHub'da.
- [ ] Imzolangan APK/AAB, `apksigner verify` OK, versiya `1.0.0`, targetSdk 36 (yoki CI: `sector-verify-release` yashil, draft Release).
- [ ] Haqiqiy telefonda release: o'lchov → hisobot → `sv-replay verify` OK.
- [ ] Arxiv: APK/AAB, `mapping.txt`, SHA-256.
- [ ] Tarqatildi (A: e'lon + SHA-256; B: Internal testing → Production).
