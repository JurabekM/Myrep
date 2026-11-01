import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Reliz imzosi: kalit hech qachon repoga kirmaydi.
// Lokal: `android/key.properties` (namuna: key.properties.example, gitignore'da).
// CI: EPIRADAR_KEYSTORE_FILE, EPIRADAR_KEYSTORE_PASSWORD, EPIRADAR_KEY_ALIAS, EPIRADAR_KEY_PASSWORD.
// EPIRADAR_REQUIRE_RELEASE_SIGNING=1 bo'lsa, kalitsiz release yig'ilmaydi (debug kalit bilan
// imzolangan APK tasodifan tarqatilmasligi uchun).
val keyProps =
    Properties().apply {
        val f = rootProject.file("key.properties")
        if (f.exists()) f.inputStream().use { load(it) }
    }

fun signingValue(
    key: String,
    env: String,
): String? = keyProps.getProperty(key)?.takeIf { it.isNotBlank() } ?: System.getenv(env)?.takeIf { it.isNotBlank() }

val releaseStoreFile = signingValue("storeFile", "EPIRADAR_KEYSTORE_FILE")
val requireReleaseSigning = System.getenv("EPIRADAR_REQUIRE_RELEASE_SIGNING") == "1"

android {
    namespace = "uz.epiradar.app"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "uz.epiradar.app"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        // java.time (yadro) va adaptiv ikonka uchun Android 8.0+.
        minSdk = 26
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildFeatures {
        buildConfig = true
    }

    signingConfigs {
        if (releaseStoreFile != null) {
            create("release") {
                storeFile = rootProject.file(releaseStoreFile)
                storePassword = signingValue("storePassword", "EPIRADAR_KEYSTORE_PASSWORD")
                keyAlias = signingValue("keyAlias", "EPIRADAR_KEY_ALIAS")
                keyPassword = signingValue("keyPassword", "EPIRADAR_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            if (releaseStoreFile == null && requireReleaseSigning) {
                throw GradleException(
                    "Reliz kaliti topilmadi: android/key.properties yoki EPIRADAR_KEYSTORE_FILE kerak (docs/RELEASE.md).",
                )
            }
            // Kalit bo'lmasa — faqat lokal sinov uchun debug kalit (`flutter run --release`).
            signingConfig = signingConfigs.getByName(if (releaseStoreFile != null) "release" else "debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

dependencies {
    implementation("uz.epiradar:epiradar-engine")
    implementation("androidx.core:core-ktx:1.17.0")
    implementation("androidx.work:work-runtime-ktx:2.11.2")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.11.0")

    // Qurilma/emulyator testlari: SyncWorker, bildirishnomalar, vidjet (src/androidTest).
    // Versiyalar Flutter Gradle plagini debug'ga qo'shadigan androidx.test (runner 1.3) bilan mos.
    androidTestImplementation("androidx.test:runner:1.3.0")
    androidTestImplementation("androidx.work:work-testing:2.11.2")
    androidTestImplementation("org.jetbrains.kotlin:kotlin-test-junit:2.4.0")
}
