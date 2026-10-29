plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "uz.mpay.wallet.sdk"
    compileSdk = 36

    defaultConfig {
        minSdk = 26
        consumerProguardFiles("consumer-rules.pro")
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) }
}

dependencies {
    api(project(":mpay-core"))
    implementation(libs.bcprov)
    implementation(libs.androidx.core.ktx)
    api(libs.androidx.biometric)
    // biometric 1.1.0 eski fragment'ni (1.2.5) olib keladi — uning FragmentActivity'si Activity Result API'ning
    // so'rov kodini rad etadi ("lower 16 bits" crash, ruxsat so'rashda).
    api(libs.androidx.fragment)
}
