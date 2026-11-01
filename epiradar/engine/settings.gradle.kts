// EpiRadar yadrosi — sof Kotlin/JVM (Android importi taqiqlangan).
// Mustaqil yig'iladi (`gradle test`) va Android ilovaga composite build sifatida ulanadi
// (android/settings.gradle.kts → includeBuild("../engine")).
pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositories {
        mavenCentral()
    }
}

rootProject.name = "epiradar-engine"
