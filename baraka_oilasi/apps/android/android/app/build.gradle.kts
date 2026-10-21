import java.io.File

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "uz.baraka.oilasi"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "uz.baraka.oilasi"
        // BARAKA_OILASI 3.2: minSdk 26.
        minSdk = 26
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        // `--split-per-abi` o'z ABI filtrini qo'yadi — ikkalasi birga bo'lolmaydi.
        if (!project.hasProperty("split-per-abi")) {
            ndk {
                abiFilters += listOf("arm64-v8a", "armeabi-v7a")
            }
        }
    }

    buildTypes {
        release {
            // Imzolash konfiguratsiyasi repodan tashqarida (RELEASE_CHECKLIST 7): `key.properties`
            // bo'lmasa — debug kalit bilan (faqat mahalliy sinov uchun).
            signingConfig = signingConfigs.getByName("debug")
            isMinifyEnabled = true
            isShrinkResources = true
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

// Rust yadro (`core/bindings/flutter`) — cargo-ndk bilan (BARAKA_OILASI 3.2). Har doim release
// profili: debug `.so` yuzlab MB bo'ladi. Natija `jniLibs` ga yoziladi va APK'ga kiradi.
val repoRoot: File = rootProject.projectDir.resolve("../../..").canonicalFile
val rustJniLibs: File = layout.buildDirectory.dir("rustJniLibs").get().asFile

val buildRustCore by tasks.registering(Exec::class) {
    group = "build"
    description = "Rust yadroni Android ABI'lari uchun yig'adi (cargo-ndk)."
    workingDir = repoRoot
    environment("ANDROID_NDK_HOME", android.ndkDirectory.absolutePath)
    commandLine(
        "cargo", "ndk",
        "-t", "arm64-v8a", "-t", "armeabi-v7a",
        "-P", "26",
        "-o", rustJniLibs.absolutePath,
        "build", "--release", "-p", "baraka-bindings-flutter",
    )
}

android.sourceSets.getByName("main").jniLibs.srcDir(rustJniLibs)

tasks.matching { it.name.startsWith("merge") && it.name.endsWith("JniLibFolders") }.configureEach {
    dependsOn(buildRustCore)
}
