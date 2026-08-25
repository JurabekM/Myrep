pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "DistribOS"

// Modul chegaralari Clean Architecture bo'yicha:
//   :domain  — sof Kotlin, hech kimga bog'liq emas (biznes qoidalari)
//   :core    — umumiy yordamchilar (formatlash, natija turlari)
//   :crypto  — AETHER-Q / DES-1. Sof Kotlin, JVM testida yuradi.
//   :data    — Room, repozitoriylar
//   :sync    — MQTT + sinxronizatsiya dvigateli
//   :app     — Compose UI va DI; hammasini biriktiradi
include(":app", ":core", ":domain", ":crypto", ":data", ":sync")
