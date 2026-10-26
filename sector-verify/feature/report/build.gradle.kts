plugins {
    alias(libs.plugins.sv.android.library)
    alias(libs.plugins.sv.android.compose)
    alias(libs.plugins.sv.android.hilt)
}

android {
    namespace = "uz.sectorverify.feature.report"
}

dependencies {
    implementation(project(":core:ui"))
    implementation(project(":core:data"))
    implementation(project(":core:analysis"))
    implementation(project(":core:format"))
    implementation(libs.androidx.hilt.navigation.compose)
    implementation(libs.kotlinx.coroutines.android)
}
