import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// F4: reliz imzosi. Kalit fayli repodan TASHQARIDA (tools/create_upload_key.ps1 yaratadi,
// standart C:\keys\rostor2\upload\key.properties). Yo'l `ROSTOR2_SIGNING_PROPERTIES` muhit
// o'zgaruvchisi yoki `-PsigningProperties=` bilan beriladi. Fayl bo'lmasa reliz debug kaliti
// bilan imzolanadi — bunday APK faqat sinov uchun, tools/check_release.py uni rad etadi.
val signingPropertiesFile: File? = (
    System.getenv("ROSTOR2_SIGNING_PROPERTIES") ?: project.findProperty("signingProperties") as String?
)?.let { File(it) }
val signingProperties = Properties().apply {
    signingPropertiesFile?.takeIf { it.isFile }?.inputStream()?.use { load(it) }
}
val hasReleaseSigning = listOf("storeFile", "storePassword", "keyAlias", "keyPassword")
    .all { !signingProperties.getProperty(it).isNullOrBlank() }

// "ROSTOR-2 haqiqiymi?" ekrani o'z imzosini shu xesh bilan solishtiradi (Q3). Play orqali
// tarqatilganda — Play Console'dagi "App signing key" SHA-256, to'g'ridan-to'g'ri APK uchun —
// upload kaliti xeshi. Berilmasa ekran faqat izni ko'rsatadi.
val expectedSignatureSha256: String =
    (project.findProperty("expectedSignatureSha256") as String?)?.replace(":", "")?.uppercase() ?: ""
require(expectedSignatureSha256.isEmpty() || Regex("[0-9A-F]{64}").matches(expectedSignatureSha256)) {
    "expectedSignatureSha256 SHA-256 emas: $expectedSignatureSha256"
}

android {
    namespace = "uz.rostor.rostor2"
    compileSdk = 36
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    buildFeatures {
        buildConfig = true
    }

    defaultConfig {
        applicationId = "uz.rostor.rostor2"
        // 26: PackageManager.getChangedPackages(); 28+ da SigningInfo, past versiyada GET_SIGNATURES.
        minSdk = 26
        targetSdk = 36
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        buildConfigField("String", "EXPECTED_SIGNATURE_SHA256", "\"$expectedSignatureSha256\"")
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
            signingConfig = signingConfigs.getByName(if (hasReleaseSigning) "release" else "debug")
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    packaging {
        resources {
            excludes += setOf("META-INF/versions/9/OSGI-INF/MANIFEST.MF", "META-INF/*.kotlin_module")
        }
    }

    testOptions {
        unitTests.isReturnDefaultValues = true
    }
}

dependencies {
    // APK Signature Scheme v1-v4 tekshiruvi (Google'ning rasmiy kutubxonasi, apksigner shu ustida).
    implementation("com.android.tools.build:apksig:8.7.3")
    // Ed25519 + ML-DSA-65 (FIPS 204) — faqat lightweight API, JCA provayderisiz.
    implementation("org.bouncycastle:bcprov-jdk18on:1.81")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}

flutter {
    source = "../.."
}
