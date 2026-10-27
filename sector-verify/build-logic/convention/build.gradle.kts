plugins {
    `kotlin-dsl`
}

group = "uz.sectorverify.buildlogic"

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) }
}

dependencies {
    compileOnly(libs.android.gradle.plugin)
    compileOnly(libs.kotlin.gradle.plugin)
    compileOnly(libs.compose.compiler.gradle.plugin)
    compileOnly(libs.ksp.gradle.plugin)
    compileOnly(libs.detekt.gradle.plugin)
    compileOnly(libs.ktlint.gradle.plugin)
    compileOnly(libs.kover.gradle.plugin)
    compileOnly(libs.android.junit5.gradle.plugin)
}

gradlePlugin {
    plugins {
        register("androidApplication") {
            id = "sv.android.application"
            implementationClass = "uz.sectorverify.buildlogic.AndroidApplicationConventionPlugin"
        }
        register("androidLibrary") {
            id = "sv.android.library"
            implementationClass = "uz.sectorverify.buildlogic.AndroidLibraryConventionPlugin"
        }
        register("androidCompose") {
            id = "sv.android.compose"
            implementationClass = "uz.sectorverify.buildlogic.AndroidComposeConventionPlugin"
        }
        register("androidHilt") {
            id = "sv.android.hilt"
            implementationClass = "uz.sectorverify.buildlogic.AndroidHiltConventionPlugin"
        }
        register("jvmLibrary") {
            id = "sv.jvm.library"
            implementationClass = "uz.sectorverify.buildlogic.JvmLibraryConventionPlugin"
        }
    }
}
