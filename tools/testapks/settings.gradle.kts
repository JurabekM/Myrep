// ROSTOR-2 E2E sinovi uchun zararsiz sinov APK'lari. Hech qanday haqiqiy xatti-harakat yo'q:
// faqat manifest belgilari (ruxsatlar, Accessibility xizmati) APK Qalqon qoidalarini sinash uchun.
pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { google(); mavenCentral() } }
rootProject.name = "rostor2-testapks"
include(":app")
