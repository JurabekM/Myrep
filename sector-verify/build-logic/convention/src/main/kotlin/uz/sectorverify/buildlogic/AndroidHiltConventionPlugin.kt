package uz.sectorverify.buildlogic

import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.dependencies

class AndroidHiltConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) = with(target) {
        pluginManager.apply("com.google.devtools.ksp")
        pluginManager.apply("com.google.dagger.hilt.android")
        dependencies {
            add("implementation", libs.lib("hilt-android"))
            add("ksp", libs.lib("hilt-compiler"))
        }
        // Lint test manbalari bilan KSP chiqishini ham o'qiydi, lekin AGP 8.10 ksp<Variant>Kotlin ga bog'liqlik qo'ymaydi:
        // parallel build'da lint KSP'ning vaqtinchalik byRounds/ fayllarini ko'rib, ular o'chganda yiqiladi (ADR-018).
        tasks.configureEach {
            val variant = LINT_ANALYZE.matchEntire(name)?.groupValues?.get(1) ?: return@configureEach
            dependsOn(tasks.matching { it.name == "ksp${variant}Kotlin" })
        }
    }

    private companion object {
        val LINT_ANALYZE = Regex("lint(?:Vital)?Analyze(\\w+)")
    }
}
