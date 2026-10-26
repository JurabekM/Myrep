plugins {
    alias(libs.plugins.sv.jvm.library)
    alias(libs.plugins.kotlin.serialization)
    application
}

application {
    mainClass.set("uz.sectorverify.replay.MainKt")
    applicationName = "sv-replay"
    // Istalgan konsolda o'zbekcha/ruscha chiqish (Windows cp1251/cp866, POSIX C locale).
    applicationDefaultJvmArgs = listOf("-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8")
}

dependencies {
    implementation(project(":core:analysis"))
    implementation(project(":core:format"))
}
