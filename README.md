# Baraka Dastur

O'zbekiston o'rta qatlami uchun ribosiz shaxsiy moliya Android ilovasi (Flutter + Kotlin).
To'liq spetsifikatsiya: [docs/SPEC.md](docs/SPEC.md). MVP-1 vazifalari: [docs/MVP1_KICKOFF.md](docs/MVP1_KICKOFF.md).

## Tuzilma

```
lib/
  app/        router, theme, l10n, settings, bootstrap
  core/       money, time, ids, errors, result, security (Pigeon ko'prigi)
  features/   income, vault, expenses, obligations, audit, content, home, lock
              └─ presentation / domain / data
pigeons/      Pigeon kontraktlari (Flutter ↔ Kotlin)
android/app/src/main/kotlin/uz/barakadaftari/app/native/   Kotlin host implementatsiyalari
tools/        ikonka generatori, emulyator skriptlari
```

## Ishga tushirish

Talablar: Flutter versiyasi `.fvmrc` da (3.32.5), JDK 21.

```
flutter pub get
flutter run
```

Boshqa buyruqlar va qoidalar: [CLAUDE.md](CLAUDE.md).

Ikonka: `python tools/make_icon.py` (Pillow) — daftar sahifasi va qizil qopcha («Kelajagim»).
