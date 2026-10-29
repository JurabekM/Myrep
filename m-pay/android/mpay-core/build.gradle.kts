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
    // Jazzer fuzz testlari (JUnit 5); mavjud JUnit 4 testlari — vintage engine orqali.
    testImplementation(platform(libs.junit.bom))
    testImplementation(libs.junit.jupiter)
    testImplementation(libs.jazzer.junit)
    testRuntimeOnly(libs.junit.vintage)
    testRuntimeOnly(libs.junit.launcher)
}

tasks.test {
    useJUnitPlatform()
    // Jazzer: JAZZER_FUZZ=1 — haqiqiy fuzzing (scripts/android-fuzz.sh), aks holda regressiya rejimi.
    System.getenv("JAZZER_FUZZ")?.let { environment("JAZZER_FUZZ", it) }
    // Interop testi: MPAY_INTEROP_URL / MPAY_SANDBOX_DIR muhit o'zgaruvchilari (scripts/android-interop.sh).
    environment("MPAY_TESTVECTORS", rootProject.file("../testvectors").absolutePath)
    testLogging { events("passed", "failed", "skipped"); showStandardStreams = true }
}
