plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.library) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.jvm) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.ksp) apply false
    alias(libs.plugins.hilt) apply false
    alias(libs.plugins.detekt) apply false
    alias(libs.plugins.ktlint) apply false
    alias(libs.plugins.android.junit5) apply false
    alias(libs.plugins.kover)
}

// Aggregated Kover report for the pure-JVM modules (root: ./gradlew koverHtmlReport).
dependencies {
    kover(project(":core:model"))
    kover(project(":core:analysis"))
    kover(project(":core:format"))
    kover(project(":tools:replay"))
}
