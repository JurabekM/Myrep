plugins {
    alias(libs.plugins.sv.android.library)
}

android {
    namespace = "uz.sectorverify.location"
}

dependencies {
    api(project(":core:model"))
    implementation(libs.androidx.core.ktx)
    implementation(libs.kotlinx.coroutines.android)
}
