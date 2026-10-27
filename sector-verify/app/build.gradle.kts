import java.util.Properties

plugins {
    alias(libs.plugins.sv.android.application)
    alias(libs.plugins.sv.android.compose)
    alias(libs.plugins.sv.android.hilt)
}

// §5 versiyalash: versionName — eng so'nggi `sector-verify/v*` tag'dan, versionCode = commitlar soni.
fun git(vararg args: String): String? = runCatching {
    providers.exec {
        commandLine("git", *args)
        isIgnoreExitValue = true
    }.standardOutput.asText.get().trim().ifEmpty { null }
}.getOrNull()

val svVersionCode = git("rev-list", "--count", "HEAD")?.toIntOrNull() ?: 1
val svVersionName = git("describe", "--tags", "--match", "sector-verify/v*")?.removePrefix("sector-verify/v") ?: "0.0.0-dev"

// §5 imzolash: keystore.properties (git-ignored) yoki SV_KEYSTORE_* muhit o'zgaruvchilari. Hech narsa commit qilinmaydi.
val keystoreProps = rootProject.file("keystore.properties").takeIf {
    it.exists()
}?.let { f -> Properties().apply { f.inputStream().use(::load) } }

fun secret(key: String, env: String): String? = keystoreProps?.getProperty(key) ?: System.getenv(env)

val releaseStore = secret("storeFile", "SV_KEYSTORE_PATH")
val releaseStorePassword = secret("storePassword", "SV_KEYSTORE_PASSWORD")
val releaseAlias = secret("keyAlias", "SV_KEY_ALIAS")
val releaseKeyPassword = secret("keyPassword", "SV_KEY_PASSWORD")
val hasReleaseKey = listOf(releaseStore, releaseStorePassword, releaseAlias, releaseKeyPassword).all { !it.isNullOrBlank() }

android {
    namespace = "uz.sectorverify.app"
    defaultConfig {
        applicationId = "uz.sectorverify"
        versionCode = svVersionCode
        versionName = svVersionName
    }
    buildFeatures.buildConfig = true
    // Ilova ichida til almashtirish (uz/ru/en) uchun barcha tillar Play til split'larida emas, asosiy APK da bo'lishi kerak.
    bundle {
        language { enableSplit = false }
    }
    signingConfigs {
        if (hasReleaseKey) {
            create("release") {
                storeFile = file(releaseStore!!)
                storePassword = releaseStorePassword
                keyAlias = releaseAlias
                keyPassword = releaseKeyPassword
                enableV2Signing = true
                enableV3Signing = true
            }
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = when {
                hasReleaseKey -> signingConfigs.getByName("release")
                // Faqat CI smoke testi uchun: debug kalit bilan imzolangan, o'rnatiladigan release build.
                providers.gradleProperty("sv.signWithDebug").isPresent -> signingConfigs.getByName("debug")
                else -> null
            }
        }
    }
}

if (!hasReleaseKey) {
    logger.warn("sector-verify: release imzo kaliti topilmadi (keystore.properties / SV_KEYSTORE_*) — release imzosiz yig'iladi.")
}

dependencies {
    implementation(project(":core:ui"))
    implementation(project(":core:data"))
    implementation(project(":feature:plan"))
    implementation(project(":feature:survey"))
    implementation(project(":feature:report"))
    implementation(project(":feature:settings"))
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.hilt.navigation.compose)
    testImplementation(project(":core:analysis"))
    testImplementation(project(":core:telephony"))
    testImplementation(libs.hilt.android.testing)
    kspTest(libs.hilt.compiler)
}
