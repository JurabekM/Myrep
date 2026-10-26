pluginManagement {
    includeBuild("build-logic")
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

rootProject.name = "sector-verify"

include(
    ":app",
    ":feature:plan",
    ":feature:survey",
    ":feature:report",
    ":feature:settings",
    ":core:telephony",
    ":core:location",
    ":core:data",
    ":core:analysis",
    ":core:format",
    ":core:model",
    ":core:ui",
    ":tools:replay",
)
