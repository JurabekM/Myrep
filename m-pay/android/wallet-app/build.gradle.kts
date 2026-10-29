plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

/** `-Pmpay.<nom>=…` qiymati (bo'lmasa — bo'sh satr). */
fun prop(name: String): String = (project.findProperty("mpay.$name") as String?).orEmpty().trim()

android {
    namespace = "uz.mpay.wallet.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "uz.mpay.wallet"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"

        // Server manzili build vaqtida (`-Pmpay.server=https://…`); bo'sh — emulyator sandbox'i.
        val server = prop("server").ifEmpty { "http://10.0.2.2:8080" }
        require(Regex("https?://[A-Za-z0-9.:\\-\\[\\]]+").matches(server)) { "mpay.server: http(s)://host[:port]" }
        buildConfigField("String", "SERVER", "\"$server\"")
        // Server ishonchi (P1.5): PQ Link barmoq izlari va TLS pini — `mpay-server identity` chiqishidan.
        val fingerprints = prop("serverFingerprints")
        val tlsPin = prop("tlsPin")
        require(Regex("[0-9a-fA-F,; ]*").matches(fingerprints) && Regex("[0-9a-fA-F]*").matches(tlsPin)) {
            "mpay.serverFingerprints / mpay.tlsPin faqat hex bo'lishi kerak"
        }
        buildConfigField("String", "SERVER_FINGERPRINTS", "\"$fingerprints\"")
        buildConfigField("String", "TLS_PIN", "\"$tlsPin\"")
        // ADR-0014/0029: oflayn ildiz va mustaqil kanallar.
        val rootFp = prop("rootFingerprint")
        require(Regex("([0-9a-fA-F]{64})?").matches(rootFp)) { "mpay.rootFingerprint 64 hex bo'lishi kerak" }
        buildConfigField("String", "ROOT_FINGERPRINT", "\"$rootFp\"")
        val revocationUrls = prop("revocationUrls")
        require(revocationUrls.split(',').map { it.trim() }.filter { it.isNotEmpty() }.all {
            it.startsWith("https://") && it.none { ch -> ch == '"' || ch == '\\' || ch.isWhitespace() }
        }) { "mpay.revocationUrls: vergul bilan ajratilgan https:// manzillar" }
        buildConfigField("String", "REVOCATION_URLS", "\"$revocationUrls\"")
        // Sandbox: ilova yaxlitligi server mock'idan (real Play Integrity — MB-4). `-Pmpay.sandbox=false` — production.
        buildConfigField("boolean", "SANDBOX", (prop("sandbox") != "false").toString())
    }

    sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/mpay-assets"))

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            // Haqiqiy imzo kaliti repoga tushmaydi (MB-3): `-Pmpay.keystore=…` berilmasa — debug kaliti (sandbox).
            val ks = prop("keystore")
            signingConfig = if (ks.isEmpty()) {
                signingConfigs.getByName("debug")
            } else {
                signingConfigs.create("mpay") {
                    storeFile = file(ks)
                    storePassword = System.getenv("MPAY_KEYSTORE_PASSWORD")
                    keyAlias = prop("keyAlias").ifEmpty { "mpay" }
                    keyPassword = System.getenv("MPAY_KEY_PASSWORD") ?: System.getenv("MPAY_KEYSTORE_PASSWORD")
                }
            }
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

// ADR-0029: imzolangan bekor qilish ro'yxati build'ga (`-Pmpay.revocationsFile=…`).
val revocationsFile = prop("revocationsFile").takeIf { it.isNotEmpty() }?.let(::file)
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
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.work.runtime)
    implementation(libs.coroutines.android)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
    implementation(libs.compose.material.icons.core)
    testImplementation(libs.junit)
}
