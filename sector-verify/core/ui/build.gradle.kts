plugins {
    alias(libs.plugins.sv.android.library)
    alias(libs.plugins.sv.android.compose)
}

android {
    namespace = "uz.sectorverify.ui"
}

dependencies {
    api(project(":core:model"))
    api(libs.compose.material.icons)
}
