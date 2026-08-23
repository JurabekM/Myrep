plugins {
    alias(libs.plugins.kotlin.jvm)
}

// DIQQAT: bu SOF Kotlin/JVM moduli, Android kutubxonasi emas.
//
// Sabab: kripto kodini oddiy JVM testida ishga tushirish mumkin bo'ladi
// (emulator yoki Robolectric kerak emas), ya'ni Python bilan baytma-bayt
// moslikni tekshiradigan KAT testi soniyalar ichida yuradi.
//
// Butun kripto BouncyCastle ustida qurilgani uchun bu modul Android'da
// ham hech qanday o'zgarishsiz ishlaydi.

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}

dependencies {
    api(libs.bouncycastle)

    testImplementation(libs.junit)
    testImplementation("org.json:json:20250517")
}

tasks.test {
    testLogging {
        events("passed", "failed", "skipped")
        showStandardStreams = false
    }
}
