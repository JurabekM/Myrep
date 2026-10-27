package uz.sectorverify.buildlogic

import com.android.build.api.dsl.ApplicationExtension
import com.android.build.api.variant.ApplicationAndroidComponentsExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.kotlin.dsl.configure
import org.jetbrains.kotlin.gradle.dsl.KotlinAndroidProjectExtension

class AndroidApplicationConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) = with(target) {
        pluginManager.apply("com.android.application")
        pluginManager.apply("org.jetbrains.kotlin.android")
        pluginManager.apply("de.mannodermaus.android-junit5")
        extensions.configure<ApplicationExtension> {
            configureAndroidCommon(this)
            defaultConfig.targetSdk = Sdk.TARGET
        }
        // Compose test activity faqat debug'da bor (ui-test-manifest), shuning uchun host testlar debug'da ishlaydi (ADR-012).
        extensions.configure<ApplicationAndroidComponentsExtension> {
            beforeVariants(selector().withBuildType("release")) { it.enableUnitTest = false }
        }
        extensions.configure<KotlinAndroidProjectExtension> {
            compilerOptions { svDefaults() }
        }
        configureQuality()
        configureAndroidTestDeps()
    }
}
