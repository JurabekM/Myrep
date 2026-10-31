// Sof Kotlin yadro: pul, tasnif, reja, kalkulyator. Android'ga bog'liq emas — JVM'da test qilinadi.
plugins {
    id("org.jetbrains.kotlin.jvm")
    id("org.jetbrains.kotlin.plugin.serialization")
}

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
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
    testImplementation(kotlin("test"))
    testImplementation("junit:junit:4.13.2")
}

tasks.test {
    // Oltin vektorlar: ../../spec/test-vectors (Python oracle bilan hisoblangan).
    systemProperty("qarzsiz.vectors", rootProject.file("../spec/test-vectors").absolutePath)
}
