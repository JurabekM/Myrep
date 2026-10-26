package uz.sectorverify.buildlogic

import com.android.build.api.dsl.CommonExtension
import io.gitlab.arturbosch.detekt.extensions.DetektExtension
import org.gradle.api.JavaVersion
import org.gradle.api.Project
import org.gradle.api.artifacts.VersionCatalog
import org.gradle.api.artifacts.VersionCatalogsExtension
import org.gradle.api.tasks.testing.Test
import org.gradle.kotlin.dsl.configure
import org.gradle.kotlin.dsl.getByType
import org.gradle.kotlin.dsl.withType
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.jetbrains.kotlin.gradle.dsl.KotlinJvmCompilerOptions
import org.jlleitschuh.gradle.ktlint.KtlintExtension

internal object Sdk {
    const val COMPILE = 35
    const val TARGET = 35
    const val MIN = 29
}

internal val Project.libs: VersionCatalog
    get() = extensions.getByType<VersionCatalogsExtension>().named("libs")

internal fun VersionCatalog.lib(alias: String) = findLibrary(alias).get()

internal fun VersionCatalog.ver(alias: String) = findVersion(alias).get().requiredVersion

internal fun KotlinJvmCompilerOptions.svDefaults() {
    jvmTarget.set(JvmTarget.JVM_17)
    allWarningsAsErrors.set(false)
    freeCompilerArgs.addAll("-Xjsr305=strict")
}

internal fun Project.configureAndroidCommon(ext: CommonExtension<*, *, *, *, *, *>) {
    ext.apply {
        compileSdk = Sdk.COMPILE
        defaultConfig {
            minSdk = Sdk.MIN
            testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        }
        compileOptions {
            sourceCompatibility = JavaVersion.VERSION_17
            targetCompatibility = JavaVersion.VERSION_17
        }
        lint {
            abortOnError = true
            warningsAsErrors = false
            checkDependencies = false
            disable += setOf("GradleDependency", "NewerVersionAvailable", "AndroidGradlePluginVersion", "OldTargetApi")
            xmlReport = true
            htmlReport = true
        }
        testOptions {
            unitTests.isIncludeAndroidResources = true
            unitTests.isReturnDefaultValues = true
        }
        packaging {
            resources.excludes += setOf("/META-INF/{AL2.0,LGPL2.1}", "/META-INF/LICENSE*", "/META-INF/NOTICE*")
        }
    }
}

/** Har bir modul uchun detekt + ktlint + Kover + JUnit 5. */
internal fun Project.configureQuality() {
    pluginManager.apply("io.gitlab.arturbosch.detekt")
    pluginManager.apply("org.jlleitschuh.gradle.ktlint")
    pluginManager.apply("org.jetbrains.kotlinx.kover")

    extensions.configure<DetektExtension> {
        buildUponDefaultConfig = true
        config.setFrom(rootProject.files("config/detekt/detekt.yml"))
        parallel = true
    }
    extensions.configure<KtlintExtension> {
        version.set(libs.ver("ktlint"))
        android.set(true)
        filter { exclude { it.file.path.contains("/build/") } }
    }
    tasks.withType<Test>().configureEach {
        useJUnitPlatform {
            // "slow": 1000 iteratsiyali Monte-Carlo (-Pslow). "perf": vaqt byudjetlari, CI'da alohida ishlaydi (-Pperf), ADR-015.
            if (project.hasProperty("perf")) {
                includeTags("perf")
            } else {
                excludeTags("perf")
                if (!project.hasProperty("slow")) excludeTags("slow")
            }
        }
        maxHeapSize = "2g"
        testLogging { events("failed"); exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL }
        systemProperty("sv.reportsDir", project.layout.buildDirectory.dir("reports").get().asFile.absolutePath)
        // Robolectric'ning android-all jar'lari uchun ixtiyoriy mirror (masalan, Maven Central so'rovlarni cheklaganda).
        project.findProperty("sv.robolectricRepoUrl")?.let { systemProperty("robolectric.dependency.repo.url", it) }
    }
}
