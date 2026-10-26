package uz.sectorverify.buildlogic

import org.gradle.api.JavaVersion
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.plugins.JavaPluginExtension
import org.gradle.kotlin.dsl.configure
import org.gradle.kotlin.dsl.dependencies
import org.jetbrains.kotlin.gradle.dsl.KotlinJvmProjectExtension

class JvmLibraryConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) = with(target) {
        pluginManager.apply("org.jetbrains.kotlin.jvm")
        extensions.configure<JavaPluginExtension> {
            // No toolchain: CI runs JDK 17; newer local JDKs still emit Java 17 bytecode.
            sourceCompatibility = JavaVersion.VERSION_17
            targetCompatibility = JavaVersion.VERSION_17
        }
        extensions.configure<KotlinJvmProjectExtension> {
            compilerOptions { svDefaults() }
        }
        configureQuality()
        dependencies {
            add("testImplementation", platform(libs.lib("junit-bom")))
            add("testImplementation", libs.lib("junit-jupiter"))
            add("testImplementation", libs.lib("kotest-assertions"))
            add("testImplementation", libs.lib("kotest-property"))
            add("testRuntimeOnly", libs.lib("junit-platform-launcher"))
        }
    }
}
