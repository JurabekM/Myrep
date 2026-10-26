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
    }

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
