plugins {
    alias(libs.plugins.kotlin.jvm)
}

// JDK 21 (Android Studio JBR) bilan yig'iladi, bayt-kod Android uchun Java 17.
java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) }
}

dependencies {
    // ML-KEM-768, ML-DSA-65, X25519, Ed25519, ChaCha20-Poly1305, AES-CMAC.
    implementation(libs.bcprov)
    // Android'da org.json platformda bor; JVM testlarida — artefakt.
    compileOnly(libs.json)
    testImplementation(libs.json)
    testImplementation(libs.bcpkix)
    testImplementation(libs.junit)
}

tasks.test {
    // Interop testi: MPAY_INTEROP_URL / MPAY_SANDBOX_DIR muhit o'zgaruvchilari (scripts/android-interop.sh).
    environment("MPAY_TESTVECTORS", rootProject.file("../testvectors").absolutePath)
    testLogging { events("passed", "failed", "skipped"); showStandardStreams = true }
}
