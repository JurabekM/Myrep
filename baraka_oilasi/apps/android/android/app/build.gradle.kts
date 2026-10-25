import java.io.File
import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Reliz imzosi (RELEASE_CHECKLIST 7): kalit repodan tashqarida — `android/key.properties`
// (gitignore) yoki CI muhit o'zgaruvchilari. Yo'q bo'lsa — debug kalit (faqat mahalliy sinov);
// `BARAKA_REQUIRE_RELEASE_SIGNING=1` bo'lsa, kalitsiz release yig'ilmaydi.
val keyProps = Properties().apply {
    val f = rootProject.file("key.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

fun signingValue(key: String, env: String): String? = keyProps.getProperty(key) ?: System.getenv(env)

val releaseStoreFile = signingValue("storeFile", "BARAKA_KEYSTORE_FILE")
val requireReleaseSigning = System.getenv("BARAKA_REQUIRE_RELEASE_SIGNING") == "1"

// Demo (`flutter build apk -P baraka.demo=true --dart-define=BARAKA_DEMO=true ...`): boshqa paket nomi
// (asl ilova sifatida Play'ga yuklab bo'lmaydi va telefondagi asl ilova bilan aralashmaydi) va har
// doim debug kalit — reliz (upload) kaliti demoga hech qachon qo'yilmaydi.
val demo = project.findProperty("baraka.demo") == "true"

// Yadro va APK ABI'lari: standart — telefonlar (arm64, armv7); emulyator testi `-P baraka.abis=x86_64`.
val abis: List<String> = (project.findProperty("baraka.abis") as String? ?: "arm64-v8a,armeabi-v7a")
    .split(",").map { it.trim() }.filter { it.isNotEmpty() }

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
        if (demo) {
            applicationIdSuffix = ".demo"
            versionNameSuffix = "-demo"
        }
        manifestPlaceholders["appLabel"] = if (demo) "Baraka Dastur DEMO" else "Baraka Dastur"
        // `--split-per-abi` o'z ABI filtrini qo'yadi — ikkalasi birga bo'lolmaydi.
        if (!project.hasProperty("split-per-abi")) {
            ndk {
                abiFilters += abis
            }
        }
    }

    signingConfigs {
        if (releaseStoreFile != null) {
            create("release") {
                storeFile = rootProject.file(releaseStoreFile)
                storePassword = signingValue("storePassword", "BARAKA_KEYSTORE_PASSWORD")
                keyAlias = signingValue("keyAlias", "BARAKA_KEY_ALIAS")
                keyPassword = signingValue("keyPassword", "BARAKA_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            if (releaseStoreFile == null && requireReleaseSigning && !demo) {
                throw GradleException("Reliz kaliti topilmadi: key.properties yoki BARAKA_KEYSTORE_FILE kerak.")
            }
            signingConfig = signingConfigs.getByName(if (releaseStoreFile != null && !demo) "release" else "debug")
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
        listOf("cargo", "ndk") + abis.flatMap { listOf("-t", it) } + listOf(
            "-P", "26",
            "-o", rustJniLibs.absolutePath,
            "build", "--release", "-p", "baraka-bindings-flutter",
        ),
    )
}

android.sourceSets.getByName("main").jniLibs.srcDir(rustJniLibs)

tasks.matching { it.name.startsWith("merge") && it.name.endsWith("JniLibFolders") }.configureEach {
    dependsOn(buildRustCore)
}
