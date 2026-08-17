# 11-bosqich — Deployment

## 1. Lokal/staging muhitni ko'tarish (Docker Compose)

Talab: Docker Desktop (yoki docker engine + compose plugin).

```bash
cd smart_moliya
docker compose -f infra/docker-compose.yml up --build
```

Nima ishga tushadi:

| Servis | Port | Izoh |
|---|---|---|
| nginx | **8080** (host) | Yagona kirish nuqtasi: `/api/*` → backend, `/ai/*` → AI service, rate-limit 20 req/s |
| backend | 8000 (ichki) | Ishga tushishda `alembic upgrade head` avtomatik bajariladi |
| ai_service | 8100 (ichki) | CPU-only PyTorch (image ~1.5GB) |
| admin_panel | **8081** (host) | Boshqaruv paneli (login: ADMIN_USERNAME/ADMIN_PASSWORD env) — ichki vosita, nginx orqali ochilmaydi |
| postgres | 5432 (ichki) | `postgres_data` volume'da saqlanadi, healthcheck bilan |
| redis | 6379 (ichki) | Cache/session/rate-limit uchun tayyor |

Tekshirish:

```bash
curl http://localhost:8080/health          # backend
curl http://localhost:8080/ai/health       # AI service
# Swagger: http://localhost:8080/docs
```

Muhit o'zgaruvchilari (`.env` fayl yoki export orqali):

```
POSTGRES_PASSWORD=kuchli-parol
JWT_SECRET_KEY=juda-uzun-tasodifiy-satr        # production'da MAJBURIY almashtirilsin
ADMIN_USERNAME=boshqa-admin-login              # standart: admin
ADMIN_PASSWORD=kuchli-admin-parol              # standart: admin123 - MAJBURIY almashtirilsin
ADMIN_SECRET_KEY=admin-sessiya-kaliti
ENVIRONMENT=production
```

## 2. Android'ni staging/production serverga ulash

`android/.../core/network/NetworkModule.kt` dagi `BASE_URL`:
- Emulyator + lokal docker: `http://10.0.2.2:8080/`
- Jismoniy qurilma (bir Wi-Fi): `http://<kompyuter-IP>:8080/`
- Production: `https://api.smartmoliya.uz/` (haqiqiy domen + TLS)

Production'da `nginx.conf`ga TLS sertifikati (Let's Encrypt/certbot) va mobil ilovaga certificate pinning qo'shiladi.

## 3. CI/CD (GitHub Actions)

`.github/workflows/ci.yml` — har push/PR da 4 ta job:

1. **backend-tests** — 41 pytest + coverage artifact
2. **ai-service-tests** — 15 pytest (CPU-only torch)
3. **android-build** — unit testlar + debug APK build, APK artifact sifatida yuklanadi
4. **docker-images** — ikkala Docker image build + smoke test (testlar o'tgandan keyingina)

CD (avtomatik deploy) hozircha qo'shilmagan — server manzili/registry tanlovi aniqlanganda `docker push` + SSH deploy step qo'shiladi.

## 4. Release APK build (Google Play uchun)

### 4.1. Imzolash kaliti yaratish (bir marta)

```bash
keytool -genkeypair -v -keystore smart-moliya-release.keystore \
  -alias smartmoliya -keyalg RSA -keysize 2048 -validity 10000
```

Keystore faylni **hech qachon** git'ga qo'shmang.

### 4.2. `android/keystore.properties` (git'dan tashqarida)

```properties
storeFile=../smart-moliya-release.keystore
storePassword=***
keyAlias=smartmoliya
keyPassword=***
```

### 4.3. `app/build.gradle.kts` ga signing config qo'shish

```kotlin
// android { } blokiga:
signingConfigs {
    create("release") {
        val props = java.util.Properties()
        val propsFile = rootProject.file("keystore.properties")
        if (propsFile.exists()) {
            props.load(propsFile.inputStream())
            storeFile = file(props["storeFile"] as String)
            storePassword = props["storePassword"] as String
            keyAlias = props["keyAlias"] as String
            keyPassword = props["keyPassword"] as String
        }
    }
}
buildTypes {
    release {
        signingConfig = signingConfigs.getByName("release")
        // ... mavjud minifyEnabled/proguard sozlamalari
    }
}
```

### 4.4. Build

```bash
cd android
./gradlew assembleRelease        # APK: app/build/outputs/apk/release/
./gradlew bundleRelease          # AAB (Google Play talabi): app/build/outputs/bundle/release/
```

Google Play Console'ga `.aab` yuklanadi. Play talablari uchun tekshirish ro'yxati:
- `targetSdk 35` ✅ (allaqachon sozlangan)
- Privacy Policy URL (moliyaviy ma'lumot bilan ishlagani uchun majburiy)
- Data safety formasi: qanday ma'lumot yig'ilishi (telefon raqami, moliyaviy tranzaksiyalar) deklaratsiya qilinishi kerak
- Release build'da HTTP loglar avtomatik o'chadi (`BuildConfig.DEBUG` sharti bilan) ✅

## 5. Certificate pinning'ni yoqish (production)

1. Server sertifikatining SPKI SHA-256 pin'ini oling:

```bash
openssl s_client -connect api.smartmoliya.uz:443 -servername api.smartmoliya.uz \
  | openssl x509 -pubkey -noout | openssl pkey -pubin -outform der \
  | openssl dgst -sha256 -binary | openssl enc -base64
```

2. `android/app/build.gradle.kts` da to'ldiring:

```kotlin
buildConfigField("String", "API_BASE_URL", "\"https://api.smartmoliya.uz/\"")
buildConfigField("String", "CERT_PIN_HOST", "\"api.smartmoliya.uz\"")
buildConfigField("String", "CERT_PIN_SHA256", "\"sha256/<olingan-pin>\"")
```

3. Manifest'dan `android:usesCleartextTraffic="true"` ni olib tashlang va rebuild qiling.

Muhim: sertifikat yangilanganda pin ham yangilanishi kerak — zaxira (backup) pin qo'shish tavsiya etiladi (`buildCertificatePinner`ga ikkinchi `.add()` qatori).

## 6. Keyingi ishlar (production'gacha qolgan)

- Real SMS provayder (Eskiz.uz adapteri — `SmsSender` interfeysi tayyor) va real Google client ID kiritish
- OTP store'ni Redis'ga ko'chirish (ko'p instance uchun; hozir in-memory)
- CD pipeline (registry + deploy target tanlanganda)
- Backend integratsion testlar (haqiqiy Postgres bilan, docker-compose test profili)
