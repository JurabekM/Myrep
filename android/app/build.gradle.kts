import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    id("org.jetbrains.kotlin.plugin.compose")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Release imzosi repodan TASHQARIDA (MVP_PLAN Vazifa 15): fayl yo'li
// `BARAKA_SIGNING_PROPERTIES` muhit o'zgaruvchisi yoki `-PsigningProperties=`
// bilan beriladi (standart — gitignore qilingan `android/key.properties`).
// Kalitlar: storeFile, storePassword, keyAlias, keyPassword. Fayl bo'lmasa
// release debug kaliti bilan imzolanadi (faqat sinov uchun, Play'ga emas).
val signingPropertiesFile: File = (
    System.getenv("BARAKA_SIGNING_PROPERTIES")
        ?: project.findProperty("signingProperties") as String?
)?.let { File(it) } ?: rootProject.file("key.properties")
// Demo yig'ish (`tools/build_demo.ps1`, `-Pbaraka.demo=true`): alohida paket
// nomi va doim debug imzo — Google Play bunday faylni qabul qilmaydi, haqiqiy
// ilova o'rnini egallay olmaydi.
val isDemo = (project.findProperty("baraka.demo") as String?) == "true"
val signingProperties = Properties().apply {
    if (signingPropertiesFile.isFile) signingPropertiesFile.inputStream().use { load(it) }
}
val hasReleaseSigning = listOf("storeFile", "storePassword", "keyAlias", "keyPassword")
    .all { !signingProperties.getProperty(it).isNullOrBlank() }

android {
    namespace = "uz.barakadaftari.app"
    // Flutter 3.32 standarti 35; Google Play 2026-08-31 dan targetSdk 36 talab qiladi.
    compileSdk = 36
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        // Play identifikatori: birinchi yuklashdan keyin o'zgartirib bo'lmaydi.
        // namespace (Kotlin paketi) ichki — o'zgartirilmagan.
        applicationId = if (isDemo) "uz.barakadastur.demo" else "uz.barakadastur.app"
        manifestPlaceholders["appLabel"] = if (isDemo) "DEMO Baraka Dastur" else "Baraka Dastur"
        // SPEC 4.1: minSdk 26.
        minSdk = 26
        // Android 16: predictive back va katta ekranda yo'nalish cheklovlari
        // e'tiborsiz (ilovada yo'nalish qulfi yo'q) — RELEASE_CHECKLIST 18.
        targetSdk = 36
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        // Release imzosining SHA-256 xeshi (`-PexpectedSignatureSha256=...`).
        // Bo'sh bo'lsa imzo tekshiruvi «sozlanmagan» deb qaytadi.
        val expectedSignature = (project.findProperty("expectedSignatureSha256") as String?).orEmpty()
        buildConfigField("String", "EXPECTED_SIGNATURE_SHA256", "\"$expectedSignature\"")
    }

    buildFeatures {
        buildConfig = true
        // Glance vidjeti (MVP_PLAN Vazifa 7).
        compose = true
    }

    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                storeFile = File(signingProperties.getProperty("storeFile"))
                storePassword = signingProperties.getProperty("storePassword")
                keyAlias = signingProperties.getProperty("keyAlias")
                keyPassword = signingProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName(
                if (hasReleaseSigning && !isDemo) "release" else "debug",
            )
            // R8: kod qisqartiriladi va obfuskatsiya qilinadi, ishlatilmagan
            // resurslar olib tashlanadi.
            isMinifyEnabled = true
            isShrinkResources = true
            // Release log siyosati: android.util.Log d/v/i chaqiruvlari olib tashlanadi.
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    testOptions {
        unitTests.isReturnDefaultValues = true
    }
}

dependencies {
    // BiometricPrompt (SPEC 4.1: androidx.biometric).
    implementation("androidx.biometric:biometric:1.1.0")
    // Majburiyat eslatmalari (SPEC 4.1: WorkManager + bildirishnomalar).
    implementation("androidx.work:work-runtime-ktx:2.9.1")
    // Bosh ekran vidjeti (MVP_PLAN Vazifa 7: Jetpack Glance).
    implementation("androidx.glance:glance-appwidget:1.1.1")
    testImplementation("junit:junit:4.13.2")
}

flutter {
    source = "../.."
}
