plugins {
    alias(libs.plugins.sv.jvm.library)
    alias(libs.plugins.kotlin.serialization)
}

dependencies {
    api(project(":core:model"))
    api(libs.kotlinx.serialization.json)
}
