plugins {
    kotlin("jvm") version "2.4.0"
    `java-library`
}

group = "uz.epiradar"
version = "1.0.0"

kotlin {
    // Android ilova JVM 17 bilan yig'iladi — yadro ham shu nishonda.
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
        // JDK 21 bilan yig'ilganda ham faqat Java 17 API'ga bog'lanish: Android'da yo'q metodlar
        // (masalan, List.removeFirst — API 35) kompilyatsiyada ushlanadi.
        freeCompilerArgs.add("-Xjdk-release=17")
        allWarningsAsErrors.set(true)
    }
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

dependencies {
    api("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.11.0")
    api("org.jetbrains.kotlinx:kotlinx-serialization-json:1.11.0")

    testImplementation(kotlin("test"))
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.11.0")
}

tasks.test {
    useJUnitPlatform()
    // Testlardagi sanalar aniq bo'lishi uchun (manbalar UTC beradi).
    systemProperty("user.timezone", "UTC")
}
