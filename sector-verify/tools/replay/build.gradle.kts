plugins {
    alias(libs.plugins.sv.jvm.library)
    alias(libs.plugins.kotlin.serialization)
    application
}

application {
    mainClass.set("uz.sectorverify.replay.MainKt")
    applicationName = "sv-replay"
}

dependencies {
    implementation(project(":core:analysis"))
    implementation(project(":core:format"))
}
