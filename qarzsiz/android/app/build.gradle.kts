import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
}

// Reliz (upload) kaliti — hech qachon commit qilinmaydi. Manbalar (birinchisi topilgani):
//  1) muhit o'zgaruvchilari: QARZSIZ_KEYSTORE (fayl yo'li), QARZSIZ_STORE_PASSWORD, QARZSIZ_KEY_ALIAS,
//     QARZSIZ_KEY_PASSWORD — CI'da GitHub Secrets'dan;
//  2) android/keystore.properties (storeFile, storePassword, keyAlias, keyPassword) — mahalliy kompyuterda.
// Kalit bo'lmasa: APK debug kaliti bilan imzolanadi (faqat sinov uchun), AAB esa umuman yig'ilmaydi —
// Play Console debug kalitli faylni qabul qilmaydi.
val keystoreProps = Properties().apply {
    val f = rootProject.file("keystore.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

data class UploadKey(val file: File, val storePassword: String, val alias: String, val keyPassword: String)

val uploadKey: UploadKey? = run {
    val env = System.getenv()
    val path = env["QARZSIZ_KEYSTORE"] ?: keystoreProps.getProperty("storeFile")
    val storePass = env["QARZSIZ_STORE_PASSWORD"] ?: keystoreProps.getProperty("storePassword")
    val alias = env["QARZSIZ_KEY_ALIAS"] ?: keystoreProps.getProperty("keyAlias")
    val keyPass = env["QARZSIZ_KEY_PASSWORD"] ?: keystoreProps.getProperty("keyPassword")
    if (path.isNullOrBlank() || storePass.isNullOrBlank() || alias.isNullOrBlank() || keyPass.isNullOrBlank()) {
        null
    } else {
        UploadKey(rootProject.file(path), storePass, alias, keyPass)
    }
}

// Play har yangi yuklashda kattaroq versionCode talab qiladi: -Pqarzsiz.versionCode=N (CI tegdan oladi).
val releaseVersionCode = providers.gradleProperty("qarzsiz.versionCode").orNull?.toInt() ?: 1
val releaseVersionName = providers.gradleProperty("qarzsiz.versionName").orNull ?: "1.0.0"

android {
    namespace = "uz.qarzsiz.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "uz.qarzsiz.app"
        minSdk = 26
        targetSdk = 36
        versionCode = releaseVersionCode
        versionName = releaseVersionName
    }

    // Faqat kerakli tillar resurslari (hajm uchun).
    androidResources {
        localeFilters += listOf("uz", "ru", "en")
    }

    signingConfigs {
        if (uploadKey != null) {
            create("upload") {
                storeFile = uploadKey.file
                storePassword = uploadKey.storePassword
                keyAlias = uploadKey.alias
                keyPassword = uploadKey.keyPassword
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.findByName("upload") ?: signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    testOptions {
        unitTests {
            isIncludeAndroidResources = true
            all {
                // Ekran testlari skrinshotlarni yozadi: app/build/outputs/roborazzi/*.png
                it.systemProperty("roborazzi.test.record", "true")
                it.systemProperty("robolectric.graphicsMode", "NATIVE")
            }
        }
    }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    implementation(project(":core"))

    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-core")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")

    testImplementation("junit:junit:4.13.2")
    // Ekran testlari: haqiqiy Compose ekranlari JVM'da (Robolectric) render qilinadi va skrinshot olinadi.
    testImplementation("org.robolectric:robolectric:4.14.1")
    testImplementation("io.github.takahirom.roborazzi:roborazzi:1.32.2")
    testImplementation("io.github.takahirom.roborazzi:roborazzi-compose:1.32.2")
    testImplementation(composeBom)
    testImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}

// AAB faqat haqiqiy upload kaliti bilan: debug kalitli bundle Play'da rad etiladi.
tasks.matching { it.name == "bundleRelease" }.configureEach {
    doFirst {
        if (uploadKey == null) {
            throw GradleException(
                "bundleRelease uchun upload kaliti kerak: QARZSIZ_KEYSTORE / QARZSIZ_STORE_PASSWORD / " +
                    "QARZSIZ_KEY_ALIAS / QARZSIZ_KEY_PASSWORD yoki android/keystore.properties (qarzsiz/play/RELEASE.md).",
            )
        }
    }
}
