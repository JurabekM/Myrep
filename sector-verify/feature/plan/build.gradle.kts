plugins {
    alias(libs.plugins.sv.android.library)
    alias(libs.plugins.sv.android.compose)
    alias(libs.plugins.sv.android.hilt)
}

android {
    namespace = "uz.sectorverify.feature.plan"
}

dependencies {
    implementation(project(":core:ui"))
    implementation(project(":core:data"))
    implementation(project(":core:format"))
    implementation(libs.androidx.hilt.navigation.compose)
    implementation(libs.kotlinx.coroutines.android)
}
