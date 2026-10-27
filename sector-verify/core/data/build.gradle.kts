plugins {
    alias(libs.plugins.sv.android.library)
    alias(libs.plugins.sv.android.hilt)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.room)
}

// Room plagini sxemani variantlar bo'yicha to'g'ri eksport qiladi (debug va release KSP bitta faylga parallel yozmaydi).
room {
    schemaDirectory("$projectDir/schemas")
}

android {
    namespace = "uz.sectorverify.data"
    defaultConfig {
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    sourceSets {
        // Room sxemalari migratsiya testlarining kirish ma'lumotlari.
        getByName("androidTest").assets.srcDir("$projectDir/schemas")
        getByName("test").assets.srcDir("$projectDir/schemas")
    }
}

ksp {
    arg("room.generateKotlin", "true")
}

dependencies {
    api(project(":core:model"))
    api(project(":core:format"))
    implementation(libs.androidx.core.ktx)
    implementation(libs.kotlinx.coroutines.android)
    api(libs.room.runtime)
    implementation(libs.room.ktx)
    ksp(libs.room.compiler)
    implementation(libs.androidx.sqlite)
    implementation(libs.sqlcipher.android)
    api(libs.datastore.preferences)
    testImplementation(libs.room.testing)
    androidTestImplementation(libs.room.testing)
}
