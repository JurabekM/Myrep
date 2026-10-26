plugins {
    alias(libs.plugins.sv.android.application)
    alias(libs.plugins.sv.android.compose)
    alias(libs.plugins.sv.android.hilt)
}

android {
    namespace = "uz.sectorverify.app"
    defaultConfig {
        applicationId = "uz.sectorverify"
        versionCode = 1
        versionName = "0.0.1"
    }
}

dependencies {
    implementation(project(":core:ui"))
    implementation(project(":core:data"))
    implementation(project(":feature:plan"))
    implementation(project(":feature:survey"))
    implementation(project(":feature:report"))
    implementation(project(":feature:settings"))
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.hilt.navigation.compose)
}

dependencies {
    testImplementation(project(":core:analysis"))
    testImplementation(project(":core:telephony"))
    testImplementation(libs.hilt.android.testing)
    kspTest(libs.hilt.compiler)
}
