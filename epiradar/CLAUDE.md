# CLAUDE.md — EpiRadar

Myrep ildizidagi `CLAUDE.md` (dark UI, til, Codex ishlatilmaydi) ham amal qiladi. Umumiy ko'rinish: `README.md`.

## Arxitektura qoidalari
- Barcha tahlil, ball va matn (o'zbekcha sabablar, darajalar) **Kotlin yadroda** (`engine/`). Flutter (`lib/`) faqat ko'rsatadi.
- `engine/` — sof Kotlin/JVM: Android importi taqiqlangan; `java.time` faqat API 26 da bor metodlar
  (`LocalDate.ofInstant` kabi Java 9+ metodlar EMAS — `instant.atZone(ZoneOffset.UTC).toLocalDate()`).
- Flutter ↔ Kotlin: `MethodChannel("uz.epiradar/engine")`, JSON matn. Format o'zgarsa: `json/Codec.kt`,
  `lib/data/models.dart` va `EPIRADAR_EXPORT=../test/fixtures gradle test --rerun-tasks` bilan fixture'lar.
- Tashqi Dart paketi qo'shilmaydi (tarmoq, saqlash, bildirishnoma — Kotlin tomonda).
- Faqat rasmiy manbalar (WHO, ECDC, CDC, FluNet). Yangi manba — `SignalSource` + fixture + test.
- Tibbiy matnlar (`diseases.json`) faqat JSST/CDC faktlariga asoslanadi; noaniq raqam yozilmaydi.

## Tekshiruv buyruqlari
- `cd engine && gradle test` (Gradle 9.3.1; bulut sessiyasida Maven Central 429 → scratchpad'dagi GCS ko'zgu init-skripti)
- `flutter analyze && TZ=Asia/Tashkent flutter test` (Flutter 3.47.6)
- `flutter build apk --release --split-per-abi`
- Jonli: `EPIRADAR_LIVE=1 gradle test --tests '*LiveSmokeTest*' -i`
