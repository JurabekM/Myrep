plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "uz.mpay.walletdemo"
    compileSdk = 36

    defaultConfig {
        applicationId = "uz.mpay.walletdemo"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0-m6"
        buildConfigField("String", "DEFAULT_SERVER", "\"http://10.0.2.2:8080\"")
        // 1-faza P1.5: server ishonchi build vaqtida (`-Pmpay.serverFingerprints=…`, `-Pmpay.tlsPin=…`,
        // qiymatlar `mpay-server identity` chiqishidan). Bo'sh bo'lsa — TOFU, faqat sandbox.
        val fingerprints = (project.findProperty("mpay.serverFingerprints") as String?).orEmpty()
        val tlsPin = (project.findProperty("mpay.tlsPin") as String?).orEmpty()
        require(Regex("[0-9a-fA-F,; ]*").matches(fingerprints) && Regex("[0-9a-fA-F]*").matches(tlsPin)) {
            "mpay.serverFingerprints / mpay.tlsPin faqat hex bo'lishi kerak"
        }
        buildConfigField("String", "SERVER_FINGERPRINTS", "\"$fingerprints\"")
        buildConfigField("String", "TLS_PIN", "\"$tlsPin\"")
        // ADR-0014: oflayn ildiz barmoq izi (`mpay-server root-keygen`); bo'sh — ro'yxat tekshirilmaydi.
        val rootFp = (project.findProperty("mpay.rootFingerprint") as String?).orEmpty()
        require(Regex("([0-9a-fA-F]{64})?").matches(rootFp)) { "mpay.rootFingerprint 64 hex bo'lishi kerak" }
        buildConfigField("String", "ROOT_FINGERPRINT", "\"$rootFp\"")
        // ADR-0029: mustaqil kanal (CDN) manzillari, vergul bilan — faqat https://.
        val revocationUrls = (project.findProperty("mpay.revocationUrls") as String?).orEmpty()
        require(revocationUrls.split(',').map { it.trim() }.filter { it.isNotEmpty() }.all {
            it.startsWith("https://") && it.none { ch -> ch == '"' || ch == '\\' || ch.isWhitespace() }
        }) { "mpay.revocationUrls: vergul bilan ajratilgan https:// manzillar" }
        buildConfigField("String", "REVOCATION_URLS", "\"$revocationUrls\"")
    }

    // ADR-0029: imzolangan bekor qilish ro'yxati build'ga joylanadi (`-Pmpay.revocationsFile=…`,
    // `mpay-server revoke` natijasi) — asset `mpay-revocations.json`. Ildiz imzosi ilovada tekshiriladi.
    sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/mpay-assets"))

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
            // Sandbox: release ham debug kaliti bilan imzolanadi (haqiqiy kalit repoga tushmaydi).
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    packaging {
        resources.excludes += setOf("META-INF/versions/9/OSGI-INF/MANIFEST.MF", "META-INF/DEPENDENCIES")
    }
}

kotlin {
    compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) }
}

// ADR-0029: berilgan ro'yxat fayli (bo'lmasa — papka bo'sh, asset yo'q) build'dan oldin nusxalanadi.
val revocationsFile = (project.findProperty("mpay.revocationsFile") as String?)?.takeIf { it.isNotBlank() }?.let(::file)
require(revocationsFile == null || revocationsFile.isFile) { "mpay.revocationsFile topilmadi: $revocationsFile" }
val bundleRevocations by tasks.registering(Sync::class) {
    into(layout.buildDirectory.dir("generated/mpay-assets"))
    if (revocationsFile != null) from(revocationsFile) { rename { "mpay-revocations.json" } }
}
tasks.named("preBuild") { dependsOn(bundleRevocations) }

dependencies {
    implementation(project(":wallet-sdk"))
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.coroutines.android)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
}
