# CLAUDE.md — HavoRadar

Myrep ildizidagi `CLAUDE.md` (dark UI, til, Codex ishlatilmaydi) ham amal qiladi. Umumiy ko'rinish: `README.md`.
Arxitektura EpiRadar bilan bir xil (`../epiradar`): o'xshash muammo bo'lsa, avval u yerdagi yechimga qarang.

## Arxitektura qoidalari
- Barcha hisob-kitob, ball va matn (o'zbekcha sabablar, tavsiyalar, darajalar) **Kotlin yadroda** (`engine/`).
  Flutter (`lib/`) faqat ko'rsatadi.
- `engine/` — sof Kotlin/JVM: Android importi taqiqlangan; `java.time` faqat API 26 da bor metodlar.
- Flutter ↔ Kotlin: `MethodChannel("uz.havoradar/engine")`, JSON matn. Format o'zgarsa: `json/Codec.kt`,
  `lib/data/models.dart` va `HAVORADAR_EXPORT=../test/fixtures ./gradlew test --tests '*CodecTest*' --rerun-tasks`
  (CI fixture'lar yadro chiqishiga mosligini tekshiradi).
- Tashqi Dart paketi qo'shilmaydi (tarmoq, saqlash, bildirishnoma — Kotlin tomonda).
- Ball chegaralari faqat rasmiy hujjatlardan (NWS, JSST AQG 2021, EPA AQI, WMO ETCCDI); har biri kodda va
  README jadvalida manbasi bilan. Yangi chegara — test bilan.
- Tibbiy matnlar (`guide.json`, `Heat.kt`/`Air.kt` tavsiyalari) faqat CDC/NIOSH/JSST/EPA matnlariga asoslanadi,
  har bir bo'limda manba havolasi bo'lishi shart (`Guide.parse` tekshiradi). Noaniq raqam yozilmaydi.
- GPS ishlatilmaydi: joylar `places.tsv` dan.

## Tekshiruv buyruqlari
- `cd engine && ./gradlew test` (bulut sessiyasida Maven Central 429 → GCS ko'zgu init-skripti:
  `maven-central.storage-download.googleapis.com/maven2/` ni `--init-script` bilan birinchi repo qilish)
- `flutter analyze && TZ=Asia/Tashkent flutter test` (Flutter 3.47.6)
- `flutter build apk --release --split-per-abi`
- Emulyator: `./tool/emulator_test.sh` (emulyator ishga tushgan bo'lsin; jonli Open-Meteo 429 bersa, jonli qism
  o'tkazib yuboriladi)
- Reliz: `havoradar-v<versiya>` tegi → `.github/workflows/havoradar-release.yml` (docs/RELEASE.md)
- Jonli: `HAVORADAR_LIVE=1 ./gradlew test --tests '*LiveSmokeTest*' -i` (bulut IP'sidan api.open-meteo.com
  kunlik limitga tushishi mumkin — HTTP 429)
