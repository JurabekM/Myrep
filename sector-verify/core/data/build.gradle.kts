plugins {
    alias(libs.plugins.sv.android.library)
    alias(libs.plugins.sv.android.hilt)
    alias(libs.plugins.kotlin.serialization)
}

android {
    namespace = "uz.sectorverify.data"
    defaultConfig {
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    sourceSets {
        // Room schemas are inputs of the migration tests.
        getByName("androidTest").assets.srcDir("$projectDir/schemas")
        getByName("test").assets.srcDir("$projectDir/schemas")
    }
}

ksp {
    arg("room.schemaLocation", "$projectDir/schemas")
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
