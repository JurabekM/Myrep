package uz.sectorverify.buildlogic

import com.android.build.api.dsl.LibraryExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.configure
import org.gradle.kotlin.dsl.dependencies
import org.jetbrains.kotlin.gradle.dsl.KotlinAndroidProjectExtension

class AndroidLibraryConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) = with(target) {
        pluginManager.apply("com.android.library")
        pluginManager.apply("org.jetbrains.kotlin.android")
        pluginManager.apply("de.mannodermaus.android-junit5")
        extensions.configure<LibraryExtension> {
            configureAndroidCommon(this)
            defaultConfig.consumerProguardFiles("consumer-rules.pro")
        }
        extensions.configure<KotlinAndroidProjectExtension> {
            compilerOptions { svDefaults() }
        }
        configureQuality()
        configureAndroidTestDeps()
    }
}

internal fun Project.configureAndroidTestDeps() {
    dependencies {
        add("testImplementation", platform(libs.lib("junit-bom")))
        add("testImplementation", libs.lib("junit-jupiter"))
        add("testImplementation", libs.lib("kotest-assertions"))
        add("testImplementation", libs.lib("kotlinx-coroutines-test"))
        add("testImplementation", libs.lib("turbine"))
        // Robolectric tests are JUnit 4 and run on the vintage engine.
        add("testImplementation", libs.lib("junit4"))
        add("testImplementation", libs.lib("robolectric"))
        add("testImplementation", libs.lib("androidx-test-core"))
        add("testImplementation", libs.lib("androidx-test-ext-junit"))
        add("testRuntimeOnly", libs.lib("junit-vintage-engine"))
        add("testRuntimeOnly", libs.lib("junit-platform-launcher"))
        add("androidTestImplementation", libs.lib("androidx-test-runner"))
        add("androidTestImplementation", libs.lib("androidx-test-rules"))
        add("androidTestImplementation", libs.lib("androidx-test-ext-junit"))
        add("androidTestImplementation", libs.lib("kotlinx-coroutines-test"))
    }
}
