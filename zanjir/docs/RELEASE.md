# ZANJIR — Release (Android, Play internal testing)

> 12-faza (ADR-0016). Release imzo kalitini (keystore) **foydalanuvchi** yaratadi va saqlaydi (🛑 3-darvoza), Play
> Console'ga yuklashni ham foydalanuvchi bajaradi. Bu hujjat va skriptlar — tayyorgarlik va tekshiruv.

## Versiyalash

- `app/pubspec.yaml` → `version: X.Y.Z+N`. `X.Y.Z` — foydalanuvchiga ko'rinadigan versiya (SemVer: X — ma'lumot formati
  yoki server bilan mos kelmaydigan o'zgarish, Y — yangi imkoniyat, Z — tuzatish); `N` — `versionCode`, har yuklashda
  **qat'iy oshadi** (Play bir xil yoki kichigini qabul qilmaydi), hech qachon qayta ishlatilmaydi.
- Git teg: `zanjir-vX.Y.Z` (release skripti teg va pubspec mosligini tekshiradi). `CHANGELOG.md`: `[Unreleased]` →
  `[X.Y.Z] — sana`.
- Ilova va server mosligi: sinxron sim formati (`tools/vectors/sync_schema.json`) o'zgarsa — server avval yangilanadi
  (eski ilova bilan ishlashi shart), ilova keyin. Birinchi pilot: ilova `0.1.0+1`, server `0.1.0`.

## Imzo kaliti (🛑 3-darvoza — foydalanuvchi)

Play App Signing tavsiya etiladi: ilovani Google'ning **ilova imzo kaliti** imzolaydi, siz faqat **upload kaliti** bilan
yuklaysiz (yo'qolsa — Play orqali almashtiriladi; ilova kaliti yo'qolmaydi).

```
keytool -genkeypair -v -keystore zanjir-upload.jks -storetype PKCS12 -alias zanjir-upload \
  -keyalg RSA -keysize 4096 -validity 10000
```

- Keystore va parollar: parol menejeri + shifrlangan zaxira nusxa (ikki joyda). Repo, chat, e-pochtaga **qo'yilmaydi**.
- `app/android/key.properties` (namuna — `key.properties.example`, `.gitignore` da):
  `storeFile=/to'liq/yo'l/zanjir-upload.jks`, `storePassword`, `keyAlias=zanjir-upload`, `keyPassword`.
- Kalitsiz release build ataylab yiqiladi (debug kalit bilan imzolanmaydi, F-02).
- Sertifikat barmoq izi (Play Console bilan solishtirish uchun):
  `keytool -list -v -keystore zanjir-upload.jks -alias zanjir-upload | grep SHA256`.

## Build

```
ZANJIR_SERVER_URL=https://<domen>/ app/tool/build_release.sh
```

Skript to'xtaydi, agar: kalit yo'q; git daraxti toza emas; teg va versiya mos emas; **normalar release darvozasi**
o'tmasa (`reviewed_by`/`reviewed_at` bo'sh yoki `needs_verification` normalar bor — 1-darvoza); analyze/testlar yiqilsa;
server manzili https emas. Chetlab o'tish parametri yo'q.

Natija `app/build/release/X.Y.Z+N/`:

| Fayl | Nima uchun |
|---|---|
| `zanjir-X.Y.Z+N.aab` | Play Console'ga yuklanadi |
| `mapping.txt` | R8 (Java/Kotlin) — Play Console'ga "Deobfuscation file" sifatida |
| `dart-symbols-X.Y.Z+N.tar.gz` | Dart obfuskatsiya simbollari — xato izlarini o'qish (`flutter symbolize`); **maxfiy**, repoga emas |
| `report.txt` | AAB tekshiruvi: imzo, manifest, SDK, ruxsatlar, versiya |
| `release-info.txt` | git commit, Flutter versiyasi, server, SHA-256 |

Texnik tekshiruv (kalitsiz, har o'zgarishda; CI `zanjir-release-check`): `app/tool/build_check.sh` — bir martalik kalit
bilan imzolangan AAB, **tarqatilmaydi**.

## AAB tekshiruvi (`app/tool/verify_aab.sh`)

- imzo to'g'ri (`jarsigner -verify`), debug sertifikat emas;
- `applicationId = uz.zanjir.app`, `minSdk 24`, `targetSdk 36`, `versionCode`/`versionName` = pubspec;
- `debuggable` yo'q, `allowBackup=false`, `usesCleartextTraffic=false`, `networkSecurityConfig` bor;
- ruxsatlar faqat ruxsat etilgan ro'yxatdan (`INTERNET` va kutubxonalarning zararsiz ruxsatlari) — kamera, joylashuv,
  kontaktlar, SMS, xotira **yo'q**;
- R8 mapping va Dart obfuskatsiyasi (AAB ichida Dart sinf nomlari ochiq ko'rinmaydi).

## Release checklist

Har release'dan oldin (natija `release-info.txt` bilan birga saqlanadi):

- [ ] 🛑 1-darvoza: `docs/NORMS_REVIEW.md` — litsenziyali muhandis imzolagan; `norms/v0.yaml` da `reviewed_by`,
      `reviewed_at`; `needs_verification` normalar yo'q (build skripti tekshiradi)
- [ ] CI yashil: core (100% coverage), protocol, data, app, server (≥ 95%), E2E, normalar, OSV auditi, deploy (staging)
- [ ] `CHANGELOG.md` va `pubspec.yaml` versiyasi; `versionCode` oldingisidan katta
- [ ] Server shu versiyaga mos va yangilangan (`RUNBOOK.md` → Yangilash), zaxira olingan
- [ ] `ZANJIR_SERVER_URL` — prod domeni (https), `/v/<token>` sahifasi ochiladi
- [ ] `build_release.sh` muvaffaqiyatli; `report.txt` da hamma band ✅; upload sertifikati barmoq izi Play bilan bir xil
- [ ] Haqiqiy Android qurilmada (Android 7 va 14+): o'rnatish, oflayn profil, o'lchov, sessiya yopish, protokol
      (1-darvozadan keyin), QR havola, sinxronlash, katta shrift, TalkBack, imzolash ekranida ekranshot taqiqlangan
- [ ] Play Console: "App content" (maxfiylik siyosati, Data safety, kontent reytingi, maqsadli auditoriya) —
      `docs/PLAY_LISTING.md`
- [ ] Internal testing: testerlar ro'yxati (pilot laboratoriyalar), "What's new" (uz/ru)
- [ ] `mapping.txt` Play'ga yuklandi; Dart simbollari maxfiy arxivda
- [ ] Git teg `zanjir-vX.Y.Z` push qilindi

## Play internal testing (foydalanuvchi)

1. Play Console → ilova yaratish: nomi «ZANJIR», standart til — o'zbek (lotin), bepul, ilova (o'yin emas).
2. Play App Signing — yoqilgan (standart); birinchi yuklashda upload kaliti sertifikati qayd etiladi.
3. App content — `docs/PLAY_LISTING.md` dagi javoblar; maxfiylik siyosati — `docs/PRIVACY.md` (huquqshunos tekshiradi)
   domenda (`https://<domen>/privacy`) yoki boshqa ochiq manzilda joylashtiriladi.
4. Testing → Internal testing → testerlar (e-pochta ro'yxati) → yangi release → AAB + mapping → "What's new" → rollout.
5. Testerlarga havola va `docs/PILOT.md` yo'riqnomasi yuboriladi.
